import React, { useState } from 'react';
import { Form, Input, Button, Card, message, Tabs } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { store } from '../store';
import { setUser } from '../store/userSlice';
import './Login.css';

const Login: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('account');
  const navigate = useNavigate();

  const handleLogin = async (values: any) => {
    setLoading(true);
    
    // 模拟登录
    setTimeout(() => {
      // 保存token
      localStorage.setItem('token', 'mock_token_' + Date.now());
      
      // 设置用户信息
      store.dispatch(setUser({
        id: '1',
        username: values.username || 'admin',
        realName: values.username === 'admin' ? '管理员' : '测试用户',
        email: 'admin@company.com',
        phone: '138****8888',
        role: 'admin',
      }));

      message.success('登录成功！');
      setLoading(false);
      navigate('/dashboard');
    }, 800);
  };

  const onFinish = (values: any) => {
    handleLogin(values);
  };

  return (
    <div className="login-page">
      <div className="login-background">
        <div className="login-shapes">
          <div className="shape shape-1"></div>
          <div className="shape shape-2"></div>
          <div className="shape shape-3"></div>
        </div>
      </div>
      
      <div className="login-container">
        <div className="login-brand">
          <div className="brand-logo">
            <svg viewBox="0 0 24 24" fill="currentColor" className="logo-icon">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
          </div>
          <h1 className="brand-title">ATS招聘管理系统</h1>
          <p className="brand-subtitle">智能招聘 · 高效管理 · 数据驱动</p>
        </div>

        <Card className="login-card" bordered={false}>
          <Tabs 
            activeKey={activeTab} 
            onChange={setActiveTab}
            centered
            className="login-tabs"
          >
            <Tabs.TabPane tab="账号密码" key="account">
              <Form
                name="login"
                onFinish={onFinish}
                size="large"
                className="login-form"
              >
                <Form.Item
                  name="username"
                  rules={[{ required: true, message: '请输入用户名!' }]}
                >
                  <Input 
                    prefix={<UserOutlined className="input-icon" />}
                    placeholder="用户名" 
                  />
                </Form.Item>

                <Form.Item
                  name="password"
                  rules={[{ required: true, message: '请输入密码!' }]}
                >
                  <Input.Password
                    prefix={<LockOutlined className="input-icon" />}
                    placeholder="密码"
                  />
                </Form.Item>

                <Form.Item>
                  <div className="form-options">
                    <label className="remember-me">
                      <input type="checkbox" />
                      <span>记住我</span>
                    </label>
                    <a href="#" className="forgot-link">忘记密码?</a>
                  </div>
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    block
                    loading={loading}
                    className="login-button"
                  >
                    登 录
                  </Button>
                </Form.Item>
              </Form>
            </Tabs.TabPane>

            <Tabs.TabPane tab="手机验证码" key="sms">
              <Form
                name="smsLogin"
                onFinish={onFinish}
                size="large"
                className="login-form"
              >
                <Form.Item
                  name="phone"
                  rules={[{ required: true, message: '请输入手机号!' }]}
                >
                  <Input 
                    prefix={<span className="input-icon">📱</span>}
                    placeholder="请输入手机号" 
                  />
                </Form.Item>

                <Form.Item
                  name="code"
                  rules={[{ required: true, message: '请输入验证码!' }]}
                >
                  <div className="code-input-wrapper">
                    <Input 
                      prefix={<LockOutlined className="input-icon" />}
                      placeholder="验证码"
                      className="code-input"
                    />
                    <Button className="code-button">获取验证码</Button>
                  </div>
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit" 
                    block
                    loading={loading}
                    className="login-button"
                  >
                    登 录
                  </Button>
                </Form.Item>
              </Form>
            </Tabs.TabPane>
          </Tabs>

          <div className="login-footer">
            <p>默认账号: admin / admin123</p>
          </div>
        </Card>

        <div className="login-features">
          <div className="feature-item">
            <span className="feature-icon">📊</span>
            <span>数据看板</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">👥</span>
            <span>人才库</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">📋</span>
            <span>流程管理</span>
          </div>
          <div className="feature-item">
            <span className="feature-icon">🔔</span>
            <span>智能提醒</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
