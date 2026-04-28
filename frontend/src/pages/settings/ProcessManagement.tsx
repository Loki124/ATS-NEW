import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Popconfirm, Tag, Space, Row, Col, Checkbox } from 'antd';

interface RecruitmentProcess {
  id: string;
  name: string;
  code: string;
  applicableScope: string;
  stages: string[];
  status: 'active' | 'inactive';
  createTime: string;
}

interface ProcessStage {
  id: string;
  name: string;
  code: string;
}

const ProcessManagement: React.FC = () => {
  const [processes, setProcesses] = useState<RecruitmentProcess[]>([
    { id: '1', name: '社会招聘流程', code: 'PROC001', applicableScope: '全部部门', stages: ['P001', 'P002', 'P003', 'P004', 'P005', 'P006', 'P007', 'P008'], status: 'active', createTime: '2024-01-15' },
    { id: '2', name: '校园招聘流程', code: 'PROC002', applicableScope: '全部部门', stages: ['P001', 'P002', 'P005', 'P006', 'P007', 'P008'], status: 'active', createTime: '2024-02-20' },
    { id: '3', name: '实习生招聘流程', code: 'PROC003', applicableScope: '全部部门', stages: ['P001', 'P002', 'P005', 'P007', 'P008'], status: 'inactive', createTime: '2024-03-10' },
  ]);

  const [stages] = useState<ProcessStage[]>([
    { id: '1', name: '初评', code: 'P001' },
    { id: '2', name: 'HRBP筛选', code: 'P002' },
    { id: '3', name: '用人经理评估', code: 'P003' },
    { id: '4', name: '邀约', code: 'P004' },
    { id: '5', name: '联合面试', code: 'P005' },
    { id: '6', name: '综合面试', code: 'P006' },
    { id: '7', name: 'Offer沟通', code: 'P007' },
    { id: '8', name: '待入职', code: 'P008' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingProcess, setEditingProcess] = useState<RecruitmentProcess | null>(null);
  const [form] = Form.useForm();

  const handleAdd = () => {
    setEditingProcess(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: RecruitmentProcess) => {
    setEditingProcess(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingProcess) {
        setProcesses(processes.map(p => p.id === editingProcess.id ? { ...editingProcess, ...values } : p));
        message.success('流程更新成功');
      } else {
        const newProcess = {
          id: Date.now().toString(),
          code: `PROC${String(processes.length + 1).padStart(3, '0')}`,
          ...values,
          status: 'active' as const,
          createTime: new Date().toISOString().split('T')[0],
        };
        setProcesses([...processes, newProcess]);
        message.success('流程创建成功');
      }
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleCopy = (record: RecruitmentProcess) => {
    const newProcess = {
      ...record,
      id: Date.now().toString(),
      code: `PROC${String(processes.length + 1).padStart(3, '0')}`,
      name: `${record.name}_副本`,
      createTime: new Date().toISOString().split('T')[0],
    };
    setProcesses([...processes, newProcess]);
    message.success('流程复制成功');
  };

  const handleToggleStatus = (record: RecruitmentProcess) => {
    setProcesses(processes.map(p => 
      p.id === record.id ? { ...p, status: p.status === 'active' ? 'inactive' : 'active' } : p
    ));
    message.success(`流程已${record.status === 'active' ? '停用' : '启用'}`);
  };

  const columns = [
    { title: '流程编号', dataIndex: 'code', key: 'code', width: 100 },
    { title: '流程名称', dataIndex: 'name', key: 'name' },
    { title: '适用范围', dataIndex: 'applicableScope', key: 'applicableScope', width: 120 },
    { title: '阶段数量', dataIndex: 'stages', key: 'stages', width: 100, render: (stages: string[]) => stages?.length || 0 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (status: string) => <Tag color={status === 'active' ? 'success' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>
    },
    { title: '创建时间', dataIndex: 'createTime', key: 'createTime', width: 120 },
    { title: '操作', key: 'action', width: 280,
      render: (_: any, record: RecruitmentProcess) => (
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
        <h1 className="page-title">招聘流程管理</h1>
      </div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button type="primary" onClick={handleAdd}>新增流程</Button>
        </div>
        <Table columns={columns} dataSource={processes} rowKey="id" pagination={false} />
      </Card>

      <Modal
        title={editingProcess ? '编辑流程' : '新增流程'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={700}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="流程名称" rules={[{ required: true, message: '请输入流程名称' }]}>
            <Input placeholder="请输入流程名称" />
          </Form.Item>
          <Form.Item name="applicableScope" label="适用范围" rules={[{ required: true, message: '请选择适用范围' }]}>
            <Select placeholder="请选择适用范围">
              <Select.Option value="全部部门">全部部门</Select.Option>
              <Select.Option value="技术部">技术部</Select.Option>
              <Select.Option value="销售部">销售部</Select.Option>
              <Select.Option value="人事部">人事部</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="stages" label="包含阶段">
            <Checkbox.Group style={{ width: '100%' }}>
              <Row>
                {stages.map(stage => (
                  <Col span={12} key={stage.id}>
                    <Checkbox value={stage.code}>{stage.name}</Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ProcessManagement;
