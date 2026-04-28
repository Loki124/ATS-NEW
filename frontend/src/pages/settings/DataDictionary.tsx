import React, { useState } from 'react';
import { Card, Table, Button, Modal, Form, Input, Select, message, Tag, Space } from 'antd';

interface DictionaryItem {
  id: string;
  name: string;
  code: string;
  category: string;
  itemCount: number;
  status: 'active' | 'inactive';
}

const DataDictionary: React.FC = () => {
  const [dictionaries, setDictionaries] = useState<DictionaryItem[]>([
    { id: '1', name: '学历', code: 'EDUCATION', category: '基本信息', itemCount: 8, status: 'active' },
    { id: '2', name: '婚姻状况', code: 'MARITAL', category: '基本信息', itemCount: 4, status: 'active' },
    { id: '3', name: '职位类型', code: 'POSITION_TYPE', category: '职位信息', itemCount: 12, status: 'active' },
    { id: '4', name: '面试类型', code: 'INTERVIEW_TYPE', category: '面试信息', itemCount: 5, status: 'active' },
    { id: '5', name: 'Offer状态', code: 'OFFER_STATUS', category: 'Offer信息', itemCount: 8, status: 'active' },
    { id: '6', name: '淘汰原因', code: 'REJECT_REASON', category: '归档信息', itemCount: 15, status: 'active' },
  ]);

  const [modalVisible, setModalVisible] = useState(false);
  const [editingDictionary, setEditingDictionary] = useState<DictionaryItem | null>(null);
  const [form] = Form.useForm();

  const handleAdd = () => {
    setEditingDictionary(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: DictionaryItem) => {
    setEditingDictionary(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
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
      setModalVisible(false);
    } catch (error) {
      console.error('验证失败:', error);
    }
  };

  const handleToggleStatus = (record: DictionaryItem) => {
    setDictionaries(dictionaries.map(d => 
      d.id === record.id ? { ...d, status: d.status === 'active' ? 'inactive' : 'active' } : d
    ));
    message.success(`字典已${record.status === 'active' ? '停用' : '启用'}`);
  };

  const columns = [
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
        <h1 className="page-title">数据字典</h1>
      </div>
      <Card>
        <div style={{ marginBottom: 16 }}>
          <Button type="primary" onClick={handleAdd}>新增字典</Button>
        </div>
        <Table columns={columns} dataSource={dictionaries} rowKey="id" pagination={false} />
      </Card>

      <Modal
        title={editingDictionary ? '编辑字典' : '新增字典'}
        open={modalVisible}
        onOk={handleSave}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
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
    </div>
  );
};

export default DataDictionary;
