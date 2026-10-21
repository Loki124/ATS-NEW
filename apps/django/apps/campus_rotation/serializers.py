"""campus_rotation 序列化器。

负责：
- 字段暴露（camelCase 由 djangorestframework-camel-case 自动转换）；
- 写时业务校验（BU 二级部门 / 身份角色 / 字典启用 / 直属上级防成环 / 日期区间）；
- 只读聚合字段 campus_count（直播间）、student_count（班级）。
"""
from rest_framework import serializers

from .models import ClassRoom, LiveRoom, RotationArrangement, ServiceDept
from .validators import (
    CapacityExceeded,
    MENTOR_ONGOING_CAPACITY,
    dict_key_active,
    is_bu_depth,
    is_subordinate_of,
    resolve_intent_bu,
    user_has_campus_role,
)


# ---------------------------------------------------------------------------
# LiveRoom
# ---------------------------------------------------------------------------
class LiveRoomSerializer(serializers.ModelSerializer):
    # 只读聚合字段（不落库）：按直播间归属部门 + 在校（ONGOING）状态统计校招生占用。
    campus_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = LiveRoom
        fields = [
            'id', 'room_no', 'name', 'department', 'bu', 'mentor',
            'platform', 'brand', 'location', 'capacity', 'social_count',
            'is_active', 'remark', 'created_at', 'updated_at', 'campus_count',
        ]
        read_only_fields = ['id', 'room_no', 'created_at', 'updated_at', 'campus_count']

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

        platform = attrs.get('platform')
        if platform and not dict_key_active('LIVE_ROOM_PLATFORM', platform):
            raise serializers.ValidationError(
                {'platform': '平台字典项不存在或未启用'})

        brand = attrs.get('brand')
        if brand and not dict_key_active('BRAND', brand):
            raise serializers.ValidationError(
                {'brand': '品牌字典项不存在或未启用'})

        location = attrs.get('location')
        if location and not dict_key_active('LOCATION', location):
            raise serializers.ValidationError(
                {'location': '地点字典项不存在或未启用'})
        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        count = 0
        if instance.department_id:
            count = RotationArrangement.objects.filter(
                current_dept_id=instance.department_id, stage='ONGOING',
            ).count()
        ret['campusCount'] = count
        return ret


# ---------------------------------------------------------------------------
# ServiceDept
# ---------------------------------------------------------------------------
class ServiceDeptSerializer(serializers.ModelSerializer):
    # 只读聚合字段（不落库）：按客服部门归属 + 在校（ONGOING）状态统计校招生占用。
    campus_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ServiceDept
        fields = [
            'id', 'dept_no', 'name', 'department', 'bu', 'brand',
            'location', 'capacity', 'cs_supervisor', 'cs_type',
            'workstation_type', 'need_training_cert', 'social_count',
            'is_active', 'remark', 'created_at', 'updated_at', 'campus_count',
        ]
        read_only_fields = ['id', 'dept_no', 'created_at', 'updated_at', 'campus_count']

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

        cs_supervisor = attrs.get('cs_supervisor')
        if cs_supervisor is not None and not user_has_campus_role(cs_supervisor.id, 'CAMPUS_MENTOR'):
            raise serializers.ValidationError(
                {'csSupervisor': '客服主管须具备校园导师（CAMPUS_MENTOR）身份'})

        location = attrs.get('location')
        if location and not dict_key_active('LOCATION', location):
            raise serializers.ValidationError(
                {'location': '地点字典项不存在或未启用'})

        # cs_type / workstation_type / brand 字典校验（S5-13 已建字典并启用）。
        cs_type = attrs.get('cs_type')
        if cs_type and not dict_key_active('CS_TYPE', cs_type):
            raise serializers.ValidationError(
                {'csType': '客服类型字典项不存在或未启用'})

        workstation_type = attrs.get('workstation_type')
        if workstation_type and not dict_key_active('WORKSTATION_TYPE', workstation_type):
            raise serializers.ValidationError(
                {'workstationType': '工位类型字典项不存在或未启用'})

        brand = attrs.get('brand')
        if brand and not dict_key_active('BRAND', brand):
            raise serializers.ValidationError(
                {'brand': '品牌字典项不存在或未启用'})

        return attrs

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        count = 0
        if instance.id:
            count = RotationArrangement.objects.filter(
                service_dept_id=instance.id, stage='ONGOING', deleted_at__isnull=True,
            ).count()
        ret['campusCount'] = count
        return ret


# ---------------------------------------------------------------------------
# ClassRoom
# ---------------------------------------------------------------------------
class ClassRoomSerializer(serializers.ModelSerializer):
    # 只读聚合字段：该班级绑定的校招生人数。
    student_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = ClassRoom
        fields = [
            'id', 'code', 'name', 'head_teacher', 'hrbp',
            'batch', 'capacity', 'remark', 'created_at', 'updated_at', 'student_count',
        ]
        read_only_fields = ['id', 'code', 'created_at', 'updated_at', 'student_count']

    def validate(self, attrs):
        head_teacher = attrs.get('head_teacher')
        if head_teacher is not None and not user_has_campus_role(head_teacher.id, 'HEAD_TEACHER'):
            raise serializers.ValidationError(
                {'headTeacher': '班主任须具备 HEAD_TEACHER 身份'})
        return attrs

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
    class Meta:
        model = RotationArrangement
        fields = [
            'id', 'person_id', 'intent_bu', 'suggest_dept', 'suggest_mentor',
            'head_teacher', 'current_dept', 'mentor', 'direct_manager',
            'class_room', 'service_dept', 'stage', 'employee_status', 'rotation_start',
            'rotation_end', 'rank', 'final_dept', 'result', 'note',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, attrs):
        instance = self.instance

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
