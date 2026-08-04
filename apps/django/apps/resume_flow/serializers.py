"""Resume Flow Serializers"""
from rest_framework import serializers

from .models import ApprovalFlow, ApprovalFlowHistory


class ApprovalFlowHistorySerializer(serializers.ModelSerializer):
    """审批流历史记录序列化器"""
    operated_by_name = serializers.CharField(source='operated_by.username', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)

    class Meta:
        model = ApprovalFlowHistory
        fields = [
            'id', 'action', 'action_display', 'from_node', 'to_node',
            'operated_by', 'operated_by_name', 'comment', 'created_at',
        ]
        read_only_fields = fields


class ApprovalFlowListSerializer(serializers.ModelSerializer):
    """审批流列表序列化器（轻量）"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    history_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ApprovalFlow
        fields = [
            'id', 'candidate', 'candidate_name', 'resume_id',
            'status', 'status_display', 'current_node_id',
            'created_by', 'created_at', 'updated_at', 'history_count',
        ]


class ApprovalFlowDetailSerializer(serializers.ModelSerializer):
    """审批流详情序列化器（含 nodes + histories）"""
    candidate_name = serializers.CharField(source='candidate.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    histories = ApprovalFlowHistorySerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalFlow
        fields = [
            'id', 'candidate', 'candidate_name', 'resume_id',
            'status', 'status_display', 'current_node_id',
            'nodes', 'created_by', 'created_by_name',
            'created_at', 'updated_at', 'histories',
        ]


class ApprovalFlowCreateSerializer(serializers.ModelSerializer):
    """审批流创建序列化器"""

    class Meta:
        model = ApprovalFlow
        fields = ['candidate', 'resume_id', 'nodes']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['created_by'] = request.user if request else None
        # 首个节点设为 current_node_id
        # 兼容 CamelCaseJSONParser 可能把 nodeId → node_id 的转换
        nodes = validated_data.get('nodes', [])
        if nodes:
            first_node = nodes[0]
            first_node_id = first_node.get('nodeId') or first_node.get('node_id', '')
            validated_data['current_node_id'] = first_node_id
        else:
            validated_data['current_node_id'] = ''
        validated_data['status'] = 'PENDING'
        flow = super().create(validated_data)
        return flow


class ApprovalFlowTransitionSerializer(serializers.Serializer):
    """审批流转序列化器（approve/reject/delegate 共用）"""
    node_id = serializers.CharField(max_length=32, required=True)
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                    default='')
    # delegate 专用
    delegate_to = serializers.CharField(max_length=64, required=False, allow_blank=True,
                                        default='')
