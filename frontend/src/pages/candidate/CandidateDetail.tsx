import React, { useState } from 'react';
import { Card, Tabs, Button, Space, Tag, Avatar, Typography, Row, Col, Modal, Form, Input, Select, message, Timeline, Divider, Badge, Dropdown, Checkbox } from 'antd';
import { 
  ArrowLeftOutlined, 
  MailOutlined, 
  PhoneOutlined, 
  MessageOutlined, 
  WechatOutlined,
  CalendarOutlined,
  UserOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SendOutlined,
  MoreOutlined,
  EditOutlined,
  DeleteOutlined,
  ExportOutlined,
  BulbOutlined,
  CloseOutlined
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useNavigate, useParams } from 'react-router-dom';

const { Text, Title } = Typography;
const { TextArea } = Input;

const NotificationModal: React.FC<{ visible: boolean; onCancel: () => void; candidateData: any }> = ({ visible, onCancel, candidateData }) => {
  const [selectedContents, setSelectedContents] = useState<string[]>(['interview_form']);
  const [selectedMethods, setSelectedMethods] = useState<string[]>(['email', 'sms']);
  const [emailSubject, setEmailSubject] = useState('【RecruitFlow科技】面试邀请与前期准备事项');
  const [emailContent, setEmailContent] = useState(`尊敬的 {{候选人姓名}}，您好！

感谢您对RecruitFlow科技的关注。很高兴通知您，您的简历已通过初步筛选，我们诚邀您参加【高级前端开发工程师】岗位的视频面试。

在面试前，为了更全面地了解您，请您点击下方专属链接，完成相关信息的填写：

📝 [面试登记表单] {{表单_面试登记表单_链接}}

如您在填写过程中有任何疑问，请随时通过本邮件与我们联系。

祝您一切顺利！
RecruitFlow 招聘团队`);

  const [smsContent, setSmsContent] = useState('【RecruitFlow科技】{{候选人姓名}}您好，诚邀您参加高级前端岗位面试。为保证流程顺畅，请在今天内点击短链接完成信息登记：{{表单_面试登记表单_短链接}}。详情已发送至您的邮箱，请注意查收。退订回T');

  const [loading, setLoading] = useState(false);

  const contentOptions = [
    { value: 'interview_form', label: '面试登记表', desc: '收集候选人基本信息' },
    { value: 'pdp_test', label: 'PDP 性格测试', desc: '耗时约3分钟，在线作答' },
    { value: 'mbti_test', label: 'MBTI 性格测试', desc: '多维度性格评估，耗时10分钟' },
    { value: 'application_form', label: '应聘登记表', desc: '完善工作履历及教育背景' },
  ];

  const methodOptions = [
    { value: 'email', label: '邮件通知', icon: <MailOutlined /> },
    { value: 'sms', label: '短信通知', icon: <MessageOutlined /> },
    { value: 'wechat', label: '微信企业号推送', icon: <WechatOutlined /> },
  ];

  const toggleContent = (value: string) => {
    setSelectedContents(prev => 
      prev.includes(value) 
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  const toggleMethod = (value: string) => {
    setSelectedMethods(prev => 
      prev.includes(value) 
        ? prev.filter(v => v !== value)
        : [...prev, value]
    );
  };

  const handleSend = () => {
    if (selectedContents.length === 0) {
      message.warning('请至少选择一项发送内容');
      return;
    }
    if (selectedMethods.length === 0) {
      message.warning('请至少选择一种通知方式');
      return;
    }
    
    setLoading(true);
    setTimeout(() => {
      message.success('通知发送成功！');
      setLoading(false);
      onCancel();
    }, 1500);
  };

  const smsLength = smsContent.length;
  const smsCount = Math.ceil(smsLength / 70);

  return (
    <Modal
      open={visible}
      onCancel={onCancel}
      width={1000}
      closable={false}
      styles={{
        mask: { background: 'rgba(0,0,0,0.4)' },
        wrapper: { borderRadius: '16px', overflow: 'hidden' },
        content: { borderRadius: '16px', padding: 0, overflow: 'hidden' }
      }}
      footer={null}
    >
      <div style={{ fontFamily: 'Inter, -apple-system, sans-serif' }}>
        {/* Header */}
        <div style={{ 
          padding: '24px', 
          borderBottom: '1px solid #dee3ed',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          background: '#f8f9ff'
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2 style={{ 
                fontFamily: 'Manrope, sans-serif',
                fontSize: '20px',
                fontWeight: 700,
                color: '#161c23',
                margin: 0
              }}>
                发送通知
              </h2>
              <Button 
                type="text" 
                icon={<CloseOutlined />}
                onClick={onCancel}
                style={{ border: 'none' }}
              />
            </div>
            
            {/* Candidate Info Card */}
            <div style={{ 
              background: '#fff',
              borderRadius: '12px',
              padding: '16px',
              display: 'flex',
              alignItems: 'center',
              gap: '16px'
            }}>
              <Avatar 
                size={48}
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuB63vWZHAZxgN1RgyObhTocmFcRwSPmh6xRQqTNI4yviPnT1wZcbfB_PczyZUPAkomjkvFhWow4LqRto_efeErMzg687JhqoUK2GXdtjhIGHX64O5Q0jv-2eNErtgVVPK8yn3885xJdNMvSe5jXQPeqgodEWdu6XHZAr8-SqA9fSytWnsqSC8ahcvLQ9XZTWDXvdm28h67ZUmuRTWJGOqvWrcyMdpbjMlL0vV3oBpE1PaQmY_yoWqR4P4tkbfSAWCr0Bde8EZRcnRU"
                style={{ border: '2px solid #f8f9ff' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, color: '#161c23' }}>
                    {candidateData?.name || '李明浩'}
                  </span>
                  <Tag style={{ 
                    borderRadius: '9999px', 
                    background: '#d7e3ff', 
                    color: '#005ab6', 
                    border: 'none',
                    fontSize: '12px'
                  }}>
                    {candidateData?.position || '高级前端开发工程师'}
                  </Tag>
                  <Tag style={{ 
                    borderRadius: '9999px', 
                    background: '#dee3ed', 
                    color: '#414753', 
                    border: 'none',
                    fontSize: '12px'
                  }}>
                    5年经验
                  </Tag>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '24px', color: '#414753', fontSize: '14px' }}>
                  <span><PhoneOutlined style={{ marginRight: '4px' }} />{candidateData?.phone || '138-8888-9999'}</span>
                  <span><MailOutlined style={{ marginRight: '4px' }} />{candidateData?.email || 'minghao.li@example.com'}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div style={{ display: 'flex', minHeight: '500px' }}>
          {/* Left Sidebar */}
          <div style={{ 
            width: '340px',
            background: '#f8f9ff',
            borderRight: '1px solid #dee3ed',
            padding: '24px',
            display: 'flex',
            flexDirection: 'column',
            gap: '32px',
            overflowY: 'auto'
          }}>
            {/* Step 1 */}
            <div>
              <h3 style={{ 
                fontFamily: 'Inter, sans-serif',
                fontSize: '16px',
                fontWeight: 600,
                color: '#161c23',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: '#1672df',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 600
                }}>1</span>
                选择发送内容
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {contentOptions.map((item) => {
                  const isSelected = selectedContents.includes(item.value);
                  return (
                    <div
                      key={item.value}
                      onClick={() => toggleContent(item.value)}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: `1px solid ${isSelected ? '#005ab6' : 'rgba(114, 119, 133, 0.6)'}`,
                        background: isSelected ? 'rgba(215, 227, 255, 0.2)' : '#fff',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        alignItems: 'flex-start',
                        gap: '8px'
                      }}
                    >
                      <Checkbox 
                        checked={isSelected}
                        style={{ marginTop: '2px' }}
                      />
                      <div>
                        <div style={{ 
                          fontFamily: 'Inter, sans-serif', 
                          fontSize: '14px', 
                          fontWeight: isSelected ? 600 : 400, 
                          color: '#161c23' 
                        }}>
                          {item.label}
                        </div>
                        <div style={{ 
                          fontFamily: 'Inter, sans-serif', 
                          fontSize: '12px', 
                          color: '#414753',
                          marginTop: '2px'
                        }}>
                          {item.desc}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Step 2 */}
            <div>
              <h3 style={{ 
                fontFamily: 'Inter, sans-serif',
                fontSize: '16px',
                fontWeight: 600,
                color: '#161c23',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: '#1672df',
                  color: '#fff',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '12px',
                  fontWeight: 600
                }}>2</span>
                选择通知方式
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {methodOptions.map((item) => {
                  const isSelected = selectedMethods.includes(item.value);
                  return (
                    <div
                      key={item.value}
                      onClick={() => toggleMethod(item.value)}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: `1px solid ${isSelected ? '#005ab6' : 'rgba(114, 119, 133, 0.6)'}`,
                        background: isSelected ? 'rgba(215, 227, 255, 0.2)' : '#fff',
                        cursor: 'pointer',
                        transition: 'all 0.2s ease',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px'
                      }}
                    >
                      <Checkbox checked={isSelected} />
                      <span style={{ 
                        color: isSelected ? '#005ab6' : '#414753',
                        fontSize: '18px'
                      }}>
                        {item.icon}
                      </span>
                      <span style={{ 
                        fontFamily: 'Inter, sans-serif', 
                        fontSize: '14px', 
                        fontWeight: isSelected ? 600 : 400, 
                        color: '#161c23' 
                      }}>
                        {item.label}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Right Content */}
          <div style={{ 
            flex: 1, 
            padding: '24px',
            overflowY: 'auto',
            background: '#f8f9ff'
          }}>
            {/* Info Callout */}
            <div style={{
              background: 'rgba(255, 214, 102, 0.1)',
              border: '1px solid #ffd666',
              borderRadius: '8px',
              padding: '12px',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '8px',
              marginBottom: '24px'
            }}>
              <BulbOutlined style={{ color: '#765c00', fontSize: '18px', marginTop: '2px' }} />
              <p style={{ 
                fontFamily: 'Inter, sans-serif', 
                fontSize: '14px', 
                color: '#241a00',
                margin: 0,
                lineHeight: 1.6
              }}>
                系统将自动为您选中的附件生成独立的安全链接，并插入到下方模板变量中。
              </p>
            </div>

            {/* Email Editor */}
            {selectedMethods.includes('email') && (
              <div style={{ marginBottom: '24px' }}>
                <div style={{ 
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  borderBottom: '1px solid rgba(114, 119, 133, 0.3)',
                  paddingBottom: '12px',
                  marginBottom: '12px'
                }}>
                  <MailOutlined style={{ color: '#005ab6', fontSize: '20px' }} />
                  <h3 style={{ 
                    fontFamily: 'Inter, sans-serif',
                    fontSize: '16px',
                    fontWeight: 600,
                    color: '#161c23',
                    margin: 0
                  }}>
                    邮件通知
                  </h3>
                </div>
                
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ 
                    fontFamily: 'Inter, sans-serif',
                    fontSize: '12px',
                    color: '#414753',
                    display: 'block',
                    marginBottom: '6px'
                  }}>
                    邮件主题
                  </label>
                  <Input 
                    value={emailSubject}
                    onChange={(e) => setEmailSubject(e.target.value)}
                    style={{ 
                      borderRadius: '6px',
                      background: 'rgba(222, 227, 237, 0.3)',
                      border: '1px solid rgba(114, 119, 133, 0.3)'
                    }}
                  />
                </div>

                <div>
                  <label style={{ 
                    fontFamily: 'Inter, sans-serif',
                    fontSize: '12px',
                    color: '#414753',
                    display: 'block',
                    marginBottom: '6px'
                  }}>
                    邮件正文
                  </label>
                  <TextArea 
                    value={emailContent}
                    onChange={(e) => setEmailContent(e.target.value)}
                    rows={10}
                    style={{ 
                      borderRadius: '6px',
                      background: 'rgba(222, 227, 237, 0.3)',
                      border: '1px solid rgba(114, 119, 133, 0.3)',
                      whiteSpace: 'pre-wrap'
                    }}
                  />
                </div>
              </div>
            )}

            {/* SMS Editor */}
            {selectedMethods.includes('sms') && (
              <div>
                <div style={{ 
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  borderBottom: '1px solid rgba(114, 119, 133, 0.3)',
                  paddingBottom: '12px',
                  marginBottom: '12px'
                }}>
                  <MessageOutlined style={{ color: '#005ab6', fontSize: '20px' }} />
                  <h3 style={{ 
                    fontFamily: 'Inter, sans-serif',
                    fontSize: '16px',
                    fontWeight: 600,
                    color: '#161c23',
                    margin: 0
                  }}>
                    短信通知
                  </h3>
                </div>

                <div>
                  <div style={{ 
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-end',
                    marginBottom: '6px'
                  }}>
                    <label style={{ 
                      fontFamily: 'Inter, sans-serif',
                      fontSize: '12px',
                      color: '#414753'
                    }}>
                      短信正文
                    </label>
                    <span style={{ 
                      fontFamily: 'Inter, sans-serif',
                      fontSize: '12px',
                      color: '#727785'
                    }}>
                      已输入 <strong style={{ color: '#005ab6', fontWeight: 500 }}>{smsLength}</strong> / 70 字 (预计计费 {smsCount} 条)
                    </span>
                  </div>
                  <TextArea 
                    value={smsContent}
                    onChange={(e) => setSmsContent(e.target.value)}
                    rows={5}
                    style={{ 
                      borderRadius: '6px',
                      background: 'rgba(222, 227, 237, 0.3)',
                      border: '1px solid rgba(114, 119, 133, 0.3)',
                      whiteSpace: 'pre-wrap'
                    }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div style={{ 
          padding: '16px 24px',
          borderTop: '1px solid #dee3ed',
          background: '#fff',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexShrink: 0,
          position: 'sticky',
          bottom: 0,
          zIndex: 10
        }}>
          <div style={{ 
            fontFamily: 'Inter, sans-serif',
            fontSize: '12px',
            color: '#414753'
          }}>
            通知将发送至: 1个手机号, 1个邮箱地址
          </div>
          <Space>
            <Button 
              onClick={onCancel}
              style={{ 
                borderRadius: '8px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600
              }}
            >
              取消
            </Button>
            <Button 
              type="primary"
              loading={loading}
              onClick={handleSend}
              icon={<SendOutlined />}
              style={{ 
                background: '#ffd666',
                borderColor: '#ffd666',
                color: '#241a00',
                borderRadius: '8px',
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                boxShadow: 'none'
              }}
            >
              确认发送
            </Button>
          </Space>
        </div>
      </div>
    </Modal>
  );
};

const CandidateDetail: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams();
  const [notificationModalVisible, setNotificationModalVisible] = useState(false);

  const candidateData = {
    id: id || '1',
    name: '张三',
    phone: '138****8888',
    email: 'zhangsan@example.com',
    position: '前端开发工程师',
    status: 'interview',
    hrbp: '李明',
    hiringManager: '王芳',
    createdAt: '2026-04-20',
  };

  const moreMenuItems: MenuProps['items'] = [
    { key: 'edit', icon: <EditOutlined />, label: '编辑信息' },
    { key: 'export', icon: <ExportOutlined />, label: '导出简历' },
    { type: 'divider' },
    { key: 'archive', icon: <DeleteOutlined />, label: '归档候选人', danger: true },
  ];

  return (
    <div style={{ 
      padding: '24px', 
      background: '#f8f9ff',
      minHeight: '100vh'
    }}>
      {/* 顶部导航 */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/candidates')}
            style={{ border: 'none', background: 'transparent' }}
          >
            返回
          </Button>
          <Title level={4} style={{ margin: 0, fontFamily: 'Manrope, sans-serif', fontWeight: 700, color: '#161c23' }}>
            候选人详情
          </Title>
        </Space>
        
        <Space>
          <Button 
            type="primary" 
            icon={<SendOutlined />} 
            onClick={() => setNotificationModalVisible(true)}
            style={{ 
              background: '#005ab6', 
              borderColor: '#005ab6',
              borderRadius: '8px',
              fontFamily: 'Inter, sans-serif',
              fontWeight: 600
            }}
          >
            发送通知
          </Button>
          <Dropdown menu={{ items: moreMenuItems }} trigger={['click']}>
            <Button 
              icon={<MoreOutlined />} 
              style={{ border: 'none', background: 'transparent' }}
            />
          </Dropdown>
        </Space>
      </div>

      {/* 候选人基本信息卡片 */}
      <Card 
        style={{ 
          marginBottom: '24px', 
          borderRadius: '24px',
          border: 'none',
          boxShadow: '0 8px 32px rgba(0,0,0,0.08)'
        }}
        styles={{ body: { padding: '24px' } }}
      >
        <Row gutter={24} align="middle">
          <Col span={3}>
            <Avatar 
              size={80} 
              style={{ 
                background: 'linear-gradient(135deg, #7431d3 0%, #005ab6 100%)', 
                fontSize: '32px',
                fontFamily: 'Manrope, sans-serif',
                fontWeight: 700
              }}
            >
              {candidateData.name[0]}
            </Avatar>
          </Col>
          <Col span={21}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <Title level={3} style={{ margin: '0 0 8px 0', fontFamily: 'Manrope, sans-serif', color: '#161c23' }}>
                  {candidateData.name}
                  <Badge 
                    status={candidateData.status === 'interview' ? 'processing' : 'success'} 
                    text={candidateData.status === 'interview' ? '面试中' : '已入职'} 
                    style={{ marginLeft: '12px', fontFamily: 'Inter, sans-serif' }} 
                  />
                </Title>
                <Space size="large" style={{ marginBottom: '12px' }}>
                  <Text style={{ fontFamily: 'Inter, sans-serif', color: '#414753' }}>
                    <PhoneOutlined style={{ marginRight: '4px' }} /> {candidateData.phone}
                  </Text>
                  <Text style={{ fontFamily: 'Inter, sans-serif', color: '#414753' }}>
                    <MailOutlined style={{ marginRight: '4px' }} /> {candidateData.email}
                  </Text>
                </Space>
                <div>
                  <Space wrap>
                    <Tag color="blue" style={{ borderRadius: '9999px', padding: '4px 12px', border: 'none', background: '#d7e3ff', color: '#005ab6' }}>
                      {candidateData.position}
                    </Tag>
                    <Tag color="purple" style={{ borderRadius: '9999px', padding: '4px 12px', border: 'none', background: '#ecdcff', color: '#7431d3' }}>
                      Boss直聘
                    </Tag>
                  </Space>
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: '12px', color: '#414753' }}>HRBP：{candidateData.hrbp}</div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: '12px', color: '#414753' }}>用人经理：{candidateData.hiringManager}</div>
              </div>
            </div>
          </Col>
        </Row>
      </Card>

      {/* Tab区域 */}
      <Card 
        style={{ 
          borderRadius: '24px',
          border: 'none',
          boxShadow: '0 8px 32px rgba(0,0,0,0.08)'
        }}
        styles={{ body: { padding: '24px' } }}
      >
        <Tabs
          defaultActiveKey="info"
          items={[
            {
              key: 'info',
              label: (
                <span style={{ fontFamily: 'Inter, sans-serif', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <UserOutlined /> 基本信息
                </span>
              ),
              children: (
                <div>
                  <Row gutter={[24, 16]}>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>姓名</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>{candidateData.name}</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>性别</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>男</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>年龄</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>28岁</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>手机号</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>{candidateData.phone}</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>邮箱</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>{candidateData.email}</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>最高学历</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>本科</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>毕业院校</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>华东理工大学</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>专业</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>计算机科学与技术</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>工作年限</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>5年</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>当前公司</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>字节跳动</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>期望薪资</div>
                        <div style={{ fontFamily: 'Inter, sans-serif', color: '#161c23', fontWeight: 600 }}>40K</div>
                      </div>
                    </Col>
                    <Col span={12}>
                      <div style={{ display: 'flex', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid #dee3ed' }}>
                        <div style={{ width: '100px', fontFamily: 'Inter, sans-serif', color: '#414753', fontSize: '14px' }}>简历来源</div>
                        <Tag style={{ borderRadius: '9999px', background: '#ecdcff', color: '#7431d3', border: 'none' }}>Boss直聘</Tag>
                      </div>
                    </Col>
                  </Row>
                </div>
              ),
            },
            {
              key: 'process',
              label: (
                <span style={{ fontFamily: 'Inter, sans-serif', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <CalendarOutlined /> 招聘流程
                </span>
              ),
              children: (
                <div>
                  <div style={{ marginBottom: '24px' }}>
                    <Title level={5} style={{ fontFamily: 'Manrope, sans-serif', color: '#161c23', marginBottom: '16px' }}>招聘进度</Title>
                    <Timeline
                      items={[
                        { color: 'green', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif' }}>简历筛选</div><div style={{ fontSize: '12px', color: '#414753', fontFamily: 'Inter, sans-serif' }}>时间：2026-04-20 | 操作人：李明</div></div> },
                        { color: 'green', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif' }}>HRBP评估</div><div style={{ fontSize: '12px', color: '#414753', fontFamily: 'Inter, sans-serif' }}>时间：2026-04-21 | 操作人：李明</div></div> },
                        { color: 'green', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif' }}>用人经理筛选</div><div style={{ fontSize: '12px', color: '#414753', fontFamily: 'Inter, sans-serif' }}>时间：2026-04-22 | 操作人：王芳</div></div> },
                        { color: 'green', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif' }}>邀约面试</div><div style={{ fontSize: '12px', color: '#414753', fontFamily: 'Inter, sans-serif' }}>时间：2026-04-23 | 操作人：张强</div></div> },
                        { color: 'blue', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif' }}>联合面试</div><div style={{ fontSize: '12px', color: '#414753', fontFamily: 'Inter, sans-serif' }}>时间：2026-04-25 | 操作人：技术面试官</div></div> },
                        { color: 'gray', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif', color: '#727785' }}>综合面试</div><div style={{ fontSize: '12px', color: '#727785', fontFamily: 'Inter, sans-serif' }}>时间：- | 操作人：-</div></div> },
                        { color: 'gray', children: <div><div style={{ fontWeight: 600, fontFamily: 'Inter, sans-serif', color: '#727785' }}>Offer沟通</div><div style={{ fontSize: '12px', color: '#727785', fontFamily: 'Inter, sans-serif' }}>时间：- | 操作人：-</div></div> },
                      ]}
                    />
                  </div>
                  <Divider style={{ margin: '24px 0' }} />
                  <div>
                    <Title level={5} style={{ fontFamily: 'Manrope, sans-serif', color: '#161c23', marginBottom: '16px' }}>面试记录</Title>
                    <div style={{ background: '#f8f9ff', borderRadius: '12px', padding: '16px' }}>
                      <Row style={{ padding: '12px 0', borderBottom: '1px solid #dee3ed', fontWeight: 600, fontFamily: 'Inter, sans-serif', color: '#414753' }}>
                        <Col span={3}>面试类型</Col>
                        <Col span={4}>面试时间</Col>
                        <Col span={4}>面试官</Col>
                        <Col span={3}>结果</Col>
                        <Col span={7}>反馈</Col>
                        <Col span={3}>操作</Col>
                      </Row>
                      <Row style={{ padding: '12px 0', borderBottom: '1px solid #dee3ed', fontFamily: 'Inter, sans-serif' }} align="middle">
                        <Col span={3}>联合面试</Col>
                        <Col span={4}>2026-04-25 14:00</Col>
                        <Col span={4}>技术面试官A、B</Col>
                        <Col span={3}><Tag color="success" style={{ borderRadius: '9999px' }}>通过</Tag></Col>
                        <Col span={7} style={{ color: '#414753' }}>技术能力强，项目经验丰富</Col>
                        <Col span={3}><Button type="link" size="small">查看详情</Button></Col>
                      </Row>
                      <Row style={{ padding: '12px 0', fontFamily: 'Inter, sans-serif' }} align="middle">
                        <Col span={3}>笔试</Col>
                        <Col span={4}>2026-04-21 10:00</Col>
                        <Col span={4}>HR</Col>
                        <Col span={3}><Tag color="success" style={{ borderRadius: '9999px' }}>通过</Tag></Col>
                        <Col span={7} style={{ color: '#414753' }}>逻辑清晰，编码规范</Col>
                        <Col span={3}><Button type="link" size="small">查看详情</Button></Col>
                      </Row>
                    </div>
                  </div>
                </div>
              ),
            },
            {
              key: 'resume',
              label: (
                <span style={{ fontFamily: 'Inter, sans-serif', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileTextOutlined /> 简历信息
                </span>
              ),
              children: (
                <div style={{ textAlign: 'center', padding: '60px 0' }}>
                  <FileTextOutlined style={{ fontSize: '64px', color: '#7431d3' }} />
                  <Title level={4} style={{ marginTop: '16px', fontFamily: 'Manrope, sans-serif' }}>简历预览</Title>
                  <Text type="secondary" style={{ fontFamily: 'Inter, sans-serif' }}>简历文件将在这里展示</Text>
                  <div style={{ marginTop: '24px' }}>
                    <Space>
                      <Button type="primary" icon={<ExportOutlined />} style={{ background: '#005ab6', borderColor: '#005ab6', borderRadius: '8px' }}>下载简历</Button>
                      <Button icon={<EditOutlined />} style={{ borderRadius: '8px' }}>编辑简历</Button>
                    </Space>
                  </div>
                </div>
              ),
            },
            {
              key: 'history',
              label: (
                <span style={{ fontFamily: 'Inter, sans-serif', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <HistoryOutlined /> 操作记录
                </span>
              ),
              children: (
                <div>
                  <Timeline
                    items={[
                      { children: <div><Tag color="blue" style={{ borderRadius: '4px' }}>发送面试通知</Tag><Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>2026-04-27 10:30</Text><div style={{ marginTop: '4px' }}><Text type="secondary">操作人：张强</Text></div><div style={{ marginTop: '4px', color: '#414753' }}>发送给张三关于4月25日联合面试的通知</div></div> },
                      { children: <div><Tag color="success" style={{ borderRadius: '4px' }}>完成面试</Tag><Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>2026-04-25 14:00</Text><div style={{ marginTop: '4px' }}><Text type="secondary">操作人：系统</Text></div><div style={{ marginTop: '4px', color: '#414753' }}>联合面试已完成</div></div> },
                      { children: <div><Tag color="blue" style={{ borderRadius: '4px' }}>安排面试</Tag><Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>2026-04-23 16:00</Text><div style={{ marginTop: '4px' }}><Text type="secondary">操作人：张强</Text></div><div style={{ marginTop: '4px', color: '#414753' }}>安排联合面试时间：4月25日14:00</div></div> },
                      { children: <div><Tag color="success" style={{ borderRadius: '4px' }}>筛选通过</Tag><Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>2026-04-22 11:00</Text><div style={{ marginTop: '4px' }}><Text type="secondary">操作人：王芳</Text></div><div style={{ marginTop: '4px', color: '#414753' }}>用人经理筛选结果：通过</div></div> },
                      { children: <div><Tag color="blue" style={{ borderRadius: '4px' }}>添加候选人</Tag><Text type="secondary" style={{ fontSize: '12px', marginLeft: '8px' }}>2026-04-20 09:00</Text><div style={{ marginTop: '4px' }}><Text type="secondary">操作人：张强</Text></div><div style={{ marginTop: '4px', color: '#414753' }}>从Boss直聘导入候选人信息</div></div> },
                    ]}
                  />
                </div>
              ),
            },
          ]}
        />
      </Card>

      {/* 发送通知弹窗 - 按code.html设计 */}
      <NotificationModal 
        visible={notificationModalVisible} 
        onCancel={() => setNotificationModalVisible(false)}
        candidateData={candidateData}
      />
    </div>
  );
};

export default CandidateDetail;
