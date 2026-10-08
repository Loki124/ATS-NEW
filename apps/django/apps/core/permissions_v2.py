"""V2 权限 DRF 接入层. V2Permission 校验资源级权限, ScopeQuerysetMixin 做数据级过滤."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models_permission_v2 import PermissionResource
from .permission_check import has_perm
from .role_v2_query import is_super_admin
from .scope_resolver import ALL_UNIT_SENTINEL, resolve_scope, unit_ids_to_dept_ids

logger = logging.getLogger(__name__)

# DRF action → 权限码后缀. 自定义 @action 一律按 edit 校验 (见 CUSTOM_ACTION_SUFFIX).
ACTION_SUFFIX = {
    'list': 'list',
    'retrieve': 'list',
    'create': 'create',
    'update': 'edit',
    'partial_update': 'edit',
    'destroy': 'delete',
}
CUSTOM_ACTION_SUFFIX = 'edit'

# 已注册 resource_code 集合缓存 (seed 是 idempotent 的, 变动极少, 无需每次请求回表).
_KNOWN_CODES_CACHE_KEY = 'ats:v2:permission_resource_codes'
_KNOWN_CODES_TTL_DEFAULT = 300


def _codes_cache_ttl() -> int:
    """权限码集合缓存时长。测试环境置 0 关闭缓存, 避免用例间相互污染。"""
    return int(getattr(settings, 'V2_PERM_CODES_CACHE_TTL', _KNOWN_CODES_TTL_DEFAULT))


def known_resource_codes() -> set:
    """返回 PermissionResource 中已注册的 resource_code 集合 (缓存 5 分钟).

    V2 schema 未应用时降级为空集合 —— 此时所有派生码都会回退到视图声明的原码,
    等价于修复前的行为, 不会在迁移中间态把人锁死在门外.
    """
    codes = cache.get(_KNOWN_CODES_CACHE_KEY)
    if codes is not None:
        return codes
    try:
        codes = set(
            PermissionResource.objects.values_list('resource_code', flat=True)
        )
    except (OperationalError, ProgrammingError):
        logger.warning('V2 schema 未就绪: 权限码集合降级为空, 按 action 派生将全部回退原码')
        codes = set()
    cache.set(_KNOWN_CODES_CACHE_KEY, codes, _codes_cache_ttl())
    return codes


def invalidate_known_codes():
    """seed / PermissionResource 变更后调用, 让缓存立即失效."""
    cache.delete(_KNOWN_CODES_CACHE_KEY)


class V2Permission(BasePermission):
    """v2 统一守卫: has_perm 校验资源级权限, 且**按 action 区分读写**. superuser bypass.

    视图可声明三种形式 (优先级从高到低):

    1. ``permission_required_map``: ``{action: code}`` 显式覆盖表, 用于资源码命名
       不规范 / 某个 action 需要特殊码的场景 (例: sync_resources → role:assign).
    2. ``permission_required = [code, ...]``: 列表, 视为调用方已明确意图, 原样校验
       (任一命中即通过), 不做 action 派生.
    3. ``permission_required = 'recruit:x:list'``: 单码, 按 action 派生 ——
       create → :create / update|partial_update|自定义POST → :edit / destroy → :delete.
       读操作 (GET/HEAD/OPTIONS) 直接用声明的原码.

    未声明任何权限码时:
       - 读操作 → 放行。这是有意设计: 数据看板/KPI/导出等读路径由 ScopeQuerysetMixin
         做行级过滤 + FieldAcl 做列级脱敏 (见 analytics/views_export.py 注释)。
       - 写操作 → **拒绝**。此前此处默认放行, 导致只持 ":list" 的账号可对同一
         ModelViewSet 做 create/update/destroy (权限提升)。写操作必须显式声明。

    派生码在 PermissionResource 中不存在时回退原码并告警 —— 避免种子数据滞后
    (例如某资源只定义了 :list/:create) 时把合法写操作一并锁死。
    """

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if is_super_admin(user):
            return True

        action = getattr(view, 'action', None) or ''
        is_read = request.method in SAFE_METHODS

        # 1) 显式 action 覆盖表
        explicit = getattr(view, 'permission_required_map', None) or {}
        if action and action in explicit:
            return self._any(user, explicit[action])

        # 2) 自助操作白名单: 只作用于当前用户自己的数据, 无资源级授权概念。
        #    必须是 action 名集合 (而非布尔开关), 便于 scripts_scan_v2_write_guard.py
        #    扫描审计 —— 加了什么、为什么, 一眼可见, 不留暗门。
        if action and action in (getattr(view, 'v2_self_service_actions', None) or ()):
            return True

        required = getattr(view, 'permission_required', None)

        # 2) 完全未声明
        if not required:
            if is_read:
                return True
            return self._reject_undeclared_write(view, request)

        # 3) 多码: 调用方已明确意图, 原样校验
        if isinstance(required, (list, tuple)):
            return self._any(user, required)

        # 4) 单码: 按 action 派生
        return has_perm(user, self._derive(required, action, is_read))

    # ------------------------------------------------------------------
    @staticmethod
    def _any(user, codes) -> bool:
        codes = codes if isinstance(codes, (list, tuple)) else [codes]
        return any(has_perm(user, c) for c in codes)

    @staticmethod
    def _derive(required: str, action: str, is_read: bool) -> str:
        """由声明的读权限码派生出当前 action 应校验的码."""
        if is_read:
            return required
        suffix = ACTION_SUFFIX.get(action, CUSTOM_ACTION_SUFFIX)
        base = required.rsplit(':', 1)[0] if ':' in required else required
        derived = f'{base}:{suffix}'
        if derived == required:
            return required
        if derived in known_resource_codes():
            return derived
        logger.warning(
            'V2 权限码缺失: 资源 %r 未定义 %r (action=%s), 回退校验 %r。'
            '请在 seed_v2_init.RESOURCES 补该码。',
            base, derived, action or '-', required,
        )
        return required

    @staticmethod
    def _reject_undeclared_write(view, request) -> bool:
        """未声明权限码的写操作: 严格模式拒绝, 灰度期可整体降级为仅告警."""
        strict = getattr(settings, 'V2_STRICT_WRITE_GUARD', True)
        if not strict:
            logger.warning(
                '[V2_STRICT_WRITE_GUARD=False 灰度中] 未声明权限码的写操作已放行: '
                'view=%s method=%s path=%s',
                view.__class__.__name__, request.method, request.path,
            )
            return True
        logger.warning(
            '拒绝未声明权限码的写操作: view=%s method=%s path=%s。'
            '请为该视图声明 permission_required / permission_required_map。',
            view.__class__.__name__, request.method, request.path,
        )
        return False


class ScopeQuerysetMixin:
    """替代 apps/core/permissions.py 旧 ScopedQuerysetMixin.

    ViewSet 在 get_queryset() 末尾调用 self.scope_queryset(qs, scope_field='department_id').
    superuser bypass; resolve_scope 4 层堆栈; ManagementUnit.org_scope 转 dept_id 集合.
    """

    scope_field: str = ''
    # 招聘类型硬分区 (opt-in): 子类设 None 即不参与分区; 默认 'recruit_type'.
    # 仅当模型确有该字段时生效 (hasattr 守卫), 不影响未分区模型.
    recruit_type_field: str = 'recruit_type'

    def scope_queryset(self, qs, scope_field: str = '', entity: str = ''):
        user = self.request.user
        # 硬系统分区: 对所有用户(含超管)生效, 先于行级 scope 应用.
        # opt-in: 仅当模型确有 recruit_type 字段时过滤, 否则 no-op.
        rt_field = self.recruit_type_field
        if rt_field and hasattr(qs.model, rt_field):
            qs = qs.filter(**{rt_field: getattr(self.request, 'recruit_type', 'social')})
        if is_super_admin(user):
            return qs
        # 角色自定义范围（数据权限向导）优先于默认 scope：有配置则替换，无配置回退。
        entity = entity or getattr(self, 'data_perm_entity', '')
        if entity:
            from apps.data_permission.enforcement import role_entity_scope_q
            custom_q = role_entity_scope_q(user, entity)
            if custom_q is not None:
                return qs.filter(custom_q)
        scope_field = scope_field or self.scope_field

        scope = resolve_scope(user)
        if scope.get('all'):
            return qs

        # R8 (2026-08-03): resolve_scope 的 DEPT / DEPT_AND_SUB 分支直接返回部门 id
        # 集合 (Department.pk 是 CharField(32), 和 ManagementUnit 的 int 主键不是同一
        # id 空间), 这里单独处理, 不要再过 ManagementUnit 那一层转换。
        dept_ids = scope.get('department_ids') or []
        if dept_ids:
            if not scope_field:
                # 没声明 scope_field 就无法按部门过滤, 保守退回 SELF
                return qs.filter(created_by=user)
            return qs.filter(**{f'{scope_field}__in': dept_ids})

        unit_ids = scope.get('management_unit_ids', [])
        if not unit_ids:
            # SELF 兜底: 仅自己创建的
            return qs.filter(created_by=user)

        # 把 management_unit_ids 转 dept_id 集合 (复用 type-safe 解析, 避免 dict org_scope
        # 把 key 当部门 id 泄漏进过滤条件). 整公司级单元(ALL sentinel) -> 可见全量.
        try:
            resolved = unit_ids_to_dept_ids(unit_ids)
            if ALL_UNIT_SENTINEL in resolved:
                return qs
            unit_dept_ids = set(d for d in resolved if d != ALL_UNIT_SENTINEL)
        except (OperationalError, ProgrammingError):
            # V2 schema 未应用 → ManagementUnit 表可能缺列. fallback SELF.
            return qs.filter(created_by=user)

        if not unit_dept_ids:
            return qs.filter(created_by=user)
        return qs.filter(**{f'{scope_field}__in': unit_dept_ids})

    def _rt_field(self):
        """返回当前 ViewSet 应注入的招聘类型字段名 (opt-in).

        仅当 recruit_type_field 已声明且 queryset 模型确有该字段时返回字段名,
        否则返回 None —— 调用方据此决定是否走默认写入路径.
        """
        rt_field = self.recruit_type_field
        if not rt_field:
            return None
        model_cls = getattr(getattr(self, 'queryset', None), 'model', None)
        if model_cls and hasattr(model_cls, rt_field):
            return rt_field
        return None

    def perform_create(self, serializer):
        """写入守卫: 创建时由请求上下文权威注入 recruit_type (覆盖客户端自填值)."""
        rt_field = self._rt_field()
        if rt_field:
            serializer.save(**{rt_field: getattr(self.request, 'recruit_type', 'social')})
        else:
            super().perform_create(serializer)

    def perform_update(self, serializer):
        """写入守卫: 更新时由请求上下文权威注入 recruit_type (覆盖客户端自填值)."""
        rt_field = self._rt_field()
        if rt_field:
            serializer.save(**{rt_field: getattr(self.request, 'recruit_type', 'social')})
        else:
            super().perform_update(serializer)
