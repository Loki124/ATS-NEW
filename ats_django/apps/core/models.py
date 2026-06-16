"""Core Models

- User: 用户（扩展 Django AbstractUser）
- Department: 部门（树形结构）
- Role: 角色
- Permission: 权限
- UserRole: 用户-角色多对多
- RolePermission: 角色-权限多对多
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


class Role(models.Model):
    """角色

    预置角色（PRD §4）：
    - SUPER_ADMIN: 超级-产线（系统管理员）
    - HRBP: HRBP
    - HR: HR（招聘专员）
    - HIRING_MANAGER: 用人经理
    - INTERVIEWER: 面试官
    - REFERRER: 推荐人
    - HR_DIRECTOR: HR 负责人
    - CHO: CHO
    - AUDITOR: 审计人员
    """
    id = models.CharField(max_length=32, primary_key=True)
    code = models.CharField(max_length=50, unique=True, verbose_name='角色编码')
    name = models.CharField(max_length=100, verbose_name='角色名称')
    description = models.TextField(blank=True, verbose_name='描述')

    is_builtin = models.BooleanField(default=False, verbose_name='内置')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='启用')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'roles'
        verbose_name = '角色'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        from nanoid import generate as nanoid_generate
        if not self.id:
            self.id = nanoid_generate(size=21)
        super().save(*args, **kwargs)


class Permission(models.Model):
    """权限"""
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


class UserRole(models.Model):
    """用户-角色关联"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True, blank=True,
        help_text='角色限定部门（NULL 表示全公司）',
    )
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='+')

    class Meta:
        db_table = 'user_roles'
        unique_together = [('user', 'role', 'department')]
        verbose_name = '用户角色'
        verbose_name_plural = verbose_name


class RolePermission(models.Model):
    """角色-权限关联"""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE)

    class Meta:
        db_table = 'role_permissions'
        unique_together = [('role', 'permission')]
        verbose_name = '角色权限'
        verbose_name_plural = verbose_name
