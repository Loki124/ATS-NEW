"""campus_rotation 序列化器。

负责：
- 字段暴露（camelCase 由 djangorestframework-camel-case 自动转换）；
- 写时业务校验（BU 二级部门 / 身份角色 / 字典启用 / 直属上级防成环 / 日期区间）；
- 只读聚合字段 campus_count（轮岗资源）、student_count（班级）。
"""
from django.db import IntegrityError
from rest_framework import serializers

from apps.campus_control.models import Person

from .models import (
    ClassRoom,
    ConcurrentPostRecord,
    RotationApproval,
    RotationArrangement,
    RotationResource,
    RotationStage,
)
from .validators import (
    MENTOR_ONGOING_CAPACITY,
    CapacityExceeded,
    dict_key_active,
    is_bu_depth,
    is_subordinate_of,
    resolve_intent_bu,
    user_has_campus_role,
)


# ---------------------------------------------------------------------------
# RotationResource（轮岗资源）—— 2026-10-22 兵哥指令：直播间 + 客服部门整合
# ---------------------------------------------------------------------------
class RotationResourceSerializer(serializers.ModelSerializer):
    """轮岗资源（直播间 / 客服部门 / 其他 三种形态合并为一张表）。

    字段归并（2026-10-22 兵哥指令）：
      · 直播间编号 / 客服部门编号 → **资源编号**（resource_no）
      · 直播间名称 / 部门名称 → **资源名称**（name）
      · 直播间导师 / 客服主管 → **导师**（mentor）
      · 新增 **资源类型**（resource_type）：直播间 / 客服部门 / 其他

    已下线字段（需求明确要求去掉，模型层已无对应列）：
      品牌 / 客服类型 / 工位类型 / 是否需培训认证
    平台（platform）保留 —— 2026-10-23 闸口1 裁决：直播间 / 客服部门 / 其他
    **三类形态均可选填**（有值则须为启用中的 LIVE_ROOM_PLATFORM 字典项）。
    """
    # 只读聚合字段（不落库）：按资源归属部门 + 在校（ONGOING）状态统计校招生占用。
    campus_count = serializers.IntegerField(read_only=True, default=0)
    # 导师展示名（FK 本身只出 PK）
    mentor_name = serializers.SerializerMethodField()

    class Meta:
        model = RotationResource
        fields = [
            'id', 'resource_no', 'name', 'resource_type', 'department', 'bu',
            'mentor', 'mentor_name', 'platform', 'location', 'capacity',
            'social_count', 'is_active', 'remark',
            'created_at', 'updated_at', 'campus_count',
        ]
        read_only_fields = [
            'id', 'resource_no', 'mentor_name', 'created_at', 'updated_at', 'campus_count',
        ]
        extra_kwargs = {
            # 资源类型是本次整合新增的核心区分字段 → 必填（模型层有默认值，
            # 若不在这里显式声明，DRF 会把它当「可省略」→ 客户端漏传就静默落成直播间）。
            'resource_type': {'required': True},
        }

    def validate(self, attrs):
        department = attrs.get('department')
        if department is not None and not department.is_active:
            raise serializers.ValidationError(
                {'department': '归属部门未启用，请选择启用状态的部门'})

        bu = attrs.get('bu')
        if bu is not None:
            if not bu.is_active:
                raise serializers.ValidationError(
                    {'bu': '归属BU部门未启用'})
            if not is_bu_depth(bu):
                raise serializers.ValidationError(
                    {'bu': 'BU 须为二级部门（部门层级=第2级）'})

        mentor = attrs.get('mentor')
        if mentor is not None and not user_has_campus_role(mentor.id, 'CAMPUS_MENTOR'):
            raise serializers.ValidationError(
                {'mentor': '该用户不具备校园导师（CAMPUS_MENTOR）身份'})

        # 平台：2026-10-23 闸口1 裁决 —— **不再按资源类型设限**（Q1：OTHER 一并放开）。
        #   唯一约束是「有值则须为启用中的字典项」；留空一律允许。
        #   ⚠️ 直播间资源的平台「必填」口径只在 **Excel 导入**端（行级错误）成立，
        #      表单端历史口径即为「不强校验」，本次维持现状（不改 = 不引入新口径差）。
        platform = attrs.get('platform')
        if platform:
            if not dict_key_active('LIVE_ROOM_PLATFORM', platform):
                raise serializers.ValidationError(
                    {'platform': '平台字典项不存在或未启用'})

        # 2026-10-22 兵哥指令：直播间「地点」改为单行自由文本（前端不再是 LOCATION 字典下拉）
        #   → 保留字典校验会让自由输入一律 400「地点字典项不存在或未启用」。
        #   长度仍受模型 max_length=64 约束（DRF 自动校验）。
        return attrs

    def get_mentor_name(self, obj):
        """导师显示名：优先姓名，其次 username，都没有则空串。"""
        if not obj.mentor_id:
            return ''
        mentor = obj.mentor
        return mentor.get_full_name() or mentor.username or ''

    @staticmethod
    def _campus_counts(context):
        """{资源 id: 在校(ONGOING)占用人数} —— 一次聚合查询（N+1 纪律）。

        口径（2026-10-22 合并后统一）：**该资源被多少条 ONGOING 的轮岗安排占用**
        （`RotationArrangement.resource_id`）。
        ⚠️ 合并前直播间用的是「按归属部门统计」（current_dept_id == 直播间.归属部门）、
        客服部门用的是「按资源统计」（service_dept_id == 客服部门.id），两套口径。
        合并成一张表后只能有一套 → 取**资源级精确口径**：一个安排只处于一个位置，
        按 resource 统计不会重复计入同部门的其它资源。
        映射缓存在 request 级 context 上 —— 同一请求内所有资源共用一次查询。
        """
        cache = context.setdefault('_resource_campus_counts', {})
        if cache:
            return cache
        from django.db.models import Count

        rows = (
            RotationArrangement.objects.filter(stage='ONGOING', deleted_at__isnull=True)
            .exclude(resource_id__isnull=True)
            .values('resource_id')
            .annotate(c=Count('id'))
        )
        for row in rows:
            cache[row['resource_id']] = row['c']
        return cache

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        counts = self._campus_counts(self.context)
        ret['campusCount'] = counts.get(instance.id, 0)
        return ret


# ---------------------------------------------------------------------------
# ClassRoom
# ---------------------------------------------------------------------------
class ClassRoomSerializer(serializers.ModelSerializer):
    # 只读聚合字段：该班级绑定的校招生人数。
    student_count = serializers.IntegerField(read_only=True, default=0)
    # 班长展示名（FK 本身只出 PK）
    class_monitor_name = serializers.SerializerMethodField()
    # 阶段分布（该班级的轮岗安排按阶段计数，页面可下钻）
    stage_counts = serializers.SerializerMethodField()

    class Meta:
        model = ClassRoom
        fields = [
            'id', 'code', 'name', 'head_teacher', 'hrbp',
            'batch', 'capacity', 'remark', 'created_at', 'updated_at', 'student_count',
            'class_monitor', 'class_monitor_name', 'stage_counts',
        ]
        read_only_fields = [
            'id', 'code', 'created_at', 'updated_at', 'student_count',
            # 班级名称 = 流水号：新建由服务端生成、编辑不可改 → 整字段只读
            'name', 'class_monitor_name', 'stage_counts',
        ]

    def get_class_monitor_name(self, obj):
        return obj.class_monitor.full_name if obj.class_monitor_id else ''

    @staticmethod
    def _stage_counts_map(context):
        """班级 → 阶段分布（一次聚合查询，N+1 纪律）。

        口径：该班级的轮岗安排按 stage 分组计数，只统计页面展示的三态
        （待分配 PENDING / 轮岗中 ONGOING / 已完成 DONE）。
        映射缓存在 request 级 context 上 —— 同一请求内所有班级共用一次查询。
        """
        cache = context.setdefault('_class_stage_counts', {})
        if cache:
            return cache
        from django.db.models import Count

        rows = (
            RotationArrangement.objects.filter(deleted_at__isnull=True)
            .values('class_room_id', 'stage')
            .annotate(c=Count('id'))
        )
        for row in rows:
            cache.setdefault(row['class_room_id'], {})[row['stage']] = row['c']
        return cache

    def get_stage_counts(self, obj):
        """该班级的阶段分布（三态计数；无安排则全 0）。"""
        by_stage = self._stage_counts_map(self.context).get(obj.id, {})
        return {
            'PENDING': by_stage.get('PENDING', 0),
            'ONGOING': by_stage.get('ONGOING', 0),
            'DONE': by_stage.get('DONE', 0),
        }

    @staticmethod
    def next_class_name() -> str:
        """下一个班级名称（从 1 开始的流水号）。

        只统计**纯数字**班名（历史遗留的「2026校招-上海-01班」之类不参与）；
        已删除的班级不占用序号（取现存最大值 + 1，天然回避被删号）。
        """
        nums = []
        for value in ClassRoom.objects.filter(deleted_at__isnull=True).values_list('name', flat=True):
            s = str(value).strip()
            if s.isdigit():
                nums.append(int(s))
        return str(max(nums) + 1 if nums else 1)

    def validate(self, attrs):
        head_teacher = attrs.get('head_teacher')
        if head_teacher is not None and not user_has_campus_role(head_teacher.id, 'HEAD_TEACHER'):
            raise serializers.ValidationError(
                {'headTeacher': '班主任须具备 HEAD_TEACHER 身份'})
        return attrs

    def create(self, validated_data):
        # 班级名称 = 流水号（客户端传的名字一律忽略，避免与流水号冲突）
        validated_data.pop('name', None)
        # 并发新建可能撞号（唯一约束）→ 重算后重试
        for _ in range(3):
            validated_data['name'] = self.next_class_name()
            try:
                return super().create(validated_data)
            except IntegrityError:
                continue
        raise serializers.ValidationError({'name': '班级序号生成冲突，请重试'})

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        ret['studentCount'] = RotationArrangement.objects.filter(
            class_room_id=instance.id,
        ).count()
        return ret


# ---------------------------------------------------------------------------
# RotationArrangement
# ---------------------------------------------------------------------------
class RotationArrangementSerializer(serializers.ModelSerializer):
    # 「轮岗位置」已不再是独立列（2026-10-22 直播间+客服部门合并为「轮岗资源」）：
    #   类型由 resource.resource_type 唯一决定 → 此处**派生输出**、只读。
    #   客户端不再提交 location_type（提交也会被忽略），避免类型与资源错配。
    location_type = serializers.SerializerMethodField()
    # 2026-10-21 三期：表单「基本信息」组需要回填校招生的工号 / 教育经历 / 入职日期。
    # 关联口径：RotationArrangement.person_id == campus_control.Person.user_id。
    person_name = serializers.SerializerMethodField()
    person_employee_id = serializers.SerializerMethodField()
    person_education = serializers.SerializerMethodField()
    person_expected_entry_date = serializers.SerializerMethodField()
    person_actual_entry_date = serializers.SerializerMethodField()
    # 具体位置（轮岗资源）/ 班长的展示名
    resource_name = serializers.SerializerMethodField()
    class_monitor_name = serializers.SerializerMethodField()
    # 2026-10-22：校招生档案（人员级，nanoid 口径）——写入口。
    #   传 campus_person（Person 主键）→ 自动把旧口径 person_id 镜像成该人员的 user_id
    #   （无账号时为空；person_id 仅作历史兼容，不再作为按人定位的口径）。
    campus_person = serializers.PrimaryKeyRelatedField(
        queryset=Person.objects.filter(deleted_at__isnull=True),
        required=False, allow_null=True,
    )

    class Meta:
        model = RotationArrangement
        fields = [
            'id', 'person_id', 'intent_bu', 'suggest_dept', 'suggest_mentor',
            'head_teacher', 'current_dept', 'mentor', 'direct_manager',
            'class_room', 'stage', 'employee_status', 'rotation_start',
            'rotation_end', 'rank', 'final_dept', 'result', 'note',
            # 具体位置（轮岗资源，直播间/客服部门/其他合一）+ 班长 + 批次
            'resource', 'resource_name', 'location_type', 'class_monitor',
            'class_monitor_name', 'batch',
            # 2026-10-22：校招生档案（人员级关联）
            'campus_person',
            # 校招生基本信息（只读，供表单回填）
            'person_name', 'person_employee_id', 'person_education',
            'person_expected_entry_date', 'person_actual_entry_date',
            'created_at', 'updated_at',
        ]
        # 🔴 S5-19：stage 为 FSM 流程态，只经 /transition/ 端点流转，通用 CRUD 不可直写。
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'stage',
            'person_name', 'person_employee_id', 'person_education',
            'person_expected_entry_date', 'person_actual_entry_date',
            'resource_name', 'location_type', 'class_monitor_name',
        ]

    # ── 校招生基本信息（person_id → Person.user_id 口径）────────────
    def _person(self, obj):
        """取该安排对应的校招生档案（带请求级缓存，避免列表 N+1）。

        优先用**人员级关联** `campus_person`（nanoid 口径，2026-10-22 新增）；
        旧数据回退到 `person_id`（账号 id 口径）。
        """
        if obj.campus_person_id:
            return obj.campus_person
        if not obj.person_id:
            return None
        cache = self.context.setdefault('_person_by_user_id', {})
        key = str(obj.person_id)
        if key not in cache:
            cache[key] = Person.objects.filter(
                user_id=obj.person_id, deleted_at__isnull=True,
            ).first()
        return cache[key]

    def get_person_name(self, obj):
        p = self._person(obj)
        return p.name if p else ''

    def get_person_employee_id(self, obj):
        p = self._person(obj)
        return p.employee_id if p else ''

    def get_person_education(self, obj):
        p = self._person(obj)
        return p.education if p else ''

    def get_person_expected_entry_date(self, obj):
        p = self._person(obj)
        return p.expected_entry_date if p else None

    def get_person_actual_entry_date(self, obj):
        p = self._person(obj)
        return p.actual_entry_date if p else None

    def get_resource_name(self, obj):
        """具体位置（轮岗资源）名称。"""
        return obj.resource.name if obj.resource_id else ''

    def get_location_type(self, obj):
        """轮岗位置类型：派生自资源类型（直播间 / 客服部门 / 其他），无资源则空串。"""
        return obj.resource.resource_type if obj.resource_id else ''

    def get_class_monitor_name(self, obj):
        return obj.class_monitor.full_name if obj.class_monitor_id else ''

    def validate(self, attrs):
        instance = self.instance

        # 2026-10-22：校招生档案（人员级）→ 旧口径 person_id 镜像（该人员的账号 id；
        #   无账号时为空 —— person_id 仅作历史兼容，不再作为按人定位的口径）。
        if 'campus_person' in attrs:
            person = attrs.get('campus_person')
            attrs['person_id'] = (person.user_id or None) if person is not None else None

        # 新建时校招生必填：人员级关联与旧口径账号 id 至少给一个。
        # （person_id 已允许为空 —— 校招生常常没有系统账号，不能再靠 NOT NULL 兜底必填性。）
        # 仅在新建时校验：编辑历史行时前端可能两个字段都不提交（保持原样不被冲掉）。
        if instance is None and not attrs.get('campus_person') and not attrs.get('person_id'):
            raise serializers.ValidationError({'campusPerson': '请选择校招生'})

        # 具体位置（轮岗资源）校验：
        #   资源只允许指向**启用中**的轮岗资源（停用资源不应再被新安排占用）；
        #   ⚠️ 资源可空 —— 未分配具体位置的安排（未进入轮岗）是合法状态。
        #   「轮岗位置类型」不再单独校验：它由 resource.resource_type 唯一决定，
        #   不存在「类型与资源错配」的可能（原本靠互斥清理规避的那类脏数据已消除）。
        resource = attrs.get('resource')
        if resource is not None and not resource.is_active:
            raise serializers.ValidationError(
                {'resource': '该轮岗资源已停用，请选择启用状态的资源'})

        # 部门启用校验
        for fld in ('suggest_dept', 'current_dept'):
            dept = attrs.get(fld)
            if dept is not None and not dept.is_active:
                raise serializers.ValidationError(
                    {fld: '部门未启用，请选择启用状态的部门'})

        # 身份角色校验
        mentor = attrs.get('mentor')
        if mentor is not None and not user_has_campus_role(mentor.id, 'CAMPUS_MENTOR'):
            raise serializers.ValidationError(
                {'mentor': '导师须具备校园导师（CAMPUS_MENTOR）身份'})
        suggest_mentor = attrs.get('suggest_mentor')
        if suggest_mentor is not None and not user_has_campus_role(suggest_mentor.id, 'CAMPUS_MENTOR'):
            raise serializers.ValidationError(
                {'suggestMentor': '建议导师须具备校园导师（CAMPUS_MENTOR）身份'})
        head_teacher = attrs.get('head_teacher')
        if head_teacher is not None and not user_has_campus_role(head_teacher.id, 'HEAD_TEACHER'):
            raise serializers.ValidationError(
                {'headTeacher': '班主任须具备 HEAD_TEACHER 身份'})

        # intent_bu：存名/编码，校验被引用部门存在且为二级部门
        intent_bu = attrs.get('intent_bu')
        if intent_bu:
            dept = resolve_intent_bu(intent_bu)
            if not dept:
                raise serializers.ValidationError(
                    {'intentBu': '意向BU部门不存在'})
            if not is_bu_depth(dept):
                raise serializers.ValidationError(
                    {'intentBu': 'BU 须为二级部门（部门层级=第2级）'})

        # 直属上级防成环（相对本安排的校招生 person_id 用户身份）
        dm = attrs.get('direct_manager')
        person_id = attrs.get('person_id', getattr(instance, 'person_id', None))
        if dm is not None and person_id:
            if dm.id == person_id:
                raise serializers.ValidationError(
                    {'directManager': '不能选自己作为直属上级'})
            if is_subordinate_of(person_id, dm.id):
                raise serializers.ValidationError(
                    {'directManager': '不能选下属作为直属上级'})

        # 日期区间：rotation_end >= rotation_start
        start = attrs.get('rotation_start', getattr(instance, 'rotation_start', None))
        end = attrs.get('rotation_end', getattr(instance, 'rotation_end', None))
        if start and end and end < start:
            raise serializers.ValidationError(
                {'rotationEnd': '轮岗结束日期不能早于开始日期'})

        # 容量 / 名额饱和校验（方案 §3.2）：返回 409
        if 'class_room' in attrs:
            class_room = attrs['class_room']
        else:
            class_room = getattr(instance, 'class_room', None)
        if class_room is not None and class_room.capacity is not None:
            bound = RotationArrangement.objects.filter(
                class_room_id=class_room.id, deleted_at__isnull=True,
            ).exclude(id=instance.id if instance else None).count()
            if bound >= class_room.capacity:
                raise CapacityExceeded('班级容量已满')

        if 'mentor' in attrs:
            mentor = attrs['mentor']
        else:
            mentor = getattr(instance, 'mentor', None)
        # 仅当本安排本身处于 ONGOING（或正改为此阶段）时才占用导师名额；
        # PENDING/APPROVING 等非 ONGOING 阶段不计入名额上限。
        if mentor is not None:
            new_stage = attrs.get('stage', getattr(instance, 'stage', None))
            if new_stage == 'ONGOING':
                ongoing = RotationArrangement.objects.filter(
                    mentor_id=mentor.id, stage='ONGOING', deleted_at__isnull=True,
                ).exclude(id=instance.id if instance else None).count()
                if ongoing >= MENTOR_ONGOING_CAPACITY:
                    raise CapacityExceeded('导师名额已饱和')

        return attrs


# ---------------------------------------------------------------------------
# RotationStage（需求 5-8 / S5-21：N 段轮岗，每段独立考核）
# ---------------------------------------------------------------------------
class RotationStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotationStage
        fields = [
            'id', 'arrangement', 'stage_no', 'department', 'mentor',
            'planned_start', 'planned_end', 'actual_start', 'actual_end',
            'assessment_status', 'assessment_result', 'assessed_at', 'assessed_by',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'assessed_at',
            # 考核状态由 15 天规则引擎独占判定，客户端不得直写
            'assessment_status',
        ]

    def validate(self, attrs):
        arrangement = attrs.get('arrangement') or getattr(self.instance, 'arrangement', None)
        stage_no = attrs.get('stage_no') or getattr(self.instance, 'stage_no', None)
        if arrangement and stage_no:
            qs = RotationStage.objects.filter(
                arrangement=arrangement, stage_no=stage_no, deleted_at__isnull=True,
            ).exclude(id=self.instance.id if self.instance else None)
            if qs.exists():
                raise serializers.ValidationError(
                    {'stageNo': '同一轮岗安排的阶段期数必须唯一'})

        department = attrs.get('department')
        if department is not None and not department.is_active:
            raise serializers.ValidationError(
                {'department': '阶段轮岗部门未启用'})

        mentor = attrs.get('mentor')
        if mentor is not None and not user_has_campus_role(mentor.id, 'CAMPUS_MENTOR'):
            raise serializers.ValidationError(
                {'mentor': '阶段带教导师须具备校园导师（CAMPUS_MENTOR）身份'})

        # 日期区间：end >= start（计划与实际分别校验）
        for s_fld, e_fld in (('planned_start', 'planned_end'), ('actual_start', 'actual_end')):
            s = attrs.get(s_fld) or getattr(self.instance, s_fld, None)
            e = attrs.get(e_fld) or getattr(self.instance, e_fld, None)
            if s and e and e < s:
                raise serializers.ValidationError(
                    {e_fld: '结束日期不能早于开始日期'})

        # 考核状态由模型层 save() 的 15 天规则独占判定，客户端不得直写
        # （read_only_fields 已排除，此处再兜一层丢弃显式传入值）
        attrs.pop('assessment_status', None)

        return attrs


# ---------------------------------------------------------------------------
# ConcurrentPostRecord（需求 5-2 / S5-25：兼岗记录 + 摩卡同步预留）
# ---------------------------------------------------------------------------
class ConcurrentPostRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConcurrentPostRecord
        fields = [
            'id', 'person', 'arrangement', 'post_type',
            'effective_from', 'effective_to',
            'sync_status', 'sync_request_id', 'sync_error', 'synced_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            # 同步状态字段由 moka_sync 服务独占写入，客户端不得直写
            'sync_status', 'sync_request_id', 'sync_error', 'synced_at',
        ]

    def validate(self, attrs):
        frm = attrs.get('effective_from') or getattr(self.instance, 'effective_from', None)
        to = attrs.get('effective_to') or getattr(self.instance, 'effective_to', None)
        if frm and to and to < frm:
            raise serializers.ValidationError(
                {'effective_to': '生效止不能早于生效起'})

        post_type = attrs.get('post_type') or getattr(self.instance, 'post_type', None)
        if not post_type:
            raise serializers.ValidationError({'post_type': '兼岗类型必填'})

        return attrs


# ---------------------------------------------------------------------------
# RotationApproval（需求 5-5 / S5-17：轮岗变更审批）
# ---------------------------------------------------------------------------
class RotationApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = RotationApproval
        fields = [
            'id', 'arrangement', 'change_type',
            'old_value', 'new_value', 'reason',
            'status', 'approver', 'approved_at', 'reject_reason',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at',
            # 审批状态/审批人/审批时间由审批动作独占写入
            'status', 'approver', 'approved_at', 'reject_reason',
            # old_value 由服务端从安排当前值快照生成，客户端不得伪造
            'old_value',
        ]

    def validate(self, attrs):
        change_type = attrs.get('change_type') or getattr(self.instance, 'change_type', None)
        if change_type not in dict(RotationApproval.TYPE_CHOICES):
            raise serializers.ValidationError({'change_type': '不支持的变更类型'})

        new_value = attrs.get('new_value')
        if new_value is not None and not str(new_value).strip():
            raise serializers.ValidationError({'new_value': '新值不能为空'})

        return attrs
