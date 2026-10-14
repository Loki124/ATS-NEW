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

    def validate(self, attrs):
        """同一简历同时只能有一个在途审批（兵哥 2026-10-14 口径）。

        终态（APPROVED / REJECTED / CANCELLED）不占用在途名额，可再次发起；
        PENDING / IN_PROGRESS 时重复发起直接拒绝 —— 否则会出现两条审批并行、
        「审批中仅发起人可操作」的归属无法判定（哪个 created_by 才是发起人？）。
        """
        candidate = attrs.get('candidate')
        if candidate is None:
            return attrs
        existing = ApprovalFlow.objects.filter(
            candidate=candidate,
            status__in=ApprovalFlow.IN_FLIGHT_STATUSES,
            deleted_at__isnull=True,
        ).first()
        if existing is not None:
            raise serializers.ValidationError({
                'candidate': (
                    f'该候选人已有在途审批（单号 {existing.id}，状态 '
                    f'{existing.get_status_display()}），不可重复发起；'
                    '如需重新审批请先完成或撤销原审批'
                ),
            })
        return attrs

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
