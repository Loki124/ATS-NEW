"""Candidate Models (PRD v4 §14.3)"""
from django.db import models
from django_fsm import FSMField, transition
from apps.common.models import FullAuditModel
from apps.common.encryption import EncryptedCharField
from nanoid import generate as nanoid_generate


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


class Candidate(FullAuditModel):
    """候选人

    2026-08-03 S3: PII 字段加密
    - id_card_no 改用 EncryptedCharField (DB 存密文, 应用层透明加解密)
    - phone/email 加 PHONE_HASH/EMAIL_HASH 索引字段 (sha256(plaintext), 不可逆, 用于查重)
    - phone/email 仍存明文 (因为需要 FieldAclService 脱敏和 search/filter 频繁使用)
      未来用 AES-SIV 等 deterministic encryption 可全加密, 当前方案是 trade-off
    """
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)

    # 基本信息
    name = models.CharField(max_length=50, db_index=True, verbose_name='姓名')
    phone = models.CharField(max_length=20, db_index=True, verbose_name='手机号')
    phone_hash = models.CharField(
        max_length=64, blank=True, db_index=True,
        verbose_name='手机号 hash (sha256, 用于查重/匿名查询)',
        help_text='hash_for_search(phone) 写入, 同明文 → 同 hash',
    )
    email = models.EmailField(max_length=100, db_index=True, null=True, blank=True, verbose_name='邮箱')
    email_hash = models.CharField(
        max_length=64, blank=True, db_index=True,
        verbose_name='邮箱 hash (sha256, 用于查重/匿名查询)',
    )
    gender = models.CharField(max_length=8, blank=True, verbose_name='性别')
    age = models.IntegerField(null=True, blank=True, verbose_name='年龄')
    birth_date = models.DateField(null=True, blank=True, verbose_name='出生日期')
    # id_card_no 改用 EncryptedCharField (DB 存密文, 不影响业务代码)
    id_card_no = EncryptedCharField(max_length=512, blank=True, verbose_name='身份证号 (加密存储)')

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

    class Meta:
        db_table = 'candidates'
        verbose_name = '候选人'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['name', 'phone']),
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
        """2026-08-03 S3: 自动同步 phone_hash / email_hash (查重/匿名查询用).

        只在 phone/email 改变时重算 hash (避免每次 save 都 hash).
        注意: 这里 import 在函数内避免循环 import.
        """
        from apps.common.encryption import hash_for_search
        # 计算 hash (无论是否变化, 简单起见都重算; 候选人 save 不频繁)
        new_phone_hash = hash_for_search(self.phone) if self.phone else ''
        new_email_hash = hash_for_search(self.email) if self.email else ''
        # 写进 instance 字段 (save 不会自动加 update_fields 之外的)
        if self.pk:
            old = Candidate.objects.filter(pk=self.pk).only('phone', 'email').first()
            if old:
                if old.phone != self.phone:
                    self.phone_hash = new_phone_hash
                if old.email != self.email:
                    self.email_hash = new_email_hash
            else:
                self.phone_hash = new_phone_hash
                self.email_hash = new_email_hash
        else:
            self.phone_hash = new_phone_hash
            self.email_hash = new_email_hash

        # 决定 update_fields: 如果只 save 一个字段, 不应该覆盖 hash
        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            # 如果显式指定了 update_fields 且不包含 hash 字段, 自动加上
            if 'phone_hash' not in update_fields and (
                'phone' in update_fields or 'email' in update_fields
            ):
                update_fields = set(update_fields)
                if 'phone' in update_fields:
                    update_fields.add('phone_hash')
                if 'email' in update_fields:
                    update_fields.add('email_hash')
                kwargs['update_fields'] = frozenset(update_fields)
        super().save(*args, **kwargs)

    # === 状态机转换 ===
    @transition(field=current_state, source=CandidateState.APPLIED, target=CandidateState.IN_PROCESS)
    def enter_process(self):
        """进入流程"""
        pass

    @transition(field=current_state, source=CandidateState.IN_PROCESS, target=CandidateState.OFFER_SENT)
    def send_offer(self):
        """发送 Offer"""
        pass

    @transition(field=current_state, source=[CandidateState.IN_PROCESS, CandidateState.OFFER_SENT], target=CandidateState.TALENT_POOL)
    def move_to_pool(self, reason='TIMEOUT'):
        """入库"""
        pass


class CandidateTag(models.Model):
    """候选人标签字典"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    name = models.CharField(max_length=50, unique=True, verbose_name='标签名')
    color = models.CharField(max_length=20, default='blue', verbose_name='颜色')
    category = models.CharField(max_length=32, blank=True, verbose_name='分类')

    class Meta:
        db_table = 'candidate_tags'
        verbose_name = '候选人标签'
        verbose_name_plural = verbose_name


class CandidateHistory(FullAuditModel):
    """候选人操作历史 - 自动审计"""
    id = models.CharField(max_length=32, primary_key=True, default=gen_id)
    candidate = models.ForeignKey(
        Candidate, on_delete=models.CASCADE,
        related_name='histories', verbose_name='候选人',
    )
    action = models.CharField(max_length=64, verbose_name='操作')
    detail = models.JSONField(default=dict, blank=True, verbose_name='详情')

    class Meta:
        db_table = 'candidate_histories'
        verbose_name = '候选人历史'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
