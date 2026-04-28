import React, { useState } from 'react';
import { Modal, Form, Input, Select, Upload, Button, Steps, Space, message, Divider } from 'antd';
import { PlusOutlined, UploadOutlined, UserOutlined, PhoneOutlined, MailOutlined, CalendarOutlined, InboxOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';

const { Option } = Select;
const { TextArea } = Input;
const { Dragger } = Upload;

interface AddCandidateModalProps {
  visible: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

const AddCandidateModal: React.FC<AddCandidateModalProps> = ({ visible, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [resumeFile, setResumeFile] = useState<any>(null);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      
      // 模拟提交
      setTimeout(() => {
        message.success('候选人添加成功！');
        setLoading(false);
        form.resetFields();
        setCurrentStep(0);
        setResumeFile(null);
        onSuccess();
        onClose();
      }, 1000);
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  const handleFileChange: UploadProps['onChange'] = (info) => {
    const file = info.file.originFileObj || info.file;
    setResumeFile(file);
    message.success(`${info.file.name} 上传成功`);
  };

  const handleCancel = () => {
    form.resetFields();
    setCurrentStep(0);
    setResumeFile(null);
    onClose();
  };

  const uploadProps: UploadProps = {
    name: 'file',
    multiple: false,
    accept: '.pdf,.doc,.docx,.jpg,.jpeg,.png,.xls,.xlsx',
    beforeUpload: (file) => {
      setResumeFile(file);
      return false;
    },
    onChange: handleFileChange,
    fileList: resumeFile ? [resumeFile as any] : [],
  };

  const steps = [
    { title: '基本信息', icon: <UserOutlined /> },
    { title: '简历上传', icon: <UploadOutlined /> },
    { title: '确认提交', icon: <InboxOutlined /> },
  ];

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ 
            width: '32px', 
            height: '32px', 
            borderRadius: '8px', 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontSize: '16px'
          }}>
            <PlusOutlined />
          </div>
          <span style={{ fontSize: '18px', fontWeight: 600 }}>新增候选人</span>
        </div>
      }
      open={visible}
      onCancel={handleCancel}
      width={720}
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Button onClick={() => currentStep > 0 && setCurrentStep(currentStep - 1)} disabled={currentStep === 0}>
            上一步
          </Button>
          <Space>
            <Button onClick={handleCancel}>取消</Button>
            {currentStep < steps.length - 1 ? (
              <Button type="primary" onClick={() => setCurrentStep(currentStep + 1)}>
                下一步
              </Button>
            ) : (
              <Button type="primary" onClick={handleSubmit} loading={loading}>
                确认提交
              </Button>
            )}
          </Space>
        </div>
      }
      destroyOnClose
    >
      <Steps 
        current={currentStep} 
        items={steps}
        style={{ marginBottom: '24px', padding: '0 20px' }}
      />

      <div style={{ minHeight: '400px' }}>
        {/* 步骤1: 基本信息 */}
        {currentStep === 0 && (
          <div>
            <Form
              form={form}
              layout="vertical"
              initialValues={{ gender: 'male', education: '本科' }}
            >
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <Form.Item
                  name="name"
                  label={<span style={{ fontWeight: 500 }}>姓名 <span style={{ color: '#ff4d4f' }}>*</span></span>}
                  rules={[{ required: true, message: '请输入候选人姓名' }]}
                >
                  <Input placeholder="请输入候选人姓名" size="large" />
                </Form.Item>

                <Form.Item
                  name="phone"
                  label={<span style={{ fontWeight: 500 }}>手机号 <span style={{ color: '#ff4d4f' }}>*</span></span>}
                  rules={[
                    { required: true, message: '请输入手机号' },
                    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号' }
                  ]}
                >
                  <Input prefix={<PhoneOutlined />} placeholder="请输入手机号" size="large" />
                </Form.Item>

                <Form.Item
                  name="email"
                  label={<span style={{ fontWeight: 500 }}>邮箱</span>}
                  rules={[{ type: 'email', message: '请输入正确的邮箱' }]}
                >
                  <Input prefix={<MailOutlined />} placeholder="请输入邮箱" size="large" />
                </Form.Item>

                <Form.Item
                  name="gender"
                  label={<span style={{ fontWeight: 500 }}>性别</span>}
                >
                  <Select placeholder="请选择性别" size="large">
                    <Option value="male">男</Option>
                    <Option value="female">女</Option>
                  </Select>
                </Form.Item>

                <Form.Item
                  name="birthDate"
                  label={<span style={{ fontWeight: 500 }}>出生日期</span>}
                >
                  <Input prefix={<CalendarOutlined />} type="date" placeholder="请选择出生日期" size="large" />
                </Form.Item>

                <Form.Item
                  name="education"
                  label={<span style={{ fontWeight: 500 }}>最高学历</span>}
                >
                  <Select placeholder="请选择学历" size="large">
                    <Option value="高中">高中</Option>
                    <Option value="大专">大专</Option>
                    <Option value="本科">本科</Option>
                    <Option value="硕士">硕士</Option>
                    <Option value="博士">博士</Option>
                  </Select>
                </Form.Item>
              </div>

              <Form.Item
                name="position"
                label={<span style={{ fontWeight: 500 }}>应聘职位 <span style={{ color: '#ff4d4f' }}>*</span></span>}
                rules={[{ required: true, message: '请选择应聘职位' }]}
              >
                <Select 
                  placeholder="请选择应聘职位" 
                  size="large"
                  showSearch
                  filterOption={(input, option) =>
                    (option?.children as unknown as string).toLowerCase().includes(input.toLowerCase())
                  }
                >
                  <Option value="1">前端开发工程师</Option>
                  <Option value="2">后端开发工程师</Option>
                  <Option value="3">产品经理</Option>
                  <Option value="4">UI设计师</Option>
                  <Option value="5">测试工程师</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="channel"
                label={<span style={{ fontWeight: 500 }}>简历来源 <span style={{ color: '#ff4d4f' }}>*</span></span>}
                rules={[{ required: true, message: '请选择简历来源' }]}
              >
                <Select placeholder="请选择简历来源" size="large">
                  <Option value="boss">Boss直聘</Option>
                  <Option value="lagou">拉勾网</Option>
                  <Option value="liepin">猎聘网</Option>
                  <Option value="zhilian">智联招聘</Option>
                  <Option value="51job">前程无忧</Option>
                  <Option value="internal">内部推荐</Option>
                  <Option value="other">其他渠道</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="recommender"
                label={<span style={{ fontWeight: 500 }}>简历推荐人</span>}
              >
                <Input placeholder="请输入推荐人姓名" size="large" />
              </Form.Item>

              <Form.Item
                name="remark"
                label={<span style={{ fontWeight: 500 }}>备注</span>}
              >
                <TextArea rows={3} placeholder="请输入备注信息" />
              </Form.Item>
            </Form>
          </div>
        )}

        {/* 步骤2: 简历上传 */}
        {currentStep === 1 && (
          <div>
            <Dragger {...uploadProps} style={{ padding: '40px' }}>
              <p className="ant-upload-drag-icon" style={{ marginBottom: '16px' }}>
                <InboxOutlined style={{ fontSize: '48px', color: '#667eea' }} />
              </p>
              <p className="ant-upload-text" style={{ fontSize: '16px', fontWeight: 500 }}>
                点击或拖拽上传简历文件
              </p>
              <p className="ant-upload-hint" style={{ color: '#999' }}>
                支持 PDF、Word、Excel、图片格式，单个文件不超过10MB
              </p>
            </Dragger>

            <Divider>或</Divider>

            <div style={{ textAlign: 'center' }}>
              <Upload {...uploadProps} showUploadList={false}>
                <Button icon={<UploadOutlined />} size="large">
                  选择文件
                </Button>
              </Upload>
            </div>

            {resumeFile && (
              <div style={{ marginTop: '24px', padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ 
                    width: '40px', 
                    height: '40px', 
                    borderRadius: '8px', 
                    background: '#667eea',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white'
                  }}>
                    <UserOutlined />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 500 }}>{resumeFile.name}</div>
                    <div style={{ fontSize: '12px', color: '#999' }}>
                      {(resumeFile.size / 1024 / 1024).toFixed(2)} MB
                    </div>
                  </div>
                  <Button type="link" danger onClick={() => setResumeFile(null)}>
                    移除
                  </Button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 步骤3: 确认提交 */}
        {currentStep === 2 && (
          <div>
            <div style={{ background: '#f8f9ff', padding: '24px', borderRadius: '12px', marginBottom: '24px' }}>
              <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: '#333' }}>
                📋 信息确认
              </div>
              
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div>
                  <div style={{ color: '#999', fontSize: '12px' }}>姓名</div>
                  <div style={{ fontWeight: 500 }}>{form.getFieldValue('name') || '-'}</div>
                </div>
                <div>
                  <div style={{ color: '#999', fontSize: '12px' }}>手机号</div>
                  <div style={{ fontWeight: 500 }}>{form.getFieldValue('phone') || '-'}</div>
                </div>
                <div>
                  <div style={{ color: '#999', fontSize: '12px' }}>邮箱</div>
                  <div style={{ fontWeight: 500 }}>{form.getFieldValue('email') || '-'}</div>
                </div>
                <div>
                  <div style={{ color: '#999', fontSize: '12px' }}>性别</div>
                  <div style={{ fontWeight: 500 }}>{form.getFieldValue('gender') === 'male' ? '男' : '女'}</div>
                </div>
                <div>
                  <div style={{ color: '#999', fontSize: '12px' }}>最高学历</div>
                  <div style={{ fontWeight: 500 }}>{form.getFieldValue('education') || '-'}</div>
                </div>
                <div>
                  <div style={{ color: '#999', fontSize: '12px' }}>简历来源</div>
                  <div style={{ fontWeight: 500 }}>{form.getFieldValue('channel') || '-'}</div>
                </div>
              </div>
            </div>

            {resumeFile && (
              <div style={{ background: '#fff7e6', padding: '16px', borderRadius: '8px', border: '1px solid #ffe58f' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ 
                    width: '36px', 
                    height: '36px', 
                    borderRadius: '8px', 
                    background: '#faad14',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white'
                  }}>
                    <UploadOutlined />
                  </div>
                  <div>
                    <div style={{ fontWeight: 500 }}>已上传简历</div>
                    <div style={{ fontSize: '12px', color: '#999' }}>{resumeFile.name}</div>
                  </div>
                </div>
              </div>
            )}

            <div style={{ marginTop: '24px', padding: '16px', background: '#f5f5f5', borderRadius: '8px' }}>
              <div style={{ color: '#667eea', fontWeight: 500 }}>
                💡 提示：提交后将自动进行简历解析和查重，重复简历会有提示。
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};

export default AddCandidateModal;
