import React, { useState } from 'react';
import { Table, Button, Card, Space, Tag, Modal, Form, Input, Select, InputNumber, DatePicker, Divider, message, Row, Col, Switch, Tabs } from 'antd';
import { PlusOutlined, EditOutlined, EyeOutlined, DeleteOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

interface Position {
  id: string;
  code: string;
  name: string;
  department: string;
  demandCode: string;
  recruitmentProcess: string;
  priority: string;
  status: string;
  headCount: number;
  hiredCount: number;
  createdAt: string;
  positionOwner: string;
  hiringManager: string;
  salaryRange: string;
  location: string;
  description: string;
}

const PositionList: React.FC = () => {
  const [modalVisible, setModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [form] = Form.useForm();
  const [positions, setPositions] = useState<Position[]>([
    {
      id: '1',
      code: 'POS001',
      name: '高级前端开发工程师',
      department: '技术部',
      demandCode: 'HC001',
      recruitmentProcess: '社会招聘流程',
      priority: '高',
      status: '招聘中',
      headCount: 2,
      hiredCount: 0,
      createdAt: '2024-01-15',
      positionOwner: '王五',
      hiringManager: '李四',
      salaryRange: '18K-30K',
      location: '上海市',
      description: '负责公司前端技术开发',
    },
    {
      id: '2',
      code: 'POS002',
      name: '产品经理',
      department: '产品部',
      demandCode: 'HC002',
      recruitmentProcess: '社会招聘流程',
      priority: '中',
      status: '招聘中',
      headCount: 1,
      hiredCount: 0,
      createdAt: '2024-01-20',
      positionOwner: '周八',
      hiringManager: '孙七',
      salaryRange: '20K-35K',
      location: '上海市',
      description: '负责产品规划和设计',
    },
    {
      id: '3',
      code: 'POS003',
      name: 'UI设计师',
      department: '设计部',
      demandCode: 'HC003',
      recruitmentProcess: '社会招聘流程',
      priority: '低',
      status: '已完成',
      headCount: 1,
      hiredCount: 1,
      createdAt: '2024-01-10',
      positionOwner: '吴一',
      hiringManager: '郑十',
      salaryRange: '12K-20K',
      location: '深圳市',
      description: '负责产品UI设计',
    },
  ]);

  const handleCreate = () => {
    setSelectedPosition(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: Position) => {
    setSelectedPosition(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleView = (record: Position) => {
    setSelectedPosition(record);
    setDetailVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (selectedPosition) {
        setPositions(positions.map(p => p.id === selectedPosition.id ? { ...selectedPosition, ...values } : p));
        message.success('职位更新成功');
      } else {
        const newPosition: Position = {
          id: Date.now().toString(),
          code: `POS00${positions.length + 1}`,
          ...values,
          status: '招聘中',
          hiredCount: 0,
          createdAt: new Date().toISOString().split('T')[0],
        };
        setPositions([...positions, newPosition]);
        message.success('职位创建成功');
      }
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleStatus = (record: Position) => {
    setPositions(positions.map(p => 
      p.id === record.id ? { ...p, status: p.status === '招聘中' ? '已停招' : '招聘中' } : p
    ));
    message.success(`职位已${record.status === '招聘中' ? '停招' : '开启招聘'}`);
  };

  const handleDelete = (id: string) => {
    setPositions(positions.filter(p => p.id !== id));
    message.success('职位已删除');
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      '招聘中': 'success',
      '已停招': 'error',
      '已完成': 'blue',
    };
    return colors[status] || 'default';
  };

  const getPriorityColor = (priority: string) => {
    const colors: Record<string, string> = {
      '高': 'red',
      '中': 'orange',
      '低': 'green',
    };
    return colors[priority] || 'default';
  };

  const columns: ColumnsType<Position> = [
    { title: '职位编号', dataIndex: 'code', key: 'code', width: 100 },
    { title: '职位名称', dataIndex: 'name', key: 'name' },
    { title: '所属部门', dataIndex: 'department', key: 'department', width: 100 },
    { title: '关联需求', dataIndex: 'demandCode', key: 'demandCode', width: 100 },
    { title: '招聘流程', dataIndex: 'recruitmentProcess', key: 'recruitmentProcess', width: 120 },
    { title: '优先级', dataIndex: 'priority', key: 'priority', width: 80,
      render: (priority: string) => <Tag color={getPriorityColor(priority)}>{priority}</Tag>
    },
    { title: '职位状态', dataIndex: 'status', key: 'status', width: 90,
      render: (status: string) => <Tag color={getStatusColor(status)}>{status}</Tag>
    },
    { title: '需求/已入职', key: 'headCount', width: 110,
      render: (_, record) => `${record.headCount}/${record.hiredCount}`
    },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 110 },
    { title: '操作', key: 'action', width: 200,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>查看</Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          <Button type="link" size="small" onClick={() => handleToggleStatus(record)}>
            {record.status === '招聘中' ? '停招' : '开启'}
          </Button>
        </Space>
      )
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">职位管理</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建职位
        </Button>
      </div>
      
      <Card>
        <Tabs defaultActiveKey="all">
          <Tabs.TabPane tab="全部职位" key="all">
            <Table columns={columns} dataSource={positions} rowKey="id" pagination={{ pageSize: 10 }} />
          </Tabs.TabPane>
          <Tabs.TabPane tab="招聘中" key="recruiting">
            <Table 
              columns={columns} 
              dataSource={positions.filter(p => p.status === '招聘中')} 
              rowKey="id" 
              pagination={{ pageSize: 10 }} 
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="已停招" key="stopped">
            <Table 
              columns={columns} 
              dataSource={positions.filter(p => p.status === '已停招')} 
              rowKey="id" 
              pagination={{ pageSize: 10 }} 
            />
          </Tabs.TabPane>
          <Tabs.TabPane tab="已完成" key="completed">
            <Table 
              columns={columns} 
              dataSource={positions.filter(p => p.status === '已完成')} 
              rowKey="id" 
              pagination={{ pageSize: 10 }} 
            />
          </Tabs.TabPane>
        </Tabs>
      </Card>

      {/* 创建/编辑职位弹窗 */}
      <Modal
        title={selectedPosition ? '编辑职位' : '创建职位'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={800}
        okText="保存"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Divider orientation="left">基本信息</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="name" label="职位名称" rules={[{ required: true, message: '请输入职位名称' }]}>
                <Input placeholder="请输入职位名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="department" label="所属部门" rules={[{ required: true, message: '请选择部门' }]}>
                <Select placeholder="请选择部门">
                  <Select.Option value="技术部">技术部</Select.Option>
                  <Select.Option value="产品部">产品部</Select.Option>
                  <Select.Option value="设计部">设计部</Select.Option>
                  <Select.Option value="销售部">销售部</Select.Option>
                  <Select.Option value="人事部">人事部</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="demandCode" label="关联需求" rules={[{ required: true, message: '请选择关联需求' }]}>
                <Select placeholder="请选择需求">
                  <Select.Option value="HC001">HC001 - 前端开发工程师</Select.Option>
                  <Select.Option value="HC002">HC002 - 产品经理</Select.Option>
                  <Select.Option value="HC003">HC003 - UI设计师</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="recruitmentProcess" label="招聘流程" rules={[{ required: true, message: '请选择招聘流程' }]}>
                <Select placeholder="请选择流程">
                  <Select.Option value="社会招聘流程">社会招聘流程</Select.Option>
                  <Select.Option value="校园招聘流程">校园招聘流程</Select.Option>
                  <Select.Option value="实习生招聘流程">实习生招聘流程</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="priority" label="优先级" rules={[{ required: true, message: '请选择优先级' }]}>
                <Select placeholder="请选择">
                  <Select.Option value="高">高</Select.Option>
                  <Select.Option value="中">中</Select.Option>
                  <Select.Option value="低">低</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="headCount" label="需求人数" rules={[{ required: true, message: '请输入需求人数' }]}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="salaryRange" label="薪资范围">
                <Select placeholder="请选择">
                  <Select.Option value="8K-12K">8K-12K</Select.Option>
                  <Select.Option value="12K-18K">12K-18K</Select.Option>
                  <Select.Option value="15K-25K">15K-25K</Select.Option>
                  <Select.Option value="20K-35K">20K-35K</Select.Option>
                  <Select.Option value="30K-50K">30K-50K</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="location" label="工作地点">
                <Input placeholder="请输入工作地点" />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">人员配置</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="positionOwner" label="职位负责人" rules={[{ required: true, message: '请选择职位负责人' }]}>
                <Select placeholder="请选择">
                  <Select.Option value="王五">王五</Select.Option>
                  <Select.Option value="周八">周八</Select.Option>
                  <Select.Option value="吴一">吴一</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="hiringManager" label="用人经理" rules={[{ required: true, message: '请选择用人经理' }]}>
                <Select placeholder="请选择" mode="multiple">
                  <Select.Option value="李四">李四</Select.Option>
                  <Select.Option value="孙七">孙七</Select.Option>
                  <Select.Option value="郑十">郑十</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">职位详情</Divider>
          <Form.Item name="description" label="职位描述">
            <Input.TextArea rows={4} placeholder="请输入职位描述和任职要求" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 职位详情弹窗 */}
      <Modal
        title="职位详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>关闭</Button>
        ]}
        width={700}
      >
        {selectedPosition && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}><strong>职位编号：</strong>{selectedPosition.code}</Col>
              <Col span={12}><strong>职位名称：</strong>{selectedPosition.name}</Col>
              <Col span={12}><strong>所属部门：</strong>{selectedPosition.department}</Col>
              <Col span={12}><strong>关联需求：</strong>{selectedPosition.demandCode}</Col>
              <Col span={12}><strong>招聘流程：</strong>{selectedPosition.recruitmentProcess}</Col>
              <Col span={12}><strong>优先级：</strong><Tag color={getPriorityColor(selectedPosition.priority)}>{selectedPosition.priority}</Tag></Col>
              <Col span={12}><strong>职位状态：</strong><Tag color={getStatusColor(selectedPosition.status)}>{selectedPosition.status}</Tag></Col>
              <Col span={12}><strong>需求人数：</strong>{selectedPosition.headCount}人</Col>
              <Col span={12}><strong>已入职：</strong>{selectedPosition.hiredCount}人</Col>
              <Col span={12}><strong>薪资范围：</strong>{selectedPosition.salaryRange}</Col>
              <Col span={12}><strong>工作地点：</strong>{selectedPosition.location}</Col>
              <Col span={12}><strong>创建时间：</strong>{selectedPosition.createdAt}</Col>
            </Row>
            <Divider />
            <Row gutter={[16, 16]}>
              <Col span={12}><strong>职位负责人：</strong>{selectedPosition.positionOwner}</Col>
              <Col span={24}><strong>用人经理：</strong>{selectedPosition.hiringManager}</Col>
            </Row>
            <Divider />
            <div>
              <strong>职位描述：</strong>
              <p>{selectedPosition.description}</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PositionList;
