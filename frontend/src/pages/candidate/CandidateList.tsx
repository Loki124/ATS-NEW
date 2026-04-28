import React, { useState } from 'react';
import { Card, Table, Button, Space, Input, Select, Tag, Dropdown, message, Avatar, Typography, Row, Col, Modal } from 'antd';
import { PlusOutlined, SearchOutlined, FilterOutlined, DownloadOutlined, MoreOutlined, UserOutlined, PhoneOutlined, MailOutlined, CalendarOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import AddCandidateModal from './AddCandidateModal';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;
const { Option } = Select;

const CandidateList: React.FC = () => {
  const navigate = useNavigate();
  const [addModalVisible, setAddModalVisible] = useState(false);
  const [searchText, setSearchText] = useState('');

  const handleAddSuccess = () => {
    message.success('候选人添加成功');
  };

  const handleViewDetail = (record: any) => {
    navigate(`/candidates/${record.key}`);
  };

  const columns = [
    {
      title: '候选人',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: any) => (
        <div 
          style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}
          onClick={() => handleViewDetail(record)}
        >
          <Avatar style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
            {text?.[0] || 'A'}
          </Avatar>
          <div>
            <div style={{ fontWeight: 500, color: '#667eea' }}>{text}</div>
            <div style={{ fontSize: '12px', color: '#999' }}>{record.email}</div>
          </div>
        </div>
      ),
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      key: 'phone',
      render: (text: string) => (
        <span><PhoneOutlined style={{ marginRight: '4px' }} />{text}</span>
      ),
    },
    {
      title: '应聘职位',
      dataIndex: 'position',
      key: 'position',
      render: (text: string) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '简历来源',
      dataIndex: 'channel',
      key: 'channel',
      render: (text: string) => {
        const channelMap: any = {
          'boss': { text: 'Boss直聘', color: 'purple' },
          'lagou': { text: '拉勾网', color: 'cyan' },
          'liepin': { text: '猎聘网', color: 'orange' },
          'internal': { text: '内部推荐', color: 'green' },
        };
        const channel = channelMap[text] || { text, color: 'default' };
        return <Tag color={channel.color}>{channel.text}</Tag>;
      },
    },
    {
      title: '当前阶段',
      dataIndex: 'stage',
      key: 'stage',
      render: (text: string) => {
        const stageMap: any = {
          'screening': { text: '筛选中', color: 'processing' },
          'interview': { text: '面试中', color: 'warning' },
          'offer': { text: 'Offer沟通', color: 'orange' },
          'hired': { text: '已入职', color: 'success' },
        };
        const stage = stageMap[text] || { text, color: 'default' };
        return <Tag color={stage.color}>{stage.text}</Tag>;
      },
    },
    {
      title: '添加时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (text: string) => text,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: any) => {
        const menuItems: MenuProps['items'] = [
          { key: 'view', label: '查看详情', onClick: () => handleViewDetail(record) },
          { key: 'edit', label: '编辑' },
          { key: 'transfer', label: '转移到其他职位' },
          { type: 'divider' },
          { key: 'archive', label: '归档', danger: true },
        ];
        
        return (
          <Space>
            <Button type="link" size="small" onClick={() => handleViewDetail(record)}>查看</Button>
            <Dropdown menu={{ items: menuItems }} trigger={['click']}>
              <Button type="text" size="small" icon={<MoreOutlined />} />
            </Dropdown>
          </Space>
        );
      },
    },
  ];

  const mockData = [
    {
      key: '1',
      name: '张三',
      email: 'zhangsan@example.com',
      phone: '138****8888',
      position: '前端开发工程师',
      channel: 'boss',
      stage: 'screening',
      createdAt: '2026-04-27',
    },
    {
      key: '2',
      name: '李四',
      email: 'lisi@example.com',
      phone: '139****6666',
      position: '产品经理',
      channel: 'lagou',
      stage: 'interview',
      createdAt: '2026-04-26',
    },
    {
      key: '3',
      name: '王五',
      email: 'wangwu@example.com',
      phone: '137****5555',
      position: 'UI设计师',
      channel: 'liepin',
      stage: 'offer',
      createdAt: '2026-04-25',
    },
    {
      key: '4',
      name: '赵六',
      email: 'zhaoliu@example.com',
      phone: '136****4444',
      position: '后端开发工程师',
      channel: 'internal',
      stage: 'hired',
      createdAt: '2026-04-24',
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '24px', fontWeight: 600 }}>候选人管理</h1>
          <Text type="secondary">管理所有候选人信息，推进招聘流程</Text>
        </div>
        <Button 
          type="primary" 
          icon={<PlusOutlined />}
          size="large"
          onClick={() => setAddModalVisible(true)}
          style={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
            height: '40px',
            paddingLeft: '20px',
            paddingRight: '20px'
          }}
        >
          新增候选人
        </Button>
      </div>

      {/* 筛选区域 */}
      <Card style={{ marginBottom: '16px', borderRadius: '12px' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜索候选人姓名、手机号、邮箱..."
                prefix={<SearchOutlined />}
                style={{ width: '280px', borderRadius: '8px' }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
              <Select placeholder="应聘职位" style={{ width: '160px' }} allowClear>
                <Option value="1">前端开发工程师</Option>
                <Option value="2">后端开发工程师</Option>
                <Option value="3">产品经理</Option>
                <Option value="4">UI设计师</Option>
              </Select>
              <Select placeholder="简历来源" style={{ width: '140px' }} allowClear>
                <Option value="boss">Boss直聘</Option>
                <Option value="lagou">拉勾网</Option>
                <Option value="liepin">猎聘网</Option>
                <Option value="internal">内部推荐</Option>
              </Select>
              <Select placeholder="当前阶段" style={{ width: '120px' }} allowClear>
                <Option value="screening">筛选中</Option>
                <Option value="interview">面试中</Option>
                <Option value="offer">Offer沟通</Option>
                <Option value="hired">已入职</Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button icon={<DownloadOutlined />}>导出数据</Button>
              <Button icon={<FilterOutlined />}>更多筛选</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 统计数据 */}
      <Row gutter={16} style={{ marginBottom: '16px' }}>
        <Col span={6}>
          <Card size="small" style={{ borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#667eea' }}>156</div>
            <div style={{ fontSize: '12px', color: '#999' }}>候选人总数</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#13c2c2' }}>45</div>
            <div style={{ fontSize: '12px', color: '#999' }}>筛选中</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#faad14' }}>28</div>
            <div style={{ fontSize: '12px', color: '#999' }}>面试中</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ borderRadius: '8px', textAlign: 'center' }}>
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#52c41a' }}>8</div>
            <div style={{ fontSize: '12px', color: '#999' }}>待入职</div>
          </Card>
        </Col>
      </Row>

      {/* 表格 */}
      <Card style={{ borderRadius: '12px' }}>
        <Table
          columns={columns}
          dataSource={mockData}
          pagination={{
            total: 156,
            pageSize: 10,
            showTotal: (total) => `共 ${total} 条`,
            showSizeChanger: true,
            showQuickJumper: true,
          }}
          style={{ borderRadius: '8px' }}
        />
      </Card>

      {/* 新增候选人弹窗 */}
      <AddCandidateModal
        visible={addModalVisible}
        onClose={() => setAddModalVisible(false)}
        onSuccess={handleAddSuccess}
      />
    </div>
  );
};

export default CandidateList;
