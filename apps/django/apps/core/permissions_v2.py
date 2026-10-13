"""V2 权限 DRF 接入层. V2Permission 校验资源级权限, ScopeQuerysetMixin 做数据级过滤."""
import logging

from django.conf import settings
from django.core.cache import cache
from django.db.utils import OperationalError, ProgrammingError
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models_permission_v2 import PermissionResource
from .permission_check import has_perm
from .role_v2_query import is_super_admin

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
        # 1b) 纯 APIView (无 DRF action, action 恒为 None): 表键按 HTTP method 小写匹配,
        #     使 POST-only 视图能声明精确码 (:create / :export / ...), 而不必退化成派生 :edit。
        if not action and isinstance(explicit, dict):
            by_method = (request.method or '').lower()
            if by_method in explicit:
                return self._any(user, explicit[by_method])

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

    2026-10-12 M02: scope_queryset 委托 scope_filter_q 全语义（唯一真相源）。
    此前本类是独立复刻版，与 scope_filter_q 存在三处口径分叉：
      1. 默认 scope 只走 unit_ids_to_dept_ids（部门集合），缺失 iter_unit_scopes 的
         成员 USER `created_by__in` OR 分支与 data_range AND 限制 —— 同一用户经
         CandidateViewSet（scope_filter_q）可见的「管理单元 USER 成员创建的候选人」，
         经 demand/position 等走本类的 ViewSet 看不到；
      2. 不读 scope_creator_field，SELF 兜底硬编码 created_by，与 ENTITY_SCOPE 登记的
         creator_field（demand=requested_by / referral=referrer / invitation=inviter）漂移；
      3. resolve_scope 不传 app_code，绕过方案 A 的 per-app 范围优先语义。
    现统一委托 scope_filter_q（recruit_type 分区 / CUSTOM 替换 / 默认 scope 回退
    全部走同一实现），并补读 scope_creator_field。行为变更方向 = 向唯一真相源收敛：
    单元 USER 成员数据可见性对齐、SELF 兜底字段与导出口径一致、per-app 范围生效。
    """

    scope_field: str = ''
    # 创建人字段路径（SELF 兜底 / 管理单元成员 USER 分支使用）。此前本类不读该属性、
    # 硬编码 created_by，导致 demand 等声明了 scope_creator_field 的 ViewSet 与实际
    # 执行口径漂移；现由 scope_filter_q 统一消费。
    scope_creator_field: str = 'created_by'
    # 招聘类型硬分区 (opt-in): 子类设 None 即不参与分区; 默认 'recruit_type'.
    # 仅当模型确有该字段时生效 (hasattr 守卫), 不影响未分区模型.
    recruit_type_field: str = 'recruit_type'
    # 默认 scope（L1-L4）应用开关（2026-10-12 M02 收敛路径③时新增）。
    #   True : CUSTOM 有配置则替换、无配置回退默认 scope（scope_filter_q 全语义）；
    #   False: 只叠加 CUSTOM 规则，无配置原样返回 —— 供 process 这类「无部门字段
    #          可依、历史上不按默认 scope 裁剪」的配置型实体显式声明，
    #          避免收敛入口时静默把可见性从全量收窄为 SELF。
    apply_default_scope: bool = True

    def scope_queryset(self, qs, scope_field: str = '', entity: str = ''):
        from apps.core.scope_resolver import scope_filter_q

        user = self.request.user
        entity = entity or getattr(self, 'data_perm_entity', '')
        # 硬系统分区: 仅当模型确有 recruit_type 字段时生效 (与 entity_scope_q 的
        # hasattr 守卫一致); 否则 rt=None, scope_filter_q 内 no-op.
        rt = getattr(self.request, 'recruit_type', 'social')
        if not (self.recruit_type_field and hasattr(qs.model, self.recruit_type_field)):
            rt = None
        if not self.apply_default_scope:
            # 只叠加 CUSTOM 规则 (role_entity_scope_q); 无配置 / 超管 -> 原样返回.
            if is_super_admin(user) or not entity:
                return qs
            from apps.data_permission.enforcement import role_entity_scope_q
            custom_q = role_entity_scope_q(user, entity)
            return qs.filter(custom_q) if custom_q is not None else qs
        return qs.filter(scope_filter_q(
            user,
            app_code='recruit',
            scope_field=scope_field or self.scope_field,
            creator_field=self.scope_creator_field,
            recruit_type=rt,
            entity=entity,
        ))

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
