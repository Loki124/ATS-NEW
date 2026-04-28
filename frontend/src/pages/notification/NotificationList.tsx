import React from 'react';
import { Table, Card, Tag } from 'antd';

const NotificationList: React.FC = () => {
  const columns = [
    { title: '标题', dataIndex: 'title', key: 'title' },
    { title: '类型', dataIndex: 'type', key: 'type',
      render: (type: string) => <Tag color="blue">{type}</Tag>
    },
    { title: '时间', dataIndex: 'time', key: 'time' },
    { title: '状态', dataIndex: 'status', key: 'status',
      render: (status: string) => (
        <Tag color={status === '未读' ? 'red' : 'green'}>{status}</Tag>
      )
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">消息通知</h1>
      </div>
      <Card>
        <Table columns={columns} dataSource={[]} rowKey="id" locale={{ emptyText: '暂无数据' }} />
      </Card>
    </div>
  );
};

export default NotificationList;
