"""Candidate Models (PRD v4 §14.3)"""
from django.db import models, transaction
from django_fsm import FSMField, FSMModelMixin, transition
from nanoid import generate as nanoid_generate

from apps.campus_control.constants import MAJORS, SCHOOLS
from apps.common.encryption import EncryptedCharField
from apps.common.models import FullAuditModel, SoftDeleteManager, SoftDeleteModel, TimestampedModel
from apps.reason_library.models import RECRUIT_TYPE_CHOICES, RecruitType

from .audit import AuditImmutabilityError, compute_row_hash


def gen_id():
    return nanoid_generate(size=21)


class CandidateState(models.TextChoices):
    APPLIED = 'APPLIED', '已投递'
    IN_PROCESS = 'IN_PROCESS', '流程中'
    OFFER_SENT = 'OFFER_SENT', '已发Offer'
    PENDING_ONBOARDING = 'PENDING_ONBOARDING', '待入职'
    ONBOARDED = 'ONBOARDED', '已入职'
    PROCESS_FAILED = 'PROCESS_FAILED', '本流程未通过'
    WITHDRAWN = 'WITHDRAWN', '候选人主动撤回'
    TALENT_POOL = 'TALENT_POOL', '公共人才库'
    PROCESS_PAUSED = 'PROCESS_PAUSED', '流程暂停'


class Candidate(FSMModelMixin, FullAuditModel):
    """候选人

    2026-08-03 S3: PII 字段加密
    - id_card_no 改用 EncryptedCharField (DB 存密文, 应用层透明加解密)
    - phone/email 加 PHONE_HASH/EMAIL_HASH 索引字段 (sha256(plaintext), 不可逆, 用于查重)
    - phone/email 仍存明文 (因为需要 FieldAclService 脱敏和 search/filter 频繁使用)
      未来用 AES-SIV 等 deterministic encryption 可全加密, 当前方案是 trade-off
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    # 候选人编号：C + 8 位流水号 (C00000001..)，save() 自动补号，规则对齐 campus_control.Person.code
    code = models.CharField(
        max_length=20, unique=True, blank=True, db_index=True,
        verbose_name='候选人编号', help_text='C+8位流水号, save() 未传时自动补号',
    )
    # 招聘类型硬分区 (social/campus): 社会/校园招聘数据相互隔离, 历史数据默认 social.
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.SOCIAL.value,
        db_index=True, verbose_name='招聘类型',
    )

    # 基本信息
    name = models.CharField(max_length=50, db_index=True, verbose_name='姓名')
    # 2026-10-21 卡 C4: phone / email 改字段级加密（与 id_card_no 同构）。
    #   · Fernet 是**非确定性**加密（每次密文不同）→ 明文 `=` / `icontains` 匹配必然落空，
    #     故**按手机号/邮箱查候选人必须走 hash 盲索引列**（phone_hash / email_hash），
    #     口径与 id_card_no 完全一致（见下方 save() 与 apps/candidate/services.py 的查重）。
    #   · 去掉 db_index：密文索引无意义（每次写入都不同），且 512 字符列建索引徒增存储；
    #     真正的按值查询走 phone_hash / email_hash（两者仍带 db_index）。
    #   · max_length=512：Fernet 密文约 140-160 字符（明文 11 位手机号 / 邮箱），
    #     与 id_card_no 的 512 保持一致；**明文长度限制仍在序列化器层**
    #     （phone max_length=20 / email EmailField 格式校验）。
    phone = EncryptedCharField(max_length=512, verbose_name='手机号')
    phone_hash = models.CharField(
        # 2026-09-27 P0-2: 64 → 80。sha256 hex 恰好 64 字符, 而启用外部 salt 后
        #   哈希带 'v2_' 前缀 = 67 字符, 64 装不下会被截断/报错, 导致查重静默失效。
        #   80 留出冗余 (见 apps.common.encryption.HASH_V2_REQUIRED_MAX_LENGTH,
        #   由 tests/test_encryption_hardening.py 断言本值 >= 该常量, 防止漂移)。
        max_length=80, blank=True, db_index=True,
        verbose_name='手机号 hash (sha256, 用于查重/匿名查询)',
        help_text='hash_for_search(phone) 写入, 同明文 → 同 hash',
    )
    email = EncryptedCharField(
        max_length=512, null=True, blank=True, verbose_name='邮箱',
        help_text='Fernet 加密存储; 查重走 email_hash 列',
    )
    email_hash = models.CharField(
        # 2026-09-27 P0-2: 64 → 80。sha256 hex 恰好 64 字符, 而启用外部 salt 后
        #   哈希带 'v2_' 前缀 = 67 字符, 64 装不下会被截断/报错, 导致查重静默失效。
        #   80 留出冗余 (见 apps.common.encryption.HASH_V2_REQUIRED_MAX_LENGTH,
        #   由 tests/test_encryption_hardening.py 断言本值 >= 该常量, 防止漂移)。
        max_length=80, blank=True, db_index=True,
        verbose_name='邮箱 hash (sha256, 用于查重/匿名查询)',
        help_text='hash_for_search(email) 写入, 同明文 → 同 hash',
    )
    gender = models.CharField(max_length=8, blank=True, verbose_name='性别')
    # 院校标签 / 专业标签：用于全维度 Offer 钩子命中（决策①：性别 + 院校标签 + 专业标签）。
    # 默认空串；取值须对齐 campus_control.constants.SCHOOLS / MAJORS。
    school_tag = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(s, s) for s in SCHOOLS], verbose_name='院校标签',
    )
    major_tag = models.CharField(
        max_length=16, blank=True, default='',
        choices=[(m, m) for m in MAJORS], verbose_name='专业标签',
    )
    age = models.IntegerField(null=True, blank=True, verbose_name='年龄')
    birth_date = models.DateField(null=True, blank=True, verbose_name='出生日期')
    # id_card_no 改用 EncryptedCharField (DB 存密文, 不影响业务代码)
    id_card_no = EncryptedCharField(max_length=512, blank=True, verbose_name='身份证号 (加密存储)')
    # 身份证号 hash (sha256, 不可逆, 用于查重/匿名查询) —— 与 phone_hash/email_hash 同构
    id_card_hash = models.CharField(
        # 2026-09-27 P0-2: 64 → 80。sha256 hex 恰好 64 字符, 而启用外部 salt 后
        #   哈希带 'v2_' 前缀 = 67 字符, 64 装不下会被截断/报错, 导致查重静默失效。
        #   80 留出冗余 (见 apps.common.encryption.HASH_V2_REQUIRED_MAX_LENGTH,
        #   由 tests/test_encryption_hardening.py 断言本值 >= 该常量, 防止漂移)。
        max_length=80, blank=True, db_index=True,
        verbose_name='身份证号 hash (sha256, 用于查重/匿名查询)',
    )

    # 学历/工作
    highest_education = models.CharField(max_length=50, blank=True, verbose_name='最高学历')
    work_years = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name='工作年限')
    current_city = models.CharField(max_length=50, blank=True, verbose_name='当前城市')
    expected_city = models.CharField(max_length=50, blank=True, verbose_name='期望城市')
    current_company = models.CharField(max_length=100, blank=True, verbose_name='当前公司')
    current_position = models.CharField(max_length=100, blank=True, verbose_name='当前职位')
    expected_salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='期望薪资')

    # 简历
    resume_file_url = models.URLField(max_length=500, null=True, blank=True, verbose_name='简历文件URL')
    resume_text = models.TextField(blank=True, verbose_name='简历文本')

    # 来源
    source_channel = models.ForeignKey(
        'channel.Channel', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='candidates',
        verbose_name='来源渠道',
    )
    referrer = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='referred_candidates',
        verbose_name='推荐人',
    )
    referral_type = models.CharField(
        max_length=16, blank=True, db_index=True,
        verbose_name='推荐类型', help_text='N+1/N+2/INTERNAL/SOCIAL',
    )

    # 评分
    resume_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='简历评分')

    # 候选人扩展（来自第三方/Moka）
    extra = models.JSONField(default=dict, blank=True, verbose_name='扩展字段')

    # 当前状态（FSM）
    current_state = FSMField(
        default=CandidateState.APPLIED, db_index=True,
        protected=True, verbose_name='当前状态',
    )

    # 标签
    tags = models.JSONField(default=list, blank=True, verbose_name='标签')

    # 黑名单
    is_blacklisted = models.BooleanField(default=False, db_index=True, verbose_name='是否黑名单')
    blacklist_reason = models.CharField(max_length=200, blank=True, verbose_name='黑名单原因')

    # 摩卡同步
    moka_candidate_id = models.CharField(max_length=100, null=True, blank=True, db_index=True, verbose_name='摩卡候选人ID')

    # 招聘官 / 负责人（批量分配招聘官 batch/assign 用）
    recruiter = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='recruited_candidates',
        verbose_name='招聘官',
    )

    # ===== 简历锁定人（双轨模型）=====
    # 依据《简历模块及特殊简历审批流程调整需求说明》(2026-10-14)：
    # - 正式锁定人：对简历拥有永久分配操作权、是最终责任人；由锁定引擎按规则自动确定与流转，
    #   **任何角色不可手动变更**（故不在任何 serializer 的可写字段中暴露，无写入口）。
    # - 临时锁定人：特定场景下被授予有时效(72h)的分配操作权，与正式锁定人并存、权限同等；
    #   到期由定时任务/Redis 过期事件回收分配权限（保留查看）。
    # 权限判定恒为两者并集，且临时锁须校验未过期：
    #   Q(formal_locked_by=me) | Q(temp_locked_by=me, temp_lock_expires_at__gt=now)
    formal_locked_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='formal_locked_candidates',
        verbose_name='正式锁定人',
        help_text='规则驱动、系统自动确定与流转；不可手动变更',
    )
    temp_locked_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='temp_locked_candidates',
        verbose_name='临时锁定人',
        help_text='72 小时有效，到期回收分配权限（保留查看）',
    )
    temp_lock_expires_at = models.DateTimeField(
        null=True, blank=True, db_index=True, verbose_name='临时锁定到期时间',
    )
    # 乐观锁版本号：正式/临时锁定人并发执行分配时「先到先得」，更新须校验 version 防覆盖
    lock_version = models.PositiveIntegerField(default=0, verbose_name='锁定乐观锁版本号')

    # ===== 简历流转角色（PRD《简历模块及特殊简历审批流程调整需求说明》2026-10-14 兵哥口径）=====
    # 提供人   = referrer（简历推荐人，既有字段，不新增）
    # 上传人   = uploaded_by（实际执行上传操作的用户）
    # 职位分配人 = assigned_by（将简历分配至职位的人）
    uploaded_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='uploaded_candidates',
        verbose_name='简历上传人',
        help_text='实际执行简历上传操作的用户；与提供人(referrer)不一致时授予 72h 临时锁定',
    )
    assigned_by = models.ForeignKey(
        'core.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_candidates',
        verbose_name='职位分配人',
        help_text='将简历成功分配至职位的人；可永久在「我分配的」中查看该简历',
    )

    class AssignState(models.TextChoices):
        """简历生命周期状态（PRD 核心生命周期 3 态），驱动「列表操作权限」：
        待分配=分配/放入人才库/查看；已分配=查看+（锁定人）推进；已归档=仅查看/重新激活。
        """
        PENDING = 'PENDING', '待分配'
        ASSIGNED = 'ASSIGNED', '已分配'
        ARCHIVED = 'ARCHIVED', '已归档'

    assign_state = models.CharField(
        max_length=16, choices=AssignState.choices, default=AssignState.PENDING.value,
        db_index=True, verbose_name='分配状态',
        help_text='简历生命周期状态；与既有 is_archived 并存，后者保留兼容，收敛待后续统一',
    )

    # 归档（批量归档 batch/archive 用，软标志，可逆）
    is_archived = models.BooleanField(default=False, db_index=True, verbose_name='是否归档')
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name='归档时间')

    class Meta:
        db_table = 'candidates'
        verbose_name = '候选人'
        verbose_name_plural = verbose_name
        indexes = [
            # 2026-10-21 卡 C4: 原 Index(['name','phone']) 已撤 —— phone 变密文后
            #   该索引的 phone 部分永远匹配不上（Fernet 每次密文不同），只剩 name 前缀的用处，
            #   而 name 本身已有 db_index。复合索引建在密文列上纯属浪费写入性能。
            models.Index(fields=['source_channel', 'created_at']),
        ]

    def __str__(self):
        """2026-08-03 R15 (寇豆码): 原来返回明文手机号 f'{name} ({phone})'.

        __str__ 会被 Django admin 列表、DRF 错误信息、logger.info('%s', obj)、
        异常栈 repr 等无数地方隐式调用, 等于把手机号成批写进日志文件和
        Sentry event —— 日志系统通常没有 PII 保护策略。改为只保留后 4 位。
        """
        from apps.common.masking import mask_phone_tail
        return f'{self.name} ({mask_phone_tail(self.phone)})'

    def save(self, *args, **kwargs):
        """2026-08-03 S3: 自动同步 phone_hash / email_hash / id_card_hash (查重/匿名查询用).

        只在对应字段改变时重算 hash (避免每次 save 都 hash).
        注意: 这里 import 在函数内避免循环 import.
        id_card_no 是 Fernet 非确定性加密字段, 不能直接 = 匹配, 查重必须走
        不可逆的 id_card_hash (见 apps/common/encryption.hash_for_search), 与
        phone_hash/email_hash 同构.
        """
        from apps.common.encryption import hash_for_search
        # 2026-10-12: 候选人编号自动补号 (C+8位流水号)。未传 code 时事务内锁定末行取
        # 最大序号 +1，避免并发撞 unique 约束 (规则与 campus_control.Person.save 一致)。
        assigned_code = False
        if not self.code:
            with transaction.atomic():
                last = (
                    Candidate.objects
                    .select_for_update()
                    .filter(code__regex=r'^C[0-9]{8}$')
                    .order_by('-code')
                    .first()
                )
                seq = 0
                if last and last.code and last.code.startswith('C'):
                    try:
                        seq = int(last.code[1:9])
                    except (ValueError, IndexError):
                        seq = 0
                # ⚠️ 2026-10-23 修复（与 campus_control.Person.save 对称）：
                #    取号必须**一并看校招档案表（Person）已占用的 C 序列号** ——
                #    两张表同用 C+8 序列，各自独立取号会互相抢占
                #    （实测：档案占 C00000001~C00000058，候选人从 C00000008 起领 →
                #    **51 个号被两边同时占用** → 编号同源时撞 unique，档案无法回填）。
                #    ⚠️ 取号必须**精确匹配 C + 8 位数字**，不能用 `startswith='C'` ——
                #    `import_campus_lifecycle_data` 引入的 `CS` 前缀编号（CS00000878，
                #    实测 878 条）同样以 C 开头，会被 `.order_by('-code')` 选中
                #    → `int('S0000087')` 解析失败 → seq 归 0 → 抢已占用的号。
                #    （局部导入：candidate app 依赖 campus_control.constants，避免 app 间 import 环）
                try:
                    from apps.campus_control.models import Person
                    person_last = (
                        Person.all_objects
                        .filter(code__regex=r'^C[0-9]{8}$')
                        .order_by('-code')
                        .first()
                    )
                    if person_last and person_last.code:
                        seq = max(seq, int(person_last.code[1:9]))
                except (ImportError, ValueError, IndexError):
                    pass
                self.code = f'C{seq + 1:08d}'
            assigned_code = True
        # 计算 hash (无论是否变化, 简单起见都重算; 候选人 save 不频繁)
        new_phone_hash = hash_for_search(self.phone) if self.phone else ''
        new_email_hash = hash_for_search(self.email) if self.email else ''
        new_id_card_hash = hash_for_search(self.id_card_no) if self.id_card_no else ''
        # 写进 instance 字段 (save 不会自动加 update_fields 之外的)
        if self.pk:
            old = Candidate.objects.filter(pk=self.pk).only(
                'phone', 'email', 'id_card_no',
            ).first()
            if old:
                if old.phone != self.phone:
                    self.phone_hash = new_phone_hash
                if old.email != self.email:
                    self.email_hash = new_email_hash
                if old.id_card_no != self.id_card_no:
                    self.id_card_hash = new_id_card_hash
            else:
                self.phone_hash = new_phone_hash
                self.email_hash = new_email_hash
                self.id_card_hash = new_id_card_hash
        else:
            self.phone_hash = new_phone_hash
            self.email_hash = new_email_hash
            self.id_card_hash = new_id_card_hash

        # 决定 update_fields: 如果只 save 一个字段, 不应该覆盖 hash
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            # 任一源字段变化都带上对应的 hash 字段, 避免 hash 与明文不一致
            if 'phone' in update_fields:
                update_fields.add('phone_hash')
            if 'email' in update_fields:
                update_fields.add('email_hash')
            if 'id_card_no' in update_fields:
                update_fields.add('id_card_hash')
            # 本次 save 内补号的 code 必须一并写入, 否则编号只留在内存、DB 仍为空
            if assigned_code:
                update_fields.add('code')
            kwargs['update_fields'] = frozenset(update_fields)
        super().save(*args, **kwargs)

    def get_current_state_display(self):
        """current_state 的中文展示名。

        ``current_state`` 是 ``FSMField`` 且未声明 ``choices``，Django 不会
        自动生成 ``get_<field>_display``；而 List/Detail 两个序列化器的
        ``state_display`` 均以 ``source='get_current_state_display'`` 取值，
        缺该方法时该字段解析抛 AttributeError 被静默丢弃 → 前端拿不到状态/流程阶段。
        这里显式从 ``CandidateState`` 枚举取 label，保证 ``state_display`` 正常出参。
        """
        try:
            return CandidateState(self.current_state).label
        except ValueError:
            return self.current_state or ''

    # === 状态机转换 ===
    @transition(field=current_state, source=CandidateState.APPLIED, target=CandidateState.IN_PROCESS)
    def enter_process(self):
        """进入流程"""
        pass

    @transition(field=current_state, source=CandidateState.IN_PROCESS, target=CandidateState.OFFER_SENT)
    def send_offer(self):
        """发送 Offer"""
        pass

    @transition(
        field=current_state,
        source=[CandidateState.APPLIED, CandidateState.IN_PROCESS, CandidateState.OFFER_SENT],
        target=CandidateState.TALENT_POOL,
    )
    def move_to_pool(self, reason='TIMEOUT'):
        """入库(从 APPLIED / IN_PROCESS / OFFER_SENT 任一态可入人才库)"""
        # 原有 service 守卫也允许 APPLIED, 保持向后兼容 —— APPLIED 候选人
        # 可在进入流程前被业务侧直接入人才库(无需先 enter_process)。
        pass

    # ── 2026-08-03 BUG-5 修复: 补齐缺失的 5 个状态机 transition ──
    # 此前这 5 个状态变更在 service 层直接给 FSMField 赋值, django-fsm 的
    # protected=True 会抛 AttributeError: Direct current_state modification is
    # not allowed, 导致 5 个候选人接口稳定 500。改为在模型上声明 @transition,
    # 由 FSM 统一校验 source(source 集合见软件架构师 docs/PHASE2_DESIGN §12)。
    # 原则: source 宁窄勿宽 —— 窄了合法操作得 409(可见可快速放宽),
    # 宽了非法流转静默污染数据(不可见)。

    @transition(
        field=current_state,
        source=[CandidateState.OFFER_SENT, CandidateState.PENDING_ONBOARDING],
        target=CandidateState.ONBOARDED,
    )
    def mark_onboarded(self):
        """完成入职 → 已入职"""
        # PENDING_ONBOARDING 当前是孤儿状态(全仓无代码写入), 保留以预留
        # 将来 Offer FSM 联动写候选人的接入点(见 PHASE2_DESIGN Q10)。
        pass

    @transition(
        field=current_state,
        source=[
            CandidateState.APPLIED,
            CandidateState.IN_PROCESS,
            CandidateState.OFFER_SENT,
            CandidateState.PENDING_ONBOARDING,
            CandidateState.PROCESS_PAUSED,
        ],
        target=CandidateState.WITHDRAWN,
    )
    def withdraw(self, reason=''):
        """候选人主动撤回 → 已撤回"""
        # 排除 ONBOARDED(已入职撤回=离职, 属另一业务域) / PROCESS_FAILED /
        # WITHDRAWN(终态) / TALENT_POOL(应走人才库移除)。
        pass

    @transition(
        field=current_state,
        source=[
            CandidateState.APPLIED,
            CandidateState.IN_PROCESS,
            CandidateState.OFFER_SENT,
            CandidateState.PROCESS_PAUSED,
        ],
        target=CandidateState.PROCESS_FAILED,
    )
    def mark_process_failed(self):
        """本流程未通过 → 终态"""
        # PROCESS_PAUSED 纳入: 暂停中可直接判失败, 避免先 resume 再 fail 的
        # 无意义跳变污染历史。PENDING_ONBOARDING 是否纳入待产品拍板(Q9), 先窄。
        pass

    @transition(
        field=current_state,
        source=CandidateState.IN_PROCESS,
        target=CandidateState.PROCESS_PAUSED,
    )
    def pause_process(self):
        """流程暂停(仅 IN_PROCESS 可暂停)"""
        pass

    @transition(
        field=current_state,
        source=CandidateState.PROCESS_PAUSED,
        target=CandidateState.IN_PROCESS,
    )
    def resume_process(self):
        """恢复流程: 单一 source → 必然无损回到 IN_PROCESS, 无需 previous_state"""
        # resume 的 source 仅 PROCESS_PAUSED 一个, 故恢复回 IN_PROCESS 是定理
        # 而非假设 —— 从 OFFER_SENT 等调 pause 直接 409, 不可能静默丢状态。
        pass


class CandidateTag(SoftDeleteModel):
    """候选人标签字典"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名')
    color = models.CharField(max_length=20, default='blue', verbose_name='颜色')
    category = models.CharField(max_length=32, blank=True, verbose_name='分类')

    class Meta:
        db_table = 'candidate_tags'
        verbose_name = '候选人标签'
        verbose_name_plural = verbose_name



    objects = SoftDeleteManager()
    all_objects = models.Manager()
class CandidateHistory(FullAuditModel):
    """候选人操作历史 - 自动审计（不可篡改：哈希链 + 禁改删）

    - ``seq``：每候选人内单调递增序号；``prev_hash`` 指向上条的 ``row_hash``，串成哈希链。
    - ``save()`` 在 INSERT 时自动补 seq/哈希；对既有行 UPDATE 或 ``delete()`` 抛
      ``AuditImmutabilityError``（软删亦走 ``save()``，同样被拦）。
    - ``row_hash`` 刻意不含 ``created_at``（auto_now_add 会覆盖，纳入会致哈希与落库值不一致）。
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE,
        related_name='histories', verbose_name='候选人',
    )
    action = models.CharField(max_length=64, verbose_name='操作')
    detail = models.JSONField(default=dict, blank=True, verbose_name='详情')
    seq = models.PositiveIntegerField(default=0, db_index=True, verbose_name='序号')
    # 2026-10-23 卡 C4（决策A·J6）：64 → 80。sha256 hexdigest **恰好 64 字符** = 列宽零余量，
    #   哈希口径一改（加 'v2_' 版本前缀 / 换摘要算法）就撑爆列；审计链一旦撑爆，
    #   ``histories/verify`` 会整链报 broken_at ⇒ 改口径前必须先留余量。
    #   80 与 PII 盲索引列（phone_hash / email_hash）同档，
    #   下限由 audit.AUDIT_HASH_REQUIRED_MAX_LENGTH 固化，并由 tests/test_audit.py 断言防漂移。
    prev_hash = models.CharField(max_length=80, blank=True, default='', verbose_name='上一行哈希')
    row_hash = models.CharField(max_length=80, blank=True, default='', db_index=True, verbose_name='行哈希')

    class Meta:
        db_table = 'candidate_histories'
        verbose_name = '候选人历史'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # 不可篡改：既有行禁止 UPDATE（软删 restore 亦走 save，一并拦截）
        if self.pk and not self._state.adding:
            raise AuditImmutabilityError(
                f'CandidateHistory 行不可修改/删除（不可篡改审计）: id={self.pk}'
            )
        if self._state.adding:
            # INSERT：在事务内取该候选人当前最大 seq 行（select_for_update 串行化并发插入），
            # 续接哈希链。sqlite 测试库忽略 FOR UPDATE（无锁但不报错）。
            with transaction.atomic():
                last = (
                    CandidateHistory.objects
                    .filter(candidate_id=self.candidate_id)
                    .select_for_update()
                    .order_by('-seq', '-created_at')
                    .first()
                )
                self.seq = (last.seq + 1) if last else 1
                self.prev_hash = (last.row_hash or '') if last else ''
                self.row_hash = compute_row_hash(
                    self.candidate_id, self.seq, self.action, self.detail,
                    self.created_by_id, self.prev_hash,
                )
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutabilityError(
            f'CandidateHistory 行不可删除（不可篡改审计）: id={self.pk}'
        )


class CandidateFieldValue(TimestampedModel):
    """候选人扩展字段值存储（标准简历配置中无 Candidate 模型对应列的字段）

    键: (candidate_id, field_key); field_key 取标准简历配置中的英文 fieldKey
    (Mobile/Email/Gender/...)。值以 JSON 存, 支持文本/数字/列表等任意类型。
    详情页「基本信息」tab 对无模型列的扩展字段从此处取值; 编辑简历功能向其写入。
    """
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE,
        related_name='field_values', verbose_name='候选人',
    )
    field_key = models.CharField(max_length=128, verbose_name='字段 Key')
    value = models.JSONField(null=True, blank=True, verbose_name='字段值')

    class Meta:
        db_table = 'candidate_field_values'
        unique_together = [('candidate', 'field_key')]
        verbose_name = '候选人字段值'
        verbose_name_plural = verbose_name
        ordering = ['field_key']

    def __str__(self):
        return f'CandidateFieldValue({self.candidate_id}/{self.field_key})'


# ============================================================
# 候选人维度批量操作审计记录（G9 PRD：前端 /candidates/batch/* 真实后端）
# 注意：process app 的 CandidateScreen / CandidateRecommendation 是「流程维度」
# （挂在 RecruitmentProcess 下）。此处是「候选人维度」批量初筛 / 推荐到职位，
# 语义不同，故独立建模型，不复用流程维度表。
# ============================================================
class CandidateScreening(SoftDeleteModel):
    """候选人维度批量初筛记录 — 审计+查询

    POST /api/v1/candidates/batch/screen/ 写入（区别于 process 维度的 CandidateScreen）。
    """
    SCREEN_RESULTS = [
        ('PASS', '通过'),
        ('FAIL', '不通过'),
        ('KEEP', '待议'),
    ]

    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT,
        related_name='screening_records', verbose_name='候选人',
    )
    result = models.CharField(
        max_length=16, choices=SCREEN_RESULTS, default='PASS', verbose_name='初筛结果',
    )
    comment = models.TextField(blank=True, verbose_name='初筛备注')
    screener = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='candidate_screenings', verbose_name='初筛人',
    )
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.SOCIAL.value,
        db_index=True, verbose_name='招聘类型',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='初筛时间')

    class Meta:
        db_table = 'candidate_screenings'
        verbose_name = '候选人初筛记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['candidate', 'result']),
            models.Index(fields=['screener', 'created_at']),
        ]

    def __str__(self):
        return f'CandidateScreening[{self.candidate_id}] {self.result}'

    objects = SoftDeleteManager()
    all_objects = models.Manager()


class CandidatePositionRecommendation(SoftDeleteModel):
    """候选人 ↔ 职位 推荐记录 — 审计+查询

    POST /api/v1/candidates/batch/recommend/ 写入（区别于 process 维度的 CandidateRecommendation）。
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.PROTECT,
        related_name='position_recommendations', verbose_name='候选人',
    )
    position = models.ForeignKey(
        'position.Position', on_delete=models.PROTECT,
        related_name='candidate_recommendations', verbose_name='推荐职位',
    )
    reason = models.TextField(blank=True, verbose_name='推荐理由')
    recommender = models.ForeignKey(
        'core.User', on_delete=models.PROTECT,
        related_name='position_recommendations', verbose_name='推荐人',
    )
    recruit_type = models.CharField(
        max_length=16, choices=RECRUIT_TYPE_CHOICES, default=RecruitType.SOCIAL.value,
        db_index=True, verbose_name='招聘类型',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='推荐时间')

    class Meta:
        db_table = 'candidate_position_recommendations'
        verbose_name = '候选人职位推荐记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['candidate', 'position']),
            models.Index(fields=['recommender', 'created_at']),
        ]

    def __str__(self):
        return f'CandidatePositionRecommendation[{self.candidate_id}→{self.position_id}]'

    objects = SoftDeleteManager()
    all_objects = models.Manager()


# ============================================================
# 候选人详情页五项操作中「关注 / 转发」的持久化模型
#
# 设计取舍（2026-10-19）：
# - 关注为**个人级**语义（兵哥拍板），故主键是 (candidate, user) 复合唯一，
#   关注状态仅本人可见，不复用候选人标签（标签是团队共享的，语义不同）。
# - 转发为**发送给内部同事**，落 CandidateForward（候选人 × 接收人 × 转发人），
#   与「推荐到职位」（CandidatePositionRecommendation，写职位）语义区分开。
# - 二者均落地为可查询业务表（而非只写审计），因为前端需要回显关注状态、
#   展示「谁转给了谁」；同时各自另写一条 CandidateHistory 进哈希链，保证可溯源。
# ============================================================
class CandidateFollow(TimestampedModel):
    """个人级关注候选人（收藏）— 关注状态仅本人可见。

    2026-10-19：详情页「关注候选人」入口。复合唯一 (candidate, user) 保证
    重复关注幂等（前端可无脑重复调用）。
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE,
        related_name='follows', verbose_name='候选人',
    )
    user = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='candidate_follows', verbose_name='关注人',
    )

    class Meta:
        db_table = 'candidate_follows'
        unique_together = [('candidate', 'user')]
        verbose_name = '候选人关注'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'candidate']),
        ]

    def __str__(self):
        return f'CandidateFollow[{self.user_id}→{self.candidate_id}]'


class CandidateForward(SoftDeleteModel):
    """候选人转发给内部同事的记录 — 审计 + 查询。

    2026-10-19：详情页「转发候选人」入口。区别于「推荐其他职位」
    （CandidatePositionRecommendation 写职位），此处接收方是**用户**。
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE,
        related_name='forwards', verbose_name='候选人',
    )
    from_user = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='forwarded_candidates', verbose_name='转发人',
    )
    to_user = models.ForeignKey(
        'core.User', on_delete=models.CASCADE,
        related_name='received_forwards', verbose_name='接收人',
    )
    note = models.TextField(blank=True, verbose_name='附言')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='转发时间')

    class Meta:
        db_table = 'candidate_forwards'
        verbose_name = '候选人转发记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['candidate', '-created_at']),
            models.Index(fields=['to_user', '-created_at']),
        ]

    def __str__(self):
        return f'CandidateForward[{self.from_user_id}→{self.to_user_id}:{self.candidate_id}]'

    objects = SoftDeleteManager()
    all_objects = models.Manager()
