"""LIFE-1 指标模板版本化后端测试（T04）。

覆盖：
  - T01 数据模型：MetricTemplate.version / version_count，MetricTemplateVersion
    快照表，删除模板 CASCADE 连带历史。
  - T02 版本服务层：build_snapshot(15 键) / diff_snapshots / create_version_snapshot /
    rollback_template。
  - T03 API 写路径：创建落 create 快照、语义变更 bump、非语义不 bump、版本历史 /
    回滚端点（成功 / 404 / 400）、导入落 import 快照。

约定：
  - 请求走 auth_client（JWT，等价于 is_superuser），响应统一经 _unwrap 解信封
    （项目响应为 {success, data, message, code}）。
  - service 层用 ORM 直建对象单测，避免绕开真实快照逻辑。
"""
import pytest

pytestmark = pytest.mark.django_db

from ..models import (
    AtomicMetric,
    DerivedMetric,
    MetricTemplate,
    MetricTemplateVersion,
)
from ..services.template_version import (
    SEMANTIC_FIELDS,
    RollbackBlocked,
    TemplateVersionNotFound,
    build_snapshot,
    create_version_snapshot,
    diff_snapshots,
    list_versions,
    rollback_template,
)

BASE = '/api/v1/metrics/'
TEMPLATES = BASE + 'templates/'


def _unwrap(resp):
    """兼容信封响应：{success, data, ...} -> data；否则原样返回。"""
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _make_atomic(name='原子指标-版本测试', source_path='candidate.age'):
    return AtomicMetric.objects.create(
        name=name, source_path=source_path, data_type='number',
        unit='岁', status='enabled',
    )


def _make_derived(name='派生指标-版本测试'):
    return DerivedMetric.objects.create(
        name=name, calc_func='MAX_GAP', base_path='candidate.workExperience',
        data_type='number', unit='天', status='enabled',
    )


def _create_template_via_api(auth_client, atomic, name, operators):
    """经 API 创建模板（触发 perform_create 落 kind='create' 快照）。返回解包后的 data dict。"""
    resp = auth_client.post(
        TEMPLATES,
        {'name': name, 'atomicMetric': str(atomic.id), 'operators': operators},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    return _unwrap(resp)


# ===========================================================================
#  T01 数据模型 / 快照落库
# ===========================================================================
class TestCreateBaselineSnapshot:
    def test_create_writes_create_snapshot(self, auth_client):
        """创建基线快照：version==1、version_count==1、存在一条 change_kind='create' 快照。"""
        atomic = _make_atomic()
        data = _create_template_via_api(auth_client, atomic, '基线模板-A', ['GT', 'LT'])

        tpl = MetricTemplate.objects.get(pk=data['id'])
        assert tpl.version == 1
        assert tpl.version_count == 1

        snap = MetricTemplateVersion.objects.get(template=tpl, version=1)
        assert snap.change_kind == 'create'
        # create 为初始基线，无上一版本可 diff
        assert snap.changed_fields == []
        # snapshot 完整记录当时配置
        assert snap.snapshot['name'] == '基线模板-A'
        assert snap.snapshot['operators'] == ['GT', 'LT']
        assert snap.snapshot['atomic_metric_id'] == atomic.id


# ===========================================================================
#  T03 语义变更 bump / 非语义不 bump
# ===========================================================================
class TestSemanticChangeBump:
    def test_semantic_change_bumps_version_and_writes_update_snapshot(self, auth_client):
        """PATCH 改 operators（SEMANTIC_FIELDS）-> version+1、version_count+1、新增 update 快照含 changed_fields。"""
        atomic = _make_atomic()
        created = _create_template_via_api(auth_client, atomic, '语义变更模板-B', ['GT'])

        url = TEMPLATES + f"{created['id']}/"
        resp = auth_client.patch(url, {'operators': ['GT', 'LT', 'EQ']}, format='json')
        assert resp.status_code == 200, resp.content
        after = _unwrap(resp)
        assert after['version'] == 2
        assert after['version_count'] == 2

        tpl = MetricTemplate.objects.get(pk=created['id'])
        assert tpl.version == 2
        assert tpl.version_count == 2

        update_snap = MetricTemplateVersion.objects.get(template=tpl, version=2)
        assert update_snap.change_kind == 'update'
        assert 'operators' in update_snap.changed_fields

        # 倒序列表：v2(update) 在前，v1(create) 在后
        versions = _unwrap(auth_client.get(url + 'versions/'))
        assert [v['version'] for v in versions] == [2, 1]
        assert versions[0]['change_kind'] == 'update'
        assert versions[1]['change_kind'] == 'create'

    def test_non_semantic_change_does_not_bump(self, auth_client):
        """PATCH 仅改 status / description（非 SEMANTIC_FIELDS）-> version 不变、无新快照。"""
        atomic = _make_atomic()
        created = _create_template_via_api(auth_client, atomic, '非语义模板-C', ['GT'])

        url = TEMPLATES + f"{created['id']}/"
        resp = auth_client.patch(url, {'status': 'disabled', 'description': '停用说明'}, format='json')
        assert resp.status_code == 200, resp.content
        after = _unwrap(resp)
        assert after['version'] == 1
        assert after['version_count'] == 1

        tpl = MetricTemplate.objects.get(pk=created['id'])
        assert tpl.version == 1
        assert tpl.version_count == 1
        # 仍只有初始 create 快照，无 update 快照
        assert MetricTemplateVersion.objects.filter(template=tpl, change_kind='update').count() == 0
        assert tpl.status == 'disabled'
        assert tpl.description == '停用说明'


# ===========================================================================
#  T02 / T03 回滚
# ===========================================================================
class TestRollback:
    def _build_v1_v2(self, auth_client, atomic, name, ops_v1, ops_v2):
        """建一个模板并 bump 到 v2，返回 (template_id, v1_snapshot_operators)。"""
        created = _create_template_via_api(auth_client, atomic, name, ops_v1)
        url = TEMPLATES + f"{created['id']}/"
        auth_client.patch(url, {'operators': ops_v2}, format='json')
        versions = _unwrap(auth_client.get(url + 'versions/'))
        v1_ops = next(v['snapshot']['operators'] for v in versions if v['version'] == 1)
        return created['id'], v1_ops

    def test_rollback_success_restores_v1_and_appends_rollback_snapshot(self, auth_client):
        """回滚到 v1：内容回到 v1、version+1（=3）、新增 kind='rollback' 快照且位于倒序首位。"""
        atomic = _make_atomic()
        tpl_id, v1_ops = self._build_v1_v2(
            auth_client, atomic, '回滚模板-D', ['GT'], ['LT', 'IN'],
        )
        url = TEMPLATES + f"{tpl_id}/"

        resp = auth_client.post(url + 'versions/rollback/', {'version_no': 1}, format='json')
        assert resp.status_code == 200, resp.content
        data = _unwrap(resp)
        # 回滚后再 +1：原本 v2 -> 审计快照 v3
        assert data['version'] == 3

        tpl = MetricTemplate.objects.get(pk=tpl_id)
        assert tpl.version == 3
        # 真实字段已写回 v1 状态
        assert tpl.operators == v1_ops

        # 倒序列表：v3(rollback) 居首
        versions = _unwrap(auth_client.get(url + 'versions/'))
        assert versions[0]['version'] == 3
        assert versions[0]['change_kind'] == 'rollback'
        # 三个快照齐全：rollback / update / create
        kinds = {v['change_kind'] for v in versions}
        assert kinds == {'rollback', 'update', 'create'}

    def test_rollback_missing_version_returns_404(self, auth_client):
        """回滚到不存在的版本号 -> 404（TemplateVersionNotFound）。"""
        atomic = _make_atomic()
        created = _create_template_via_api(auth_client, atomic, '回滚缺失-E', ['GT'])
        url = TEMPLATES + f"{created['id']}/"

        resp = auth_client.post(url + 'versions/rollback/', {'version_no': 99}, format='json')
        assert resp.status_code == 404, resp.content
        assert '快照不存在' in str(resp.data)

    def test_rollback_blocked_when_metric_disabled_returns_400(self, auth_client):
        """回滚目标版本引用的指标 status!='enabled' -> 400（RollbackBlocked，绝不静默降级）。"""
        atomic = _make_atomic('原子指标-失效测试')
        created = _create_template_via_api(auth_client, atomic, '回滚失效-F', ['GT'])
        url = TEMPLATES + f"{created['id']}/"

        # 让引用指标失效（软删不允许，改状态为 disabled 同样阻断）
        AtomicMetric.objects.filter(pk=atomic.id).update(status='disabled')

        resp = auth_client.post(url + 'versions/rollback/', {'version_no': 1}, format='json')
        assert resp.status_code == 400, resp.content
        assert '无法回滚' in str(resp.data)
        # 未误判为 404
        assert resp.status_code != 404
        # 版本号未被错误 bump
        assert MetricTemplate.objects.get(pk=created['id']).version == 1

    def test_rollback_blocked_when_derived_metric_disabled(self, auth_client):
        """派生指标引用失效同样阻断（覆盖 derived_metric 分支）。"""
        derived = _make_derived()
        resp = auth_client.post(
            TEMPLATES,
            {'name': '回滚派生-G', 'derivedMetric': str(derived.id), 'operators': ['GT']},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        tpl_id = _unwrap(resp)['id']
        url = TEMPLATES + f"{tpl_id}/"

        DerivedMetric.objects.filter(pk=derived.id).update(status='disabled')
        resp = auth_client.post(url + 'versions/rollback/', {'version_no': 1}, format='json')
        assert resp.status_code == 400, resp.content
        assert '无法回滚' in str(resp.data)


# ===========================================================================
#  T01 删除连带历史（CASCADE）
# ===========================================================================
class TestDeleteCascade:
    def test_delete_template_cascades_versions(self, auth_client):
        """删除模板 -> 其 versions 全部随删（查询为空 / version_count==0）。"""
        atomic = _make_atomic()
        created = _create_template_via_api(auth_client, atomic, '级联删除-H', ['GT'])
        tpl = MetricTemplate.objects.get(pk=created['id'])
        assert tpl.version_count == 1

        tpl.delete()

        # 主表记录已不存在
        assert not MetricTemplate.objects.filter(pk=tpl.id).exists()
        # 快照历史随 FK CASCADE 清空
        assert MetricTemplateVersion.objects.filter(template_id=tpl.id).count() == 0


# ===========================================================================
#  T03 导入落 import 快照
# ===========================================================================
class TestImportSnapshot:
    def _xlsx_bytes(self, rows):
        import io

        from openpyxl import Workbook

        wb = Workbook()
        ws = wb.active
        ws.title = '指标模板'
        for r in rows:
            ws.append(r)
        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()

    def _upload(self, content, name):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return SimpleUploadedFile(name, content, content_type='application/octet-stream')

    def test_import_update_writes_import_snapshot_and_bumps_version(self, auth_client):
        """io_template.import_templates(mode='update') 更新已有模板 -> version+1 且新增 kind='import' 快照。"""
        atomic = _make_atomic('导入指标-版本测试')
        created = _create_template_via_api(auth_client, atomic, '导入模板-I', ['GT'])
        tpl_id = created['id']
        assert MetricTemplate.objects.get(pk=tpl_id).version == 1

        headers = ['模板名称', '指标类型', '引用指标名称', '支持的运算符', '参数枚举', '允许为空', '状态', '说明']
        content = self._xlsx_bytes([
            headers,
            ['导入模板-I', '原子', '导入指标-版本测试', 'GTE', '', '否', '启用', '导入更新说明'],
        ])
        resp = auth_client.post(
            TEMPLATES + 'import/',
            {'file': self._upload(content, 'x.xlsx'), 'mode': 'update'},
            format='multipart',
        )
        assert resp.status_code == 200, resp.content
        body = _unwrap(resp)
        assert body['updated'] == 1

        tpl = MetricTemplate.objects.get(pk=tpl_id)
        # version +1
        assert tpl.version == 2
        # 新增一条 kind='import' 快照
        assert tpl.version_count == 2
        import_snap = MetricTemplateVersion.objects.get(template=tpl, version=2)
        assert import_snap.change_kind == 'import'
        assert tpl.operators == ['GTE']
        assert tpl.description == '导入更新说明'


# ===========================================================================
#  T02 服务层单测（纯函数 / 直建对象）
# ===========================================================================
class TestVersionServiceUnit:
    def test_build_snapshot_has_15_keys(self, super_user):
        atomic = _make_atomic('快照键测试')
        tpl = MetricTemplate.objects.create(
            name='快照键模板', atomic_metric=atomic, operators=['GT'], status='enabled',
        )
        snap = build_snapshot(tpl)
        expected_keys = {
            'name', 'atomic_metric_id', 'derived_metric_id', 'metric_name', 'metric_kind',
            'metric_path', 'data_type', 'unit', 'operators', 'param_config', 'value_domain',
            'param_enums', 'calc_params', 'param_allow_null', 'status', 'description',
        }
        assert set(snap.keys()) == expected_keys

    def test_diff_snapshots_returns_changed_keys(self):
        old = {'a': 1, 'b': 2, 'c': 3}
        new = {'a': 1, 'b': 20, 'c': 3}
        assert diff_snapshots(old, new) == ['b']
        # 仅比较共有键
        assert diff_snapshots(old, {'b': 20}) == ['b']
        # 无差异
        assert diff_snapshots(old, dict(old)) == []

    def test_create_version_snapshot_records_change_kind_and_changed_fields(self, super_user):
        """create_version_snapshot：version 取 tpl.version，changed_fields 来自与上一版本的 diff。"""
        atomic = _make_atomic('快照写入测试')
        tpl = MetricTemplate.objects.create(
            name='快照写入模板', atomic_metric=atomic, operators=['GT'], status='enabled',
        )
        # 手动落一条 v1（模拟 create 基线）
        create_version_snapshot(tpl, super_user, kind='create', note='初始')
        assert MetricTemplateVersion.objects.filter(template=tpl, version=1).exists()

        # bump 到 v2 并改 operators，再落快照
        tpl.operators = ['GT', 'LT']
        tpl.version = 2
        tpl.save(update_fields=['operators', 'version'])
        snap = create_version_snapshot(tpl, super_user, kind='update')
        assert snap.version == 2
        assert snap.change_kind == 'update'
        assert snap.changed_fields == ['operators']

    def test_rollback_template_service_missing_version_raises(self, super_user):
        """服务层直接调用：版本不存在抛 TemplateVersionNotFound。"""
        atomic = _make_atomic('回滚服务测试')
        tpl = MetricTemplate.objects.create(
            name='回滚服务模板', atomic_metric=atomic, operators=['GT'], status='enabled',
        )
        with pytest.raises(TemplateVersionNotFound):
            rollback_template(tpl, 42, super_user)

    def test_rollback_template_service_blocked_when_metric_disabled(self, super_user):
        """服务层直接调用：引用指标失效抛 RollbackBlocked。"""
        atomic = _make_atomic('回滚服务失效')
        tpl = MetricTemplate.objects.create(
            name='回滚服务失效模板', atomic_metric=atomic, operators=['GT'], status='enabled',
        )
        create_version_snapshot(tpl, super_user, kind='create')
        atomic.status = 'disabled'
        atomic.save(update_fields=['status'])
        with pytest.raises(RollbackBlocked):
            rollback_template(tpl, 1, super_user)

    def test_list_versions_ordered_desc(self, super_user):
        atomic = _make_atomic('列表排序测试')
        tpl = MetricTemplate.objects.create(
            name='列表排序模板', atomic_metric=atomic, operators=['GT'], status='enabled',
        )
        create_version_snapshot(tpl, super_user, kind='create')
        tpl.operators = ['LT']
        tpl.version = 2
        tpl.save(update_fields=['operators', 'version'])
        create_version_snapshot(tpl, super_user, kind='update')
        versions = list_versions(tpl.id)
        assert [v.version for v in versions] == [2, 1]


# 防守：SEMANTIC_FIELDS 真源应与 models 中 version 语义字段一致（防回归）。
def test_semantic_fields_excludes_status_and_description():
    assert 'status' not in SEMANTIC_FIELDS
    assert 'description' not in SEMANTIC_FIELDS
    assert 'operators' in SEMANTIC_FIELDS
    assert 'name' in SEMANTIC_FIELDS


@pytest.mark.django_db
def test_b3_concurrent_snapshot_no_integrity_error():
    """【P1/B-3 回归】同一 (template, version) 重复落快照不得抛 IntegrityError（不得 500）。

    模拟两名 HR 并发编辑同一模板：二者都读到旧 version 并算出相同新 version，
    第二个 create 会撞 uniq_tpl_version 唯一约束 → 修复前 IntegrityError 逃逸为 500。
    修复后 create_version_snapshot 用 get_or_create，第二个调用复用已存在快照行。
    """
    atomic = AtomicMetric.objects.create(
        name='B3原子', source_path='candidate.age', data_type='number', status='enabled',
    )
    tpl = MetricTemplate.objects.create(
        name='B3模板', atomic_metric=atomic, operators=['GT'], version=1,
    )
    # v1 基线快照（正常 perform_create 已落）
    MetricTemplateVersion.objects.create(
        template=tpl, version=1, snapshot=build_snapshot(tpl), change_kind='create',
    )

    tpl.version = 2
    s1 = create_version_snapshot(tpl, user=None, kind='update', note='并发A')
    # 第二个并发写者算出相同 version=2，再次落快照
    s2 = create_version_snapshot(tpl, user=None, kind='update', note='并发B')

    assert s1.id == s2.id, '重复 (template, version) 应复用同一快照行，而非撞唯一约束 500'
    assert MetricTemplateVersion.objects.filter(template=tpl, version=2).count() == 1


@pytest.mark.django_db
def test_b3_update_twice_same_version_no_500():
    """【P1/B-3 回归】两次更新都 bump 到相同 version 时，第二次不得 500（端到端模拟竞态末端）。"""
    atomic = AtomicMetric.objects.create(
        name='B3原子2', source_path='candidate.age', data_type='number', status='enabled',
    )
    tpl = MetricTemplate.objects.create(
        name='B3模板2', atomic_metric=atomic, operators=['GT'], version=1,
    )
    MetricTemplateVersion.objects.create(
        template=tpl, version=1, snapshot=build_snapshot(tpl), change_kind='create',
    )
    # 模拟两个并发请求都基于 version=1 各自 bump 到 2
    tpl.version = 2
    tpl.save(update_fields=['version'])
    create_version_snapshot(tpl, user=None, kind='update', note='writer-A')
    # writer-B 也 bump 到 2（幂等，无冲突）
    tpl.version = 2
    tpl.save(update_fields=['version'])
    create_version_snapshot(tpl, user=None, kind='update', note='writer-B')
    assert MetricTemplateVersion.objects.filter(template=tpl, version=2).count() == 1


# ===========================================================================
#  V13 回归：模板 calc_params 必须符合引用派生指标的 param_schema 契约
#  （计算参数已下沉到模板层，定义层不再持有取值）
# ===========================================================================
@pytest.mark.django_db
class TestCalcParamsSchemaValidation:
    def _make_avg_work(self):
        return DerivedMetric.objects.create(
            name='平均工作时长-V13', calc_func='AVG_WORK_MONTHS',
            base_path='candidate.workExperience', data_type='number',
            unit='月', status='enabled',
        )

    def test_valid_calc_params_passes(self, auth_client):
        d = self._make_avg_work()
        resp = auth_client.post(
            TEMPLATES,
            {
                'name': '平均时长模板', 'derivedMetric': str(d.id),
                'operators': ['GT'],
                'calcParams': {'recent_n': 3, 'unit': 'month'},
            },
            format='json',
        )
        assert resp.status_code == 201, resp.content.decode()
        data = resp.json()['data']
        # 响应经 camelCase 渲染：嵌套键也被转换（recent_n -> recentN），DB 内仍存 snake_case
        assert data['calcParams']['unit'] == 'month'
        assert data['calcParams'].get('recentN', data['calcParams'].get('recent_n')) == 3

    def test_unknown_param_key_rejected(self, auth_client):
        d = self._make_avg_work()
        resp = auth_client.post(
            TEMPLATES,
            {
                'name': '未知参数模板', 'derivedMetric': str(d.id),
                'operators': ['GT'],
                'calcParams': {'recent_n': 3, 'foo': 1},
            },
            format='json',
        )
        assert resp.status_code == 400

    def test_select_value_out_of_options_rejected(self, auth_client):
        d = self._make_avg_work()
        resp = auth_client.post(
            TEMPLATES,
            {
                'name': '非法枚举模板', 'derivedMetric': str(d.id),
                'operators': ['GT'],
                'calcParams': {'recent_n': 3, 'unit': 'lightyear'},
            },
            format='json',
        )
        assert resp.status_code == 400

    def test_required_param_missing_rejected(self, auth_client, monkeypatch):
        """required 参数缺失时序列化器应拒绝（直接校验静态方法）。"""
        from .. import serializers as sers
        from rest_framework import serializers as drf
        fake_func = {'param_schema': [
            {'key': 'k', 'label': 'K', 'type': 'number', 'required': True},
        ]}
        monkeypatch.setattr(sers, 'get_derived_func', lambda name: fake_func)
        with pytest.raises(drf.ValidationError):
            sers.MetricTemplateSerializer._validate_calc_params(
                {}, type('M', (), {'calc_func': 'X'})()
            )

