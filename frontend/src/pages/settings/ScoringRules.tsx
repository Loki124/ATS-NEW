import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Tag, Space } from 'antd';

interface ScoringRule {
  id: string;
  name: string;
  code: string;
  scope: string;
  ruleType: 'normal' | 'combination';
  status: 'active' | 'inactive';
}

const ScoringRules: React.FC = () => {
  const [rules, setRules] = useState<ScoringRule[]>([
    { id: '1', name: '学历评分规则', code: 'RULE001', scope: '全局', ruleType: 'normal', status: 'active' },
    { id: '2', name: '工作经验评分规则', code: 'RULE002', scope: '技术部-高级', ruleType: 'combination', status: 'active' },
    { id: '3', name: '综合评分规则', code: 'RULE003', scope: '销售部', ruleType: 'combination', status: 'inactive' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingRule, setEditingRule] = useState<ScoringRule | null>(null);
  const [form] = Form.useForm();

  const handleAdd = () => {
    setEditingRule(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: ScoringRule) => {
    setEditingRule(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingRule) {
        setRules(rules.map(r => r.id === editingRule.id ? { ...editingRule, ...values } : r));
        message.success('规则更新成功');
      } else {
        const newRule = {
          id: Date.now().toString(),
          code: `RULE${String(rules.length + 1).padStart(3, '0')}`,
          ...values,
          status: 'active' as const,
        };
        setRules([...rules, newRule]);
        message.success('规则创建成功');
      }
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleCopy = (record: ScoringRule) => {
    const newRule = {
      ...record,
      id: Date.now().toString(),
      code: `RULE${String(rules.length + 1).padStart(3, '0')}`,
      name: `${record.name}_副本`,
    };
    setRules([...rules, newRule]);
    message.success('规则复制成功');
  };

  const handleToggleStatus = (record: ScoringRule) => {
    setRules(rules.map(r => 
      r.id === record.id ? { ...r, status: r.status === 'active' ? 'inactive' : 'active' } : r
    ));
    message.success(`规则已${record.status === 'active' ? '停用' : '启用'}`);
  };

  const columns = [
    { title: '规则编号', dataIndex: 'code', key: 'code', width: 100 },
    { title: '规则名称', dataIndex: 'name', key: 'name' },
    { title: '适用范围', dataIndex: 'scope', key: 'scope', width: 150 },
    { title: '规则类型', dataIndex: 'ruleType', key: 'ruleType', width: 120,
      render: (type: string) => <Tag color={type === 'normal' ? 'blue' : 'purple'}>{type === 'normal' ? '普通规则' : '组合规则'}</Tag>
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (status: string) => <Tag color={status === 'active' ? 'success' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>
    },
    { title: '操作', key: 'action', width: 280,
      render: (_: any, record: ScoringRule) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" onClick={() => handleCopy(record)}>复制</Button>
          <Button type="link" size="small" onClick={() => handleToggleStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      )
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">评分规则</h1>
      </div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button type="primary" onClick={handleAdd}>新增规则</Button>
        </div>
        <Table columns={columns} dataSource={rules} rowKey="id" pagination={false} />
      </Card>

      <Modal
        title={editingRule ? '编辑规则' : '新增规则'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="规则名称" rules={[{ required: true, message: '请输入规则名称' }]}>
            <Input placeholder="请输入规则名称" />
          </Form.Item>
          <Form.Item name="ruleType" label="规则类型" rules={[{ required: true, message: '请选择规则类型' }]}>
            <Select placeholder="请选择规则类型">
              <Select.Option value="normal">普通规则</Select.Option>
              <Select.Option value="combination">组合规则</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="scope" label="适用范围" rules={[{ required: true, message: '请选择适用范围' }]}>
            <Select placeholder="请选择适用范围" mode="multiple">
              <Select.Option value="全局">全局</Select.Option>
              <Select.Option value="技术部">技术部</Select.Option>
              <Select.Option value="销售部">销售部</Select.Option>
              <Select.Option value="人事部">人事部</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ScoringRules;
