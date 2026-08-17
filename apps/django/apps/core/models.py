"""Core Models

- User: 用户（扩展 Django AbstractUser）
- Department: 部门（树形结构）
- Permission: V1 权限表（managed=False, T01.2 计划清理）
- RolePermission: V1 角色-权限关联（managed=False, T01.2 计划清理）

2026-08-03 (寇豆码 T01.1):
- 删除 Role (db_table='roles') V1 影子模型 — 与 RoleV2 (db_table='roles') 同表冲突
- 删除 UserRole (db_table='user_roles') V1 影子模型 — 与 UserRoleV2 (db_table='user_roles') 同表冲突
- Permission / RolePermission 仍被 init_demo_data.py 与 migrate_v2_data.py 引用,
  暂保留 (managed=False) 留 T01.2 处理
- 调用 Role/UserRole 的管理命令 (migrate_v2_data.py / init_demo_data.py)
  会因 ImportError 而失败, 这是 T01.2 范围
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """自定义 User Manager - 用手机号/工号登录"""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        return self.create_user(username, password, **extra_fields)

    def active(self):
        return self.filter(is_active=True, deleted_at__isnull=True)


class User(AbstractUser):
    """用户模型

    扩展字段：
    - employee_id: 工号
    - phone: 手机号
    - avatar: 头像 URL
    - department: 所属部门
    - direct_manager: 直接上级
    - position_title: 职务
    - level: 职级
    - bu_president: 所属 BU 总裁
    - solid_vp / dotted_vp: 实线/虚线 VP
    - last_login_at: 最后登录时间
    - moka_user_id: 摩卡系统用户 ID（同步用）
    """
    employee_id = models.CharField(max_length=50, unique=True, null=True, blank=True, verbose_name='工号')
    phone = models.CharField(max_length=20, null=True, blank=True, db_index=True, verbose_name='手机号')
    avatar = models.URLField(max_length=500, null=True, blank=True, verbose_name='头像')

    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members',
        verbose_name='所属部门',
    )
    direct_manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='subordinates',
        verbose_name='直接上级',
    )

    # 职级/职务（来自摩卡字典）
    position_title = models.CharField(max_length=100, null=True, blank=True, verbose_name='职务')
    level = models.CharField(max_length=50, null=True, blank=True, db_index=True, verbose_name='职级')

    # 组织关系（V4.0 新增）
    bu_president = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='BU 总裁',
    )
    solid_vp = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='实线 VP',
    )
    dotted_vp = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='虚线 VP',
    )

    # 摩卡同步
    moka_user_id = models.CharField(max_length=100, null=True, blank=True, db_index=True, verbose_name='摩卡用户ID')

    # 抢单 ROUND_ROBIN
    last_assignment_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='上次被分配时间')

    # 软删除
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='删除时间')

    # 时间戳
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name='最后登录时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    objects = UserManager()

    # 解决 auth.User 反向访问冲突
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='ats_user_set',
        blank=True,
        verbose_name='组',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='ats_user_permissions',
        blank=True,
        verbose_name='用户权限',
    )

    class Meta:
        # 注：使用 auth_user 默认表名（不重命名），与 Django auth 系统完全兼容
        # 如果要重命名表，需在 settings 中设置 AUTH_USER_MODEL = 'core.User' 并清空所有迁移重建
        verbose_name = '用户'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['department', 'is_active']),
            models.Index(fields=['level']),
        ]

    def __str__(self):
        return f'{self.username}({self.employee_id or self.id})'

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def soft_delete(self):
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=['deleted_at', 'is_active', 'updated_at'])


class Department(models.Model):
    """部门 - 树形结构"""
    id = models.CharField(max_length=32, primary_key=True)
    name = models.CharField(max_length=100, verbose_name='部门名称')
    code = models.CharField(max_length=50, unique=True, verbose_name='部门编码')
    parent = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='children',
        verbose_name='上级部门',
    )
    path = models.CharField(max_length=500, blank=True, verbose_name='路径', help_text='/root/dept1/dept2/')
    sort_order = models.IntegerField(default=0, verbose_name='排序')

    leader = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='+',
        verbose_name='部门负责人',
    )

    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments'
        verbose_name = '部门'
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from nanoid import generate as nanoid_generate
        if not self.id:
            self.id = nanoid_generate(size=21)
        if self.parent and not self.path:
            self.path = f'{self.parent.path}/{self.name}'
        elif not self.path:
            self.path = f'/{self.name}'
        super().save(*args, **kwargs)

    def get_ancestors(self):
        """获取所有祖先部门"""
        ancestors = []
        node = self.parent
        while node:
            ancestors.append(node)
            node = node.parent
        return ancestors

    def get_descendants(self):
        """获取所有后代部门"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants


class Permission(models.Model):
    """权限 (V1 残留)

    2026-08-03 T01.1 (寇豆码): 暂保留, 因 init_demo_data.py 仍 import.
    T01.2 会改为直接用 PermissionResource (V2 资源表) + 清理 init_demo_data.

    不加 managed=False (避免 migration drift): 0001 已建好 `permissions` 表,
    字段与本 model 一致, Django 自动管理. 等 T01.2 删除此 model 时再加
    managed=False 防止误操作.
    """
    id = models.CharField(max_length=32, primary_key=True)
    code = models.CharField(max_length=100, unique=True, verbose_name='权限编码', help_text='如 stage:create')
    name = models.CharField(max_length=100, verbose_name='权限名称')
    module = models.CharField(max_length=50, db_index=True, verbose_name='模块')
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'permissions'
        verbose_name = '权限'
        verbose_name_plural = verbose_name

    def save(self, *args, **kwargs):
        from nanoid import generate as nanoid_generate
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)


class UserPreference(models.Model):
    """用户偏好（UI 等），按用户存储，跟随账号而非浏览器。

    - settings: JSON 字典。当前使用键：
        - menu_layout: 'side'（左侧竖排，默认）| 'top'（顶部横排）
      保留扩展空间，后续可加主题、密度等 UI 偏好。
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='preference', verbose_name='用户'
    )
    settings = models.JSONField(default=dict, blank=True, verbose_name='偏好设置')

    class Meta:
        verbose_name = '用户偏好'
        verbose_name_plural = '用户偏好'

    def __str__(self):
        return f'用户偏好(uid={self.user_id})'

    @classmethod
    def get_for_user(cls, user):
        """取或建当前用户的偏好（保证单例行存在）。"""
        obj, _ = cls.objects.get_or_create(user=user, defaults={'settings': {}})
        return obj

    def get_menu_layout(self) -> str:
        layout = (self.settings or {}).get('menu_layout', 'side')
        return layout if layout in ('side', 'top') else 'side'


# ---- V2 权限系统 (spec §3.2, T2) ----
# 显式 import 让 Django 注册器发现 V2 models (V1/V2 共存于 T17 drop_old 前)
from .models_permission_v2 import (  # noqa: E402,F401
    PermissionResource,
    PermissionTemplate,
    RoleV2,
    RolePermissionV2,
    ManagementUnit,
    UserRoleV2,
    TenantConfig,
)
