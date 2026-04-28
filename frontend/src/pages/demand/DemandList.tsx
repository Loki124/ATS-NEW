import React, { useState } from 'react';
import { Table, Button, Card, Space, Tag, Modal, Form, Input, Select, InputNumber, DatePicker, Divider, message, Row, Col, Upload } from 'antd';
import { PlusOutlined, EditOutlined, EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { TextArea } = Input;

interface Demand {
  id: string;
  code: string;
  name: string;
  department: string;
  count: number;
  status: string;
  approvalStatus: string;
  createdAt: string;
  demandType: string;
  position: string;
  salaryRange: string;
  deadline: string;
  hrbp: string;
  hiringManager: string;
  demandOwner: string;
}

const DemandList: React.FC = () => {
  const [modalVisible, setModalVisible] = useState(false);
  const [detailVisible, setDetailVisible] = useState(false);
  const [selectedDemand, setSelectedDemand] = useState<Demand | null>(null);
  const [form] = Form.useForm();
  const [demands, setDemands] = useState<Demand[]>([
    {
      id: '1',
      code: 'HC001',
      name: '前端开发工程师',
      department: '技术部',
      count: 2,
      status: '进行中',
      approvalStatus: '已通过',
      createdAt: '2024-01-15',
      demandType: '新增',
      position: '前端开发',
      salaryRange: '15K-25K',
      deadline: '2024-03-31',
      hrbp: '张三',
      hiringManager: '李四',
      demandOwner: '王五',
    },
    {
      id: '2',
      code: 'HC002',
      name: '产品经理',
      department: '产品部',
      count: 1,
      status: '进行中',
      approvalStatus: '审批中',
      createdAt: '2024-01-20',
      demandType: '替补',
      position: '产品经理',
      salaryRange: '20K-35K',
      deadline: '2024-04-15',
      hrbp: '赵六',
      hiringManager: '孙七',
      demandOwner: '周八',
    },
    {
      id: '3',
      code: 'HC003',
      name: 'UI设计师',
      department: '设计部',
      count: 1,
      status: '已完成',
      approvalStatus: '已通过',
      createdAt: '2024-01-10',
      demandType: '新增',
      position: 'UI设计',
      salaryRange: '12K-20K',
      deadline: '2024-02-28',
      hrbp: '钱九',
      hiringManager: '郑十',
      demandOwner: '吴一',
    },
  ]);

  const handleCreate = () => {
    setSelectedDemand(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: Demand) => {
    setSelectedDemand(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleView = (record: Demand) => {
    setSelectedDemand(record);
    setDetailVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (selectedDemand) {
        setDemands(demands.map(d => d.id === selectedDemand.id ? { ...d, ...values } : d));
        message.success('需求更新成功');
      } else {
        const newDemand: Demand = {
          id: Date.now().toString(),
          code: `HC00${demands.length + 1}`,
          ...values,
          status: '草稿',
          approvalStatus: '未发起',
          createdAt: new Date().toISOString().split('T')[0],
        };
        setDemands([...demands, newDemand]);
        message.success('需求创建成功');
      }
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleSubmitApproval = (record: Demand) => {
    setDemands(demands.map(d => 
      d.id === record.id ? { ...d, approvalStatus: '审批中', status: '进行中' } : d
    ));
    message.success('已提交审批');
  };

  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      '草稿': 'default',
      '进行中': 'processing',
      '已完成': 'success',
      '已暂停': 'warning',
      '已停招': 'error',
      '已超期': 'orange',
    };
    return colors[status] || 'default';
  };

  const getApprovalStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      '未发起': 'default',
      '审批中': 'processing',
      '已通过': 'success',
      '已拒绝': 'error',
      '已撤销': 'warning',
    };
    return colors[status] || 'default';
  };

  const columns: ColumnsType<Demand> = [
    { title: '需求编号', dataIndex: 'code', key: 'code', width: 100 },
    { title: '需求名称', dataIndex: 'name', key: 'name' },
    { title: '所属部门', dataIndex: 'department', key: 'department', width: 100 },
    { title: '需求人数', dataIndex: 'count', key: 'count', width: 90 },
    { title: '需求类型', dataIndex: 'demandType', key: 'demandType', width: 90,
      render: (type: string) => <Tag color={type === '新增' ? 'blue' : 'green'}>{type}</Tag>
    },
    { title: '薪资范围', dataIndex: 'salaryRange', key: 'salaryRange', width: 110 },
    { title: '需求状态', dataIndex: 'status', key: 'status', width: 90,
      render: (status: string) => <Tag color={getStatusColor(status)}>{status}</Tag>
    },
    { title: '审批状态', dataIndex: 'approvalStatus', key: 'approvalStatus', width: 90,
      render: (status: string) => <Tag color={getApprovalStatusColor(status)}>{status}</Tag>
    },
    { title: '创建时间', dataIndex: 'createdAt', key: 'createdAt', width: 110 },
    { title: '操作', key: 'action', width: 180,
      render: (_, record) => (
        <Space size="small">
          <Button type="link" size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>查看</Button>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>编辑</Button>
          {record.approvalStatus !== '已通过' && (
            <Button type="link" size="small" onClick={() => handleSubmitApproval(record)}>提交审批</Button>
          )}
        </Space>
      )
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 className="page-title">招聘需求</h1>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建需求
        </Button>
      </div>
      
      <Card>
        <Table
          columns={columns}
          dataSource={demands}
          rowKey="id"
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* 创建/编辑需求弹窗 */}
      <Modal
        title={selectedDemand ? '编辑需求' : '创建需求'}
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
              <Form.Item name="name" label="需求名称" rules={[{ required: true, message: '请输入需求名称' }]}>
                <Input placeholder="请输入需求名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="demandType" label="需求类型" rules={[{ required: true, message: '请选择需求类型' }]}>
                <Select placeholder="请选择">
                  <Select.Option value="新增">新增</Select.Option>
                  <Select.Option value="替补">替补</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
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
            <Col span={12}>
              <Form.Item name="position" label="职位" rules={[{ required: true, message: '请选择职位' }]}>
                <Select placeholder="请选择职位">
                  <Select.Option value="前端开发">前端开发</Select.Option>
                  <Select.Option value="后端开发">后端开发</Select.Option>
                  <Select.Option value="产品经理">产品经理</Select.Option>
                  <Select.Option value="UI设计">UI设计</Select.Option>
                  <Select.Option value="销售专员">销售专员</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="count" label="需求人数" rules={[{ required: true, message: '请输入需求人数' }]}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="salaryRange" label="薪资范围" rules={[{ required: true, message: '请选择薪资范围' }]}>
                <Select placeholder="请选择">
                  <Select.Option value="8K-12K">8K-12K</Select.Option>
                  <Select.Option value="12K-18K">12K-18K</Select.Option>
                  <Select.Option value="15K-25K">15K-25K</Select.Option>
                  <Select.Option value="20K-35K">20K-35K</Select.Option>
                  <Select.Option value="30K-50K">30K-50K</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="deadline" label="需求截止日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">人员配置</Divider>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="hrbp" label="HRBP" rules={[{ required: true, message: '请选择HRBP' }]}>
                <Select placeholder="请选择HRBP">
                  <Select.Option value="张三">张三</Select.Option>
                  <Select.Option value="赵六">赵六</Select.Option>
                  <Select.Option value="钱九">钱九</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="hiringManager" label="用人经理" rules={[{ required: true, message: '请选择用人经理' }]}>
                <Select placeholder="请选择用人经理" mode="multiple">
                  <Select.Option value="李四">李四</Select.Option>
                  <Select.Option value="孙七">孙七</Select.Option>
                  <Select.Option value="郑十">郑十</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="demandOwner" label="需求负责人" rules={[{ required: true, message: '请选择需求负责人' }]}>
                <Select placeholder="请选择">
                  <Select.Option value="王五">王五</Select.Option>
                  <Select.Option value="周八">周八</Select.Option>
                  <Select.Option value="吴一">吴一</Select.Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">需求详情</Divider>
          <Form.Item name="description" label="需求描述">
            <TextArea rows={4} placeholder="请输入需求描述和职位要求" />
          </Form.Item>

          <Form.Item name="jd" label="职位JD">
            <Upload beforeUpload={() => false} maxCount={1}>
              <Button>上传职位JD文件</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>

      {/* 需求详情弹窗 */}
      <Modal
        title="需求详情"
        open={detailVisible}
        onCancel={() => setDetailVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailVisible(false)}>关闭</Button>
        ]}
        width={700}
      >
        {selectedDemand && (
          <div>
            <Row gutter={[16, 16]}>
              <Col span={12}><strong>需求编号：</strong>{selectedDemand.code}</Col>
              <Col span={12}><strong>需求名称：</strong>{selectedDemand.name}</Col>
              <Col span={12}><strong>所属部门：</strong>{selectedDemand.department}</Col>
              <Col span={12}><strong>需求人数：</strong>{selectedDemand.count}人</Col>
              <Col span={12}><strong>需求类型：</strong>{selectedDemand.demandType}</Col>
              <Col span={12}><strong>薪资范围：</strong>{selectedDemand.salaryRange}</Col>
              <Col span={12}><strong>需求状态：</strong><Tag color={getStatusColor(selectedDemand.status)}>{selectedDemand.status}</Tag></Col>
              <Col span={12}><strong>审批状态：</strong><Tag color={getApprovalStatusColor(selectedDemand.approvalStatus)}>{selectedDemand.approvalStatus}</Tag></Col>
              <Col span={12}><strong>截止日期：</strong>{selectedDemand.deadline}</Col>
              <Col span={12}><strong>创建时间：</strong>{selectedDemand.createdAt}</Col>
            </Row>
            <Divider />
            <Row gutter={[16, 16]}>
              <Col span={12}><strong>HRBP：</strong>{selectedDemand.hrbp}</Col>
              <Col span={12}><strong>需求负责人：</strong>{selectedDemand.demandOwner}</Col>
              <Col span={24}><strong>用人经理：</strong>{selectedDemand.hiringManager}</Col>
            </Row>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default DemandList;
