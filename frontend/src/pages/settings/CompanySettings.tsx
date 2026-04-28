import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, message, Tag, Space } from 'antd';

interface CompanyAddress {
  id: string;
  name: string;
  region: string;
  address: string;
  longitude?: number;
  latitude?: number;
  status: 'active' | 'inactive';
}

const CompanySettings: React.FC = () => {
  const [addresses, setAddresses] = useState<CompanyAddress[]>([
    { id: '1', name: '上海总部', region: '上海市-宝山区', address: '沪太路5008弄200号', longitude: 121.407, latitude: 31.352, status: 'active' },
    { id: '2', name: '深圳分部', region: '广东省-深圳市-南山区', address: '科技园路100号', status: 'active' },
    { id: '3', name: '北京分部', region: '北京市-朝阳区', address: '建国路88号', status: 'inactive' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingAddress, setEditingAddress] = useState<CompanyAddress | null>(null);
  const [form] = Form.useForm();

  const handleAdd = () => {
    setEditingAddress(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: CompanyAddress) => {
    setEditingAddress(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingAddress) {
        setAddresses(addresses.map(a => a.id === editingAddress.id ? { ...editingAddress, ...values } : a));
        message.success('地址更新成功');
      } else {
        const newAddress = {
          id: Date.now().toString(),
          ...values,
          status: 'active' as const,
        };
        setAddresses([...addresses, newAddress]);
        message.success('地址创建成功');
      }
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleStatus = (record: CompanyAddress) => {
    setAddresses(addresses.map(a => 
      a.id === record.id ? { ...a, status: a.status === 'active' ? 'inactive' : 'active' } : a
    ));
    message.success(`地址已${record.status === 'active' ? '停用' : '启用'}`);
  };

  const columns = [
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
          <Button type="link" size="small" onClick={() => handleEdit(record)}>编辑</Button>
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
        <h1 className="page-title">公司设置</h1>
      </div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button type="primary" onClick={handleAdd}>新增地址</Button>
        </div>
        <Table columns={columns} dataSource={addresses} rowKey="id" pagination={false} />
      </Card>

      <Modal
        title={editingAddress ? '编辑地址' : '新增地址'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
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

export default CompanySettings;
