import React from 'react';
import { Card, Row, Col, Typography, Button, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div style={{ padding: '24px', minHeight: '100%' }}>
      <Card 
        style={{ 
          borderRadius: '12px',
          boxShadow: '0 2px 12px rgba(0,0,0,0.08)'
        }}
      >
        <div style={{ textAlign: 'center', padding: '60px 20px' }}>
          <Title level={2}>🎉 ATS招聘管理系统</Title>
          <Text type="secondary" style={{ fontSize: '16px' }}>
            欢迎使用招聘管理系统
          </Text>
          
          <div style={{ marginTop: '40px' }}>
            <Space size="large" wrap>
              <Button 
                type="primary" 
                size="large"
                icon={<PlusOutlined />}
                onClick={() => navigate('/demands')}
              >
                创建需求
              </Button>
              <Button 
                size="large"
                onClick={() => navigate('/candidates')}
              >
                候选人管理
              </Button>
              <Button 
                size="large"
                onClick={() => navigate('/positions')}
              >
                职位管理
              </Button>
            </Space>
          </div>

          <div style={{ marginTop: '60px', padding: '20px', background: '#f5f5f5', borderRadius: '8px' }}>
            <Title level={4}>📊 招聘数据概览</Title>
            <Row gutter={[24, 24]} style={{ marginTop: '20px' }}>
              <Col xs={24} sm={12} md={6}>
                <Card size="small" style={{ borderRadius: '8px' }}>
                  <Text type="secondary">招聘需求</Text>
                  <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#667eea' }}>28</div>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small" style={{ borderRadius: '8px' }}>
                  <Text type="secondary">进行中职位</Text>
                  <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#13c2c2' }}>156</div>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small" style={{ borderRadius: '8px' }}>
                  <Text type="secondary">候选人</Text>
                  <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#faad14' }}>892</div>
                </Card>
              </Col>
              <Col xs={24} sm={12} md={6}>
                <Card size="small" style={{ borderRadius: '8px' }}>
                  <Text type="secondary">本周面试</Text>
                  <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#52c41a' }}>45</div>
                </Card>
              </Col>
            </Row>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default Dashboard;
