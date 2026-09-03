"""通用资源导出 (G35 数据看板"导出"按钮死链修复)

FE  web/app/src/api/data.ts:51 exportResource(resource)
    → GET /api/v1/data/export/{resource}/?format=csv&fields=xxx,yyy
    → responseType=blob, 后端返 text/csv (UTF-8 BOM) 或 application/json

修复: 此前后端无路由 → 404 → 数据看板导出按钮点了没反应. 本模块补单 view,
同步流式 (StreamingHttpResponse), 不上 Celery (导出 ≤ 几千行 DB 内一次性返).

G35 字段级 ACL (PRD v4 §4.4 G43):
每行走 FieldAclService.apply_acl(entity, row, user) — 默认敏感字段
(phone/email/id_card_no/salary/bonus 等) 按角色脱敏; 超管 bypass.
"""
import csv
import logging
from typing import Callable, Dict, List

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions_v2 import V2Permission
from apps.field_acl.services import FieldAclService

logger = logging.getLogger(__name__)


class _Echo:
    """伪 file-like, 让 csv.writer 每次 write 返回一段 — 用于 StreamingHttpResponse."""
    def write(self, value: str) -> str:
        return value


# ---- 资源 → 字段清单 (key, 中文 label) ----
# key 必须是 model 序列化后字典里存在的字段名. label 用中文, Excel 直接可见.
CSV_FIELDS: Dict[str, List[tuple]] = {
    'Candidate': [
        ('id', 'ID'),
        ('name', '姓名'),
        ('phone', '手机'),
        ('email', '邮箱'),
        ('id_card_no', '身份证'),
        ('gender', '性别'),
        ('current_company', '当前公司'),
        ('current_position', '当前职位'),
        ('experience_years', '工作年限'),
        ('state', '状态'),
        ('source', '来源'),
        ('created_at', '创建时间'),
    ],
    'Demand': [
        ('id', 'ID'),
        ('title', '标题'),
        ('department', '部门'),
        ('hiring_manager', '用人经理'),
        ('headcount', '需求人数'),
        ('priority', '优先级'),
        ('state', '状态'),
        ('created_at', '创建时间'),
    ],
    'Position': [
        ('id', 'ID'),
        ('title', '职位'),
        ('department', '部门'),
        ('headcount', '招聘人数'),
        ('filled_count', '已招人数'),
        ('state', '状态'),
        ('created_at', '创建时间'),
    ],
    'Offer': [
        ('id', 'ID'),
        ('candidate_id', '候选人ID'),
        ('position_title', '职位'),
        ('salary', '薪资'),
        ('bonus', '奖金'),
        ('state', '状态'),
        ('created_at', '创建时间'),
    ],
    'Interview': [
        ('id', 'ID'),
        ('round_name', '轮次'),
        ('interview_type', '类型'),
        ('interview_date', '面试时间'),
        ('duration', '时长(分钟)'),
        ('interviewer_names', '面试官'),
        ('status', '状态'),
        ('feedback_status', '反馈状态'),
    ],
    'Onboarding': [
        ('id', 'ID'),
        ('candidate_id', '候选人ID'),
        ('position_title', '职位'),
        ('department', '部门'),
        ('onboard_date', '入职日期'),
        ('state', '状态'),
        ('created_at', '创建时间'),
    ],
}


# ---- 资源 → 行迭代器 (raw dict, 走 apply_acl 后再 yield 给 CSV/JSON) ----
def _iter_candidates():
    from apps.candidate.models import Candidate
    for c in Candidate.objects.filter(deleted_at__isnull=True).iterator(chunk_size=200):
        yield {
            'id': c.id,
            'name': c.name,
            'phone': c.phone,
            'email': getattr(c, 'email', None),
            'id_card_no': getattr(c, 'id_card_no', None),
            'gender': getattr(c, 'gender', None),
            'current_company': getattr(c, 'current_company', None),
            'current_position': getattr(c, 'current_position', None),
            'experience_years': getattr(c, 'experience_years', None),
            'state': c.state,
            'source': getattr(c, 'source', None),
            'created_at': c.created_at.isoformat() if getattr(c, 'created_at', None) else '',
        }


def _iter_demands():
    from apps.demand.models import Demand
    for d in Demand.objects.filter(deleted_at__isnull=True).iterator(chunk_size=200):
        yield {
            'id': d.id,
            'title': d.title,
            'department': getattr(d, 'department', None),
            'hiring_manager': getattr(d, 'hiring_manager', None),
            'headcount': getattr(d, 'headcount', None),
            'priority': getattr(d, 'priority', None),
            'state': d.state,
            'created_at': d.created_at.isoformat() if getattr(d, 'created_at', None) else '',
        }


def _iter_positions():
    from apps.position.models import Position
    for p in Position.objects.filter(deleted_at__isnull=True).iterator(chunk_size=200):
        yield {
            'id': p.id,
            'title': p.title,
            'department': getattr(p, 'department', None),
            'headcount': getattr(p, 'headcount', None),
            'filled_count': getattr(p, 'filled_count', None),
            'state': p.state,
            'created_at': p.created_at.isoformat() if getattr(p, 'created_at', None) else '',
        }


def _iter_offers():
    from apps.offer.models import Offer
    for o in Offer.objects.filter(deleted_at__isnull=True).iterator(chunk_size=200):
        yield {
            'id': o.id,
            'candidate_id': str(getattr(o, 'candidate_id', '') or ''),
            'position_title': getattr(o, 'position_title', None),
            'salary': getattr(o, 'salary', None),
            'bonus': getattr(o, 'bonus', None),
            'state': o.state,
            'created_at': o.created_at.isoformat() if getattr(o, 'created_at', None) else '',
        }


def _iter_interviews():
    from apps.interview.models import Interview
    for i in Interview.objects.filter(deleted_at__isnull=True).iterator(chunk_size=200):
        yield {
            'id': i.id,
            'round_name': getattr(i, 'round_name', None),
            'interview_type': i.interview_type,
            'interview_date': i.interview_date.isoformat() if getattr(i, 'interview_date', None) else '',
            'duration': i.duration,
            'interviewer_names': getattr(i, 'interviewer_names', None),
            'status': i.status,
            'feedback_status': i.feedback_status,
        }


def _iter_onboardings():
    from apps.onboarding.models import Onboarding
    for o in Onboarding.objects.filter(deleted_at__isnull=True).iterator(chunk_size=200):
        yield {
            'id': o.id,
            'candidate_id': str(getattr(o, 'candidate_id', '') or ''),
            'position_title': getattr(o, 'position_title', None),
            'department': getattr(o, 'department', None),
            'onboard_date': o.onboard_date.isoformat() if getattr(o, 'onboard_date', None) else '',
            'state': o.state,
            'created_at': o.created_at.isoformat() if getattr(o, 'created_at', None) else '',
        }


RESOURCE_ITER: Dict[str, Callable] = {
    'Candidate': _iter_candidates,
    'Demand': _iter_demands,
    'Position': _iter_positions,
    'Offer': _iter_offers,
    'Interview': _iter_interviews,
    'Onboarding': _iter_onboardings,
}


# FieldAclService.apply_acl 的 entity 名映射 (DEFAULT_SENSITIVE_FIELDS 键)
ENTITY_MAP = {
    'Candidate': 'candidate',
    'Demand': 'demand',           # 无默认敏感字段 (mask 全部按规则)
    'Position': 'position',
    'Offer': 'offer',             # 默认敏感: salary / bonus
    'Interview': 'interview',
    'Onboarding': 'onboarding',
}


class DataExportView(APIView):
    """通用资源导出 — GET /api/v1/data/export/<resource>/

    Query params:
        format: csv (default) | json
        fields: 逗号分隔字段名, 不传返全部 (CSV_FIELDS 子集)

    响应:
        CSV  → text/csv; charset=utf-8, 首行 UTF-8 BOM (Excel 中文兼容)
        JSON → {success: True, data: [...]}
    """
    # 不声明 permission_required → V2Permission 默认放行, 走 FieldAclService 行级脱敏
    # (与 KpiViewSet 同模式 — 数据看板全员可看, 敏感字段按角色 mask)
    permission_classes = [V2Permission]

    def get(self, request, resource: str):
        if resource not in RESOURCE_ITER:
            return Response(
                {'success': False, 'message': f'不支持的资源: {resource}（支持: {", ".join(RESOURCE_ITER)}）'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fmt = (request.query_params.get('format') or 'csv').lower()
        if fmt not in ('csv', 'json'):
            return Response(
                {'success': False, 'message': f'不支持的格式: {fmt}（支持 csv / json）'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 字段白名单 (前端 ?fields=name,phone)
        fields_param = (request.query_params.get('fields') or '').strip()
        requested = [f.strip() for f in fields_param.split(',') if f.strip()] if fields_param else None

        if fmt == 'csv':
            return self._csv_response(resource, requested, request.user)
        return self._json_response(resource, requested, request.user)

    # ----- CSV 流式 -----
    def _csv_response(self, resource: str, requested, user):
        field_specs = CSV_FIELDS[resource]
        if requested:
            valid_keys = {f[0] for f in field_specs}
            invalid = [k for k in requested if k not in valid_keys]
            if invalid:
                return Response(
                    {'success': False, 'message': f'不支持的字段: {", ".join(invalid)}'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            field_specs = [f for f in field_specs if f[0] in requested]
        labels = [label for _, label in field_specs]
        keys = [name for name, _ in field_specs]
        entity = ENTITY_MAP[resource]

        def stream():
            writer = csv.writer(_Echo())
            # UTF-8 BOM 让 Excel 正确识别 UTF-8 中文
            yield '\ufeff'
            yield writer.writerow(labels)
            count = 0
            for raw in RESOURCE_ITER[resource]():
                row = FieldAclService.apply_acl(entity, raw, user)
                yield writer.writerow([row.get(k, '') for k in keys])
                count += 1
            logger.info('data export: resource=%s user=%s rows=%d', resource, getattr(user, 'username', '?'), count)

        resp = StreamingHttpResponse(stream(), content_type='text/csv; charset=utf-8')
        # RFC 5987 编码兼容中文文件名
        from urllib.parse import quote
        filename = f'{resource}.csv'
        resp['Content-Disposition'] = (
            f"attachment; filename={filename}; "
            f"filename*=UTF-8''{quote(filename)}"
        )
        return resp

    # ----- JSON 全量 -----
    def _json_response(self, resource: str, requested, user):
        entity = ENTITY_MAP[resource]
        rows = []
        for raw in RESOURCE_ITER[resource]():
            row = FieldAclService.apply_acl(entity, raw, user)
            if requested:
                row = {k: row.get(k) for k in requested if k in row}
            rows.append(row)
        logger.info(
            'data export (json): resource=%s user=%s rows=%d',
            resource, getattr(user, 'username', '?'), len(rows),
        )
        return Response({'success': True, 'data': rows})