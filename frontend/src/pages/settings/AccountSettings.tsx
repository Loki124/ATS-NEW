import React from 'react';
import { Card, Form, Input, Button, message, Divider, Space } from 'antd';
import { store } from '../../store';

const AccountSettings: React.FC = () => {
  const user = store.getState().user.user;
  const [form] = Form.useForm();

  const handleSave = () => {
    message.success('保存成功');
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">账号设置</h1>
      </div>
      <Card>
        <Form form={form} layout="vertical" initialValues={user}>
          <Form.Item label="用户名">
            <Input value={user?.username} disabled />
          </Form.Item>
          <Form.Item label="真实姓名" name="realName">
            <Input placeholder="请输入真实姓名" />
          </Form.Item>
          <Form.Item label="邮箱" name="email">
            <Input placeholder="请输入邮箱" />
          </Form.Item>
          <Form.Item label="手机号" name="phone">
            <Input placeholder="请输入手机号" />
          </Form.Item>
          <Divider />
          <Form.Item label="新密码">
            <Input.Password placeholder="请输入新密码（不修改请留空）" />
          </Form.Item>
          <Form.Item label="确认密码">
            <Input.Password placeholder="请再次输入密码" />
          </Form.Item>
          <Space>
            <Button type="primary" onClick={handleSave}>保存</Button>
            <Button onClick={() => form.resetFields()}>重置</Button>
          </Space>
        </Form>
      </Card>
    </div>
  );
};

export default AccountSettings;
