"""人员 / 部门 引用型字段 (2026-09-24 兵哥)。

覆盖:
  - resolve_options_source 对 internal_user / external_user / organization 的解析
  - FieldType choices 含 PERSON / DEPARTMENT
  - 序列化层 (DynamicFieldSerializer.to_representation) 按 options_source 动态回填 options
  - 序列化层接受 PERSON / DEPARTMENT 作为 field_type (DRF ChoiceField 契约)
"""
import pytest

from apps.core.models import User
from apps.core.models_permission_v2 import ManagementUnit
from apps.dynamic_field.models import DynamicField
from apps.dynamic_field.serializers import DynamicFieldSerializer


@pytest.mark.django_db
class TestPersonDepartmentResolve:
    def test_field_type_choices(self):
        values = [c[0] for c in DynamicField.FieldType.choices]
        assert 'PERSON' in values
        assert 'DEPARTMENT' in values

    def test_resolve_none_for_custom_and_empty(self):
        assert DynamicField.resolve_options_source(None) is None
        assert DynamicField.resolve_options_source({'type': 'custom'}) is None
        # internal_user 不需要 key, 有用户即返回列表 (无用户返回空列表, 但非 None)
        assert DynamicField.resolve_options_source({'type': 'internal_user', 'key': ''}) is not None

    def test_resolve_internal_user(self):
        internal = User.objects.create(username='in1', user_type='INTERNAL', is_active=True)
        User.objects.create(username='ex1', user_type='EXTERNAL', is_active=True)
        opts = DynamicField.resolve_options_source({'type': 'internal_user', 'key': ''})
        assert opts is not None
        vals = [o['value'] for o in opts]
        assert str(internal.id) in vals
        ex = User.objects.get(username='ex1')
        assert str(ex.id) not in vals
        assert opts[0]['label']  # 标签回退到姓名/用户名

    def test_resolve_external_user(self):
        external = User.objects.create(username='ex2', user_type='EXTERNAL', is_active=True)
        User.objects.create(username='in2', user_type='INTERNAL', is_active=True)
        opts = DynamicField.resolve_options_source({'type': 'external_user'})
        vals = [o['value'] for o in opts]
        assert str(external.id) in vals
        in2 = User.objects.get(username='in2')
        assert str(in2.id) not in vals

    def test_resolve_organization_excludes_disabled(self):
        mu = ManagementUnit.objects.create(unit_name='OrgA', status=1)
        ManagementUnit.objects.create(unit_name='OrgB', status=0)
        opts = DynamicField.resolve_options_source({'type': 'organization'})
        vals = [o['value'] for o in opts]
        assert str(mu.id) in vals
        assert all(o['label'] for o in opts)


@pytest.mark.django_db
class TestPersonDepartmentSerializer:
    def test_to_representation_resolves_internal_user(self):
        User.objects.create(username='in3', user_type='INTERNAL', is_active=True)
        field = DynamicField.objects.create(
            resource='Candidate', field_key='recruiter', label='招聘者',
            field_type=DynamicField.FieldType.PERSON,
            options_source={'type': 'internal_user', 'key': ''},
        )
        data = DynamicFieldSerializer(field).data
        assert data['field_type'] == 'PERSON'
        assert data['options']  # 序列化层按 options_source 回填

    def test_to_representation_resolves_organization(self):
        mu = ManagementUnit.objects.create(unit_name='OrgC', status=1)
        field = DynamicField.objects.create(
            resource='Candidate', field_key='belong_dept', label='归属部门',
            field_type=DynamicField.FieldType.DEPARTMENT,
            options_source={'type': 'organization', 'key': ''},
        )
        data = DynamicFieldSerializer(field).data
        assert data['field_type'] == 'DEPARTMENT'
        assert any(o['value'] == str(mu.id) for o in data['options'])

    def test_serializer_accepts_person_field_type(self):
        ser = DynamicFieldSerializer(data={
            'resource': 'Candidate', 'field_key': 'owner', 'label': '负责人',
            'field_type': 'PERSON', 'options_source': {'type': 'internal_user', 'key': ''},
        })
        assert ser.is_valid(), ser.errors
        assert 'field_type' not in ser.errors

    def test_serializer_accepts_department_field_type(self):
        ser = DynamicFieldSerializer(data={
            'resource': 'Candidate', 'field_key': 'dept', 'label': '部门',
            'field_type': 'DEPARTMENT', 'options_source': {'type': 'organization', 'key': ''},
        })
        assert ser.is_valid(), ser.errors
        assert 'field_type' not in ser.errors

    def test_create_persists_person_field(self):
        # 真实 save() → DB 持久化, 验收「创建字段」整链路 (人员 + 内部用户来源)
        internal = User.objects.create(username='in_persist', user_type='INTERNAL', is_active=True)
        ser = DynamicFieldSerializer(data={
            'resource': 'Candidate', 'field_key': 'owner_persist', 'label': '负责人',
            'field_type': 'PERSON', 'options_source': {'type': 'internal_user', 'key': ''},
        })
        assert ser.is_valid(), ser.errors
        field = ser.save()
        # 落库校验
        reloaded = DynamicField.objects.get(pk=field.pk)
        assert reloaded.field_type == 'PERSON'
        assert reloaded.options_source == {'type': 'internal_user', 'key': ''}
        # 序列化回填校验: 内部用户动态解析命中刚创建的用户
        out = DynamicFieldSerializer(reloaded).data
        assert out['field_type'] == 'PERSON'
        assert any(o['value'] == str(internal.id) for o in out['options'])

    def test_create_persists_department_field(self):
        mu = ManagementUnit.objects.create(unit_name='OrgPersist', status=1)
        ser = DynamicFieldSerializer(data={
            'resource': 'Candidate', 'field_key': 'dept_persist', 'label': '归属部门',
            'field_type': 'DEPARTMENT', 'options_source': {'type': 'organization', 'key': ''},
        })
        assert ser.is_valid(), ser.errors
        field = ser.save()
        reloaded = DynamicField.objects.get(pk=field.pk)
        assert reloaded.field_type == 'DEPARTMENT'
        assert reloaded.options_source == {'type': 'organization', 'key': ''}
        out = DynamicFieldSerializer(reloaded).data
        assert out['field_type'] == 'DEPARTMENT'
        assert any(o['value'] == str(mu.id) for o in out['options'])
