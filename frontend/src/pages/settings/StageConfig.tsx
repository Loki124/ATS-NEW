import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, InputNumber, message, Popconfirm, Tag, Space } from 'antd';

interface ProcessStage {
  id: string;
  name: string;
  code: string;
  type: string;
  status: 'active' | 'inactive';
  order: number;
}

const StageConfig: React.FC = () => {
  const [stages, setStages] = useState<ProcessStage[]>([
    { id: '1', name: '初评', code: 'P001', type: '筛选型', status: 'active', order: 1 },
    { id: '2', name: 'HRBP筛选', code: 'P002', type: '筛选型', status: 'active', order: 2 },
    { id: '3', name: '用人经理评估', code: 'P003', type: '筛选型', status: 'active', order: 3 },
    { id: '4', name: '邀约', code: 'P004', type: '邀约型', status: 'active', order: 4 },
    { id: '5', name: '联合面试', code: 'P005', type: '面试型', status: 'active', order: 5 },
    { id: '6', name: '综合面试', code: 'P006', type: '面试型', status: 'active', order: 6 },
    { id: '7', name: 'Offer沟通', code: 'P007', type: 'Offer型', status: 'active', order: 7 },
    { id: '8', name: '待入职', code: 'P008', type: '入职型', status: 'active', order: 8 },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingStage, setEditingStage] = useState<ProcessStage | null>(null);
  const [form] = Form.useForm();

  const handleAdd = () => {
    setEditingStage(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: ProcessStage) => {
    setEditingStage(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingStage) {
        setStages(stages.map(s => s.id === editingStage.id ? { ...editingStage, ...values } : s));
        message.success('阶段更新成功');
      } else {
        const newStage = {
          id: Date.now().toString(),
          code: `P${String(stages.length + 1).padStart(3, '0')}`,
          ...values,
          status: 'active' as const,
          order: stages.length + 1,
        };
        setStages([...stages, newStage]);
        message.success('阶段创建成功');
      }
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleStatus = (record: ProcessStage) => {
    setStages(stages.map(s => 
      s.id === record.id ? { ...s, status: s.status === 'active' ? 'inactive' : 'active' } : s
    ));
    message.success(`阶段已${record.status === 'active' ? '停用' : '启用'}`);
  };

  const handleDelete = (id: string) => {
    setStages(stages.filter(s => s.id !== id));
    message.success('阶段已删除');
  };

  const columns = [
    { title: '阶段编号', dataIndex: 'code', key: 'code', width: 100 },
    { title: '阶段名称', dataIndex: 'name', key: 'name' },
    { title: '阶段类型', dataIndex: 'type', key: 'type', width: 120,
      render: (type: string) => {
        const colors: Record<string, string> = { '筛选型': 'blue', '邀约型': 'cyan', '面试型': 'green', 'Offer型': 'orange', '入职型': 'purple' };
        return <Tag color={colors[type] || 'default'}>{type}</Tag>;
      }
    },
    { title: '排序', dataIndex: 'order', key: 'order', width: 80 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (status: string) => <Tag color={status === 'active' ? 'success' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>
    },
    { title: '操作', key: 'action', width: 200,
      render: (_: any, record: ProcessStage) => (
        <Space>
          <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" onClick={() => handleToggleStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger>删除</Button>
          </Popconfirm>
        </Space>
      )
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">阶段配置</h1>
      </div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button type="primary" onClick={handleAdd}>新增阶段</Button>
        </div>
        <Table columns={columns} dataSource={stages} rowKey="id" pagination={false} />
      </Card>

      <Modal
        title={editingStage ? '编辑阶段' : '新增阶段'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="阶段名称" rules={[{ required: true, message: '请输入阶段名称' }]}>
            <Input placeholder="请输入阶段名称" />
          </Form.Item>
          <Form.Item name="type" label="阶段类型" rules={[{ required: true, message: '请选择阶段类型' }]}>
            <Select placeholder="请选择阶段类型">
              <Select.Option value="筛选型">筛选型</Select.Option>
              <Select.Option value="邀约型">邀约型</Select.Option>
              <Select.Option value="面试型">面试型</Select.Option>
              <Select.Option value="Offer型">Offer型</Select.Option>
              <Select.Option value="入职型">入职型</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="order" label="排序" rules={[{ required: true, message: '请输入排序' }]}>
            <InputNumber min={1} max={99} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default StageConfig;
