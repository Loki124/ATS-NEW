"""职务管理序列化器。"""
from rest_framework import serializers

from apps.dictionary.models import DictionaryItem

from .models import JobTitle

# 写入的字典项 id 仅允许取未软删的字典项, 防止引用已删除数据
_LIVE_DICT_ITEMS = DictionaryItem.objects.filter(deleted_at__isnull=True)


class JobTitleSerializer(serializers.ModelSerializer):
    """职务 — 列表 / 详情 / 写入。

    - ``job_family`` / ``job_category`` / ``job_subcategory`` 写入收字典项 id,
      输出附带展示名 (``*_name``), 供前端下拉回显;
    - ``status`` 为只读派生字段 (ACTIVE/INACTIVE), 与 DB ``is_enabled`` 同步;
    - ``responsibility`` 存原始 HTML 字符串, 由前端富文本编辑器产出。
    """

    job_family = serializers.PrimaryKeyRelatedField(
        queryset=_LIVE_DICT_ITEMS, label='职位族',
    )
    job_category = serializers.PrimaryKeyRelatedField(
        queryset=_LIVE_DICT_ITEMS, allow_null=True, required=False, label='职位类',
    )
    job_subcategory = serializers.PrimaryKeyRelatedField(
        queryset=_LIVE_DICT_ITEMS, allow_null=True, required=False, label='职位子类',
    )
    job_family_name = serializers.SerializerMethodField()
    job_category_name = serializers.SerializerMethodField()
    job_subcategory_name = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    updated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JobTitle
        fields = [
            'id', 'name',
            'job_family', 'job_family_name',
            'job_category', 'job_category_name',
            'job_subcategory', 'job_subcategory_name',
            'is_key_position', 'responsibility', 'is_management', 'job_level_tier',
            'sort_order', 'is_enabled', 'status',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'job_family_name', 'job_category_name', 'job_subcategory_name',
            'created_by_name', 'created_at', 'updated_by_name', 'updated_at',
        ]

    def validate_name(self, value: str) -> str:
        """职务名称非空 (去掉纯空白)。"""
        value = (value or '').strip()
        if not value:
            raise serializers.ValidationError('职务名称不能为空')
        return value

    def validate(self, attrs: dict) -> dict:
        """职务名称全局唯一 (含软删占位行)。

        DB unique 约束同样兜底 (软删行仍占坑位), 这里先做友好拦截,
        冲突信息打到 ``name`` 字段, 便于前端映射。
        """
        attrs = super().validate(attrs)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        if not name:
            return attrs
        qs = JobTitle.objects.filter(name=name)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': ['该职务名称已存在']})
        return attrs

    def get_job_family_name(self, obj) -> str:
        return obj.job_family.value if obj.job_family_id else ''

    def get_job_category_name(self, obj) -> str:
        return obj.job_category.value if obj.job_category_id else ''

    def get_job_subcategory_name(self, obj) -> str:
        return obj.job_subcategory.value if obj.job_subcategory_id else ''

    def get_status(self, obj) -> str:
        return obj.status

    def get_created_by_name(self, obj) -> str:
        user = getattr(obj, 'created_by', None)
        return user.full_name if user else ''

    def get_updated_by_name(self, obj) -> str:
        user = getattr(obj, 'updated_by', None)
        return user.full_name if user else ''
