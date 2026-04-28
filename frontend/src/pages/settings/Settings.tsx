import React, { useState } from 'react';
import { Card, Tabs, Table, Button, Modal, Form, Input, Select, Switch, message, Popconfirm, Tag, Space, Divider, Row, Col, InputNumber, TreeSelect, Checkbox } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, StopOutlined, PlayCircleOutlined, CopyOutlined } from '@ant-design/icons';

const { TextArea } = Input;

interface ProcessStage {
  id: string;
  name: string;
  code: string;
  type: string;
  status: 'active' | 'inactive';
  order: number;
}

interface RecruitmentProcess {
  id: string;
  name: string;
  code: string;
  applicableScope: string;
  stages: string[];
  status: 'active' | 'inactive';
  createTime: string;
}

interface ScoringRule {
  id: string;
  name: string;
  code: string;
  scope: string;
  ruleType: 'normal' | 'combination';
  status: 'active' | 'inactive';
}

interface DictionaryItem {
  id: string;
  name: string;
  code: string;
  category: string;
  itemCount: number;
  status: 'active' | 'inactive';
}

interface CompanyAddress {
  id: string;
  name: string;
  region: string;
  address: string;
  longitude?: number;
  latitude?: number;
  status: 'active' | 'inactive';
}

const Settings: React.FC = () => {
  const [activeTab, setActiveTab] = useState('process');
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
  
  const [processes, setProcesses] = useState<RecruitmentProcess[]>([
    { id: '1', name: '社会招聘流程', code: 'PROC001', applicableScope: '全部部门', stages: ['P001', 'P002', 'P003', 'P004', 'P005', 'P006', 'P007', 'P008'], status: 'active', createTime: '2024-01-15' },
    { id: '2', name: '校园招聘流程', code: 'PROC002', applicableScope: '全部部门', stages: ['P001', 'P002', 'P005', 'P006', 'P007', 'P008'], status: 'active', createTime: '2024-02-20' },
    { id: '3', name: '实习生招聘流程', code: 'PROC003', applicableScope: '全部部门', stages: ['P001', 'P002', 'P005', 'P007', 'P008'], status: 'inactive', createTime: '2024-03-10' },
  ]);
  
  const [scoringRules, setScoringRules] = useState<ScoringRule[]>([
    { id: '1', name: '学历评分规则', code: 'RULE001', scope: '全局', ruleType: 'normal', status: 'active' },
    { id: '2', name: '工作经验评分规则', code: 'RULE002', scope: '技术部-高级', ruleType: 'combination', status: 'active' },
    { id: '3', name: '综合评分规则', code: 'RULE003', scope: '销售部', ruleType: 'combination', status: 'inactive' },
  ]);
  
  const [dictionaries, setDictionaries] = useState<DictionaryItem[]>([
    { id: '1', name: '学历', code: 'EDUCATION', category: '基本信息', itemCount: 8, status: 'active' },
    { id: '2', name: '婚姻状况', code: 'MARITAL', category: '基本信息', itemCount: 4, status: 'active' },
    { id: '3', name: '职位类型', code: 'POSITION_TYPE', category: '职位信息', itemCount: 12, status: 'active' },
    { id: '4', name: '面试类型', code: 'INTERVIEW_TYPE', category: '面试信息', itemCount: 5, status: 'active' },
    { id: '5', name: 'Offer状态', code: 'OFFER_STATUS', category: 'Offer信息', itemCount: 8, status: 'active' },
    { id: '6', name: '淘汰原因', code: 'REJECT_REASON', category: '归档信息', itemCount: 15, status: 'active' },
  ]);
  
  const [companyAddresses, setCompanyAddresses] = useState<CompanyAddress[]>([
    { id: '1', name: '上海总部', region: '上海市-宝山区', address: '沪太路5008弄200号', longitude: 121.407, latitude: 31.352, status: 'active' },
    { id: '2', name: '深圳分部', region: '广东省-深圳市-南山区', address: '科技园路100号', status: 'active' },
    { id: '3', name: '北京分部', region: '北京市-朝阳区', address: '建国路88号', status: 'inactive' },
  ]);

  const [stageModalVisible, setStageModalVisible] = useState(false);
  const [processModalVisible, setProcessModalVisible] = useState(false);
  const [ruleModalVisible, setRuleModalVisible] = useState(false);
  const [dictionaryModalVisible, setDictionaryModalVisible] = useState(false);
  const [addressModalVisible, setAddressModalVisible] = useState(false);
  const [editingStage, setEditingStage] = useState<ProcessStage | null>(null);
  const [editingProcess, setEditingProcess] = useState<RecruitmentProcess | null>(null);
  const [editingRule, setEditingRule] = useState<ScoringRule | null>(null);
  const [editingDictionary, setEditingDictionary] = useState<DictionaryItem | null>(null);
  const [editingAddress, setEditingAddress] = useState<CompanyAddress | null>(null);
  const [form] = Form.useForm();
  const [processForm] = Form.useForm();
  const [ruleForm] = Form.useForm();
  const [dictionaryForm] = Form.useForm();
  const [addressForm] = Form.useForm();

  // 阶段相关操作
  const handleAddStage = () => {
    setEditingStage(null);
    form.resetFields();
    setStageModalVisible(true);
  };

  const handleEditStage = (record: ProcessStage) => {
    setEditingStage(record);
    form.setFieldsValue(record);
    setStageModalVisible(true);
  };

  const handleSaveStage = async () => {
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
      setStageModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleStageStatus = (record: ProcessStage) => {
    setStages(stages.map(s => 
      s.id === record.id ? { ...s, status: s.status === 'active' ? 'inactive' : 'active' } : s
    ));
    message.success(`阶段已${record.status === 'active' ? '停用' : '启用'}`);
  };

  const handleDeleteStage = (id: string) => {
    setStages(stages.filter(s => s.id !== id));
    message.success('阶段已删除');
  };

  // 流程相关操作
  const handleAddProcess = () => {
    setEditingProcess(null);
    processForm.resetFields();
    setProcessModalVisible(true);
  };

  const handleEditProcess = (record: RecruitmentProcess) => {
    setEditingProcess(record);
    processForm.setFieldsValue(record);
    setProcessModalVisible(true);
  };

  const handleSaveProcess = async () => {
    try {
      const values = await processForm.validateFields();
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
      setProcessModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleCopyProcess = (record: RecruitmentProcess) => {
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

  const handleToggleProcessStatus = (record: RecruitmentProcess) => {
    setProcesses(processes.map(p => 
      p.id === record.id ? { ...p, status: p.status === 'active' ? 'inactive' : 'active' } : p
    ));
    message.success(`流程已${record.status === 'active' ? '停用' : '启用'}`);
  };

  // 评分规则相关操作
  const handleAddRule = () => {
    setEditingRule(null);
    ruleForm.resetFields();
    setRuleModalVisible(true);
  };

  const handleEditRule = (record: ScoringRule) => {
    setEditingRule(record);
    ruleForm.setFieldsValue(record);
    setRuleModalVisible(true);
  };

  const handleSaveRule = async () => {
    try {
      const values = await ruleForm.validateFields();
      if (editingRule) {
        setScoringRules(scoringRules.map(r => r.id === editingRule.id ? { ...editingRule, ...values } : r));
        message.success('规则更新成功');
      } else {
        const newRule = {
          id: Date.now().toString(),
          code: `RULE${String(scoringRules.length + 1).padStart(3, '0')}`,
          ...values,
          status: 'active' as const,
        };
        setScoringRules([...scoringRules, newRule]);
        message.success('规则创建成功');
      }
      setRuleModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleCopyRule = (record: ScoringRule) => {
    const newRule = {
      ...record,
      id: Date.now().toString(),
      code: `RULE${String(scoringRules.length + 1).padStart(3, '0')}`,
      name: `${record.name}_副本`,
    };
    setScoringRules([...scoringRules, newRule]);
    message.success('规则复制成功');
  };

  const handleToggleRuleStatus = (record: ScoringRule) => {
    setScoringRules(scoringRules.map(r => 
      r.id === record.id ? { ...r, status: r.status === 'active' ? 'inactive' : 'active' } : r
    ));
    message.success(`规则已${record.status === 'active' ? '停用' : '启用'}`);
  };

  // 数据字典相关操作
  const handleAddDictionary = () => {
    setEditingDictionary(null);
    dictionaryForm.resetFields();
    setDictionaryModalVisible(true);
  };

  const handleEditDictionary = (record: DictionaryItem) => {
    setEditingDictionary(record);
    dictionaryForm.setFieldsValue(record);
    setDictionaryModalVisible(true);
  };

  const handleSaveDictionary = async () => {
    try {
      const values = await dictionaryForm.validateFields();
      if (editingDictionary) {
        setDictionaries(dictionaries.map(d => d.id === editingDictionary.id ? { ...editingDictionary, ...values } : d));
        message.success('字典更新成功');
      } else {
        const newDictionary = {
          id: Date.now().toString(),
          code: `DICT${String(dictionaries.length + 1).padStart(3, '0')}`,
          ...values,
          status: 'active' as const,
          itemCount: 0,
        };
        setDictionaries([...dictionaries, newDictionary]);
        message.success('字典创建成功');
      }
      setDictionaryModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleDictionaryStatus = (record: DictionaryItem) => {
    setDictionaries(dictionaries.map(d => 
      d.id === record.id ? { ...d, status: d.status === 'active' ? 'inactive' : 'active' } : d
    ));
    message.success(`字典已${record.status === 'active' ? '停用' : '启用'}`);
  };

  // 公司地址相关操作
  const handleAddAddress = () => {
    setEditingAddress(null);
    addressForm.resetFields();
    setAddressModalVisible(true);
  };

  const handleEditAddress = (record: CompanyAddress) => {
    setEditingAddress(record);
    addressForm.setFieldsValue(record);
    setAddressModalVisible(true);
  };

  const handleSaveAddress = async () => {
    try {
      const values = await addressForm.validateFields();
      if (editingAddress) {
        setCompanyAddresses(companyAddresses.map(a => a.id === editingAddress.id ? { ...editingAddress, ...values } : a));
        message.success('地址更新成功');
      } else {
        const newAddress = {
          id: Date.now().toString(),
          ...values,
          status: 'active' as const,
        };
        setCompanyAddresses([...companyAddresses, newAddress]);
        message.success('地址创建成功');
      }
      setAddressModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleAddressStatus = (record: CompanyAddress) => {
    setCompanyAddresses(companyAddresses.map(a => 
      a.id === record.id ? { ...a, status: a.status === 'active' ? 'inactive' : 'active' } : a
    ));
    message.success(`地址已${record.status === 'active' ? '停用' : '启用'}`);
  };

  // 表格列定义
  const stageColumns = [
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
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditStage(record)}>编辑</Button>
          <Button type="link" size="small" icon={record.status === 'active' ? <StopOutlined /> : <PlayCircleOutlined />} onClick={() => handleToggleStageStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
          <Popconfirm title="确定删除?" onConfirm={() => handleDeleteStage(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      )
    },
  ];

  const processColumns = [
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
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditProcess(record)}>编辑</Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => handleCopyProcess(record)}>复制</Button>
          <Button type="link" size="small" icon={record.status === 'active' ? <StopOutlined /> : <PlayCircleOutlined />} onClick={() => handleToggleProcessStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      )
    },
  ];

  const ruleColumns = [
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
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditRule(record)}>编辑</Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => handleCopyRule(record)}>复制</Button>
          <Button type="link" size="small" icon={record.status === 'active' ? <StopOutlined /> : <PlayCircleOutlined />} onClick={() => handleToggleRuleStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      )
    },
  ];

  const dictionaryColumns = [
    { title: '字典编号', dataIndex: 'code', key: 'code', width: 120 },
    { title: '字典名称', dataIndex: 'name', key: 'name' },
    { title: '所属分类', dataIndex: 'category', key: 'category', width: 120 },
    { title: '选项数量', dataIndex: 'itemCount', key: 'itemCount', width: 100 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (status: string) => <Tag color={status === 'active' ? 'success' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>
    },
    { title: '操作', key: 'action', width: 200,
      render: (_: any, record: DictionaryItem) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditDictionary(record)}>编辑</Button>
          <Button type="link" size="small" icon={record.status === 'active' ? <StopOutlined /> : <PlayCircleOutlined />} onClick={() => handleToggleDictionaryStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      )
    },
  ];

  const addressColumns = [
    { title: '地址名称', dataIndex: 'name', key: 'name' },
    { title: '所在地区', dataIndex: 'region', key: 'region' },
    { title: '详细地址', dataIndex: 'address', key: 'address' },
    { title: '定位状态', key: 'location', width: 100,
      render: (_: any, record: CompanyAddress) => (
        record.longitude ? <Tag color="success">已定位</Tag> : <Tag color="default">未定位</Tag>
      )
    },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (status: string) => <Tag color={status === 'active' ? 'success' : 'default'}>{status === 'active' ? '启用' : '停用'}</Tag>
    },
    { title: '操作', key: 'action', width: 200,
      render: (_: any, record: CompanyAddress) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEditAddress(record)}>编辑</Button>
          <Button type="link" size="small" icon={record.status === 'active' ? <StopOutlined /> : <PlayCircleOutlined />} onClick={() => handleToggleAddressStatus(record)}>
            {record.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      )
    },
  ];

  const tabItems = [
    {
      key: 'process',
      label: '招聘流程管理',
      children: (
        <div>
          <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAddProcess}>新增流程</Button>
            </Space>
          </div>
          <Table columns={processColumns} dataSource={processes} rowKey="id" pagination={false} />
        </div>
      ),
    },
    {
      key: 'stage',
      label: '阶段配置',
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddStage}>新增阶段</Button>
          </div>
          <Table columns={stageColumns} dataSource={stages} rowKey="id" pagination={false} />
        </div>
      ),
    },
    {
      key: 'scoring',
      label: '评分规则',
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddRule}>新增规则</Button>
          </div>
          <Table columns={ruleColumns} dataSource={scoringRules} rowKey="id" pagination={false} />
        </div>
      ),
    },
    {
      key: 'dictionary',
      label: '数据字典',
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddDictionary}>新增字典</Button>
          </div>
          <Table columns={dictionaryColumns} dataSource={dictionaries} rowKey="id" pagination={false} />
        </div>
      ),
    },
    {
      key: 'company',
      label: '公司设置',
      children: (
        <div>
          <div style={{ marginBottom: 16 }}>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleAddAddress}>新增地址</Button>
          </div>
          <Table columns={addressColumns} dataSource={companyAddresses} rowKey="id" pagination={false} />
        </div>
      ),
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">系统设置</h1>
      </div>
      
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>

      {/* 阶段弹窗 */}
      <Modal
        title={editingStage ? '编辑阶段' : '新增阶段'}
        open={stageModalVisible}
        onOk={handleSaveStage}
        onCancel={() => setStageModalVisible(false)}
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

      {/* 流程弹窗 */}
      <Modal
        title={editingProcess ? '编辑流程' : '新增流程'}
        open={processModalVisible}
        onOk={handleSaveProcess}
        onCancel={() => setProcessModalVisible(false)}
        width={700}
      >
        <Form form={processForm} layout="vertical">
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
                {stages.filter(s => s.status === 'active').map(stage => (
                  <Col span={12} key={stage.id}>
                    <Checkbox value={stage.code}>{stage.name}</Checkbox>
                  </Col>
                ))}
              </Row>
            </Checkbox.Group>
          </Form.Item>
        </Form>
      </Modal>

      {/* 评分规则弹窗 */}
      <Modal
        title={editingRule ? '编辑规则' : '新增规则'}
        open={ruleModalVisible}
        onOk={handleSaveRule}
        onCancel={() => setRuleModalVisible(false)}
        width={600}
      >
        <Form form={ruleForm} layout="vertical">
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

      {/* 数据字典弹窗 */}
      <Modal
        title={editingDictionary ? '编辑字典' : '新增字典'}
        open={dictionaryModalVisible}
        onOk={handleSaveDictionary}
        onCancel={() => setDictionaryModalVisible(false)}
        width={600}
      >
        <Form form={dictionaryForm} layout="vertical">
          <Form.Item name="name" label="字典名称" rules={[{ required: true, message: '请输入字典名称' }]}>
            <Input placeholder="请输入字典名称" />
          </Form.Item>
          <Form.Item name="category" label="所属分类" rules={[{ required: true, message: '请选择所属分类' }]}>
            <Select placeholder="请选择所属分类">
              <Select.Option value="基本信息">基本信息</Select.Option>
              <Select.Option value="职位信息">职位信息</Select.Option>
              <Select.Option value="面试信息">面试信息</Select.Option>
              <Select.Option value="Offer信息">Offer信息</Select.Option>
              <Select.Option value="归档信息">归档信息</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* 公司地址弹窗 */}
      <Modal
        title={editingAddress ? '编辑地址' : '新增地址'}
        open={addressModalVisible}
        onOk={handleSaveAddress}
        onCancel={() => setAddressModalVisible(false)}
        width={600}
      >
        <Form form={addressForm} layout="vertical">
          <Form.Item name="name" label="地址名称" rules={[{ required: true, message: '请输入地址名称' }]}>
            <Input placeholder="如：上海总部、深圳分部" />
          </Form.Item>
          <Form.Item name="region" label="所在地区" rules={[{ required: true, message: '请选择所在地区' }]}>
            <Input placeholder="省-市-区" />
          </Form.Item>
          <Form.Item name="address" label="详细地址" rules={[{ required: true, message: '请输入详细地址' }]}>
            <Input placeholder="请输入详细地址" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Settings;
