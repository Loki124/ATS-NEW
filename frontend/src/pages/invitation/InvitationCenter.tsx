import React from 'react';
import { Table, Card, Tag } from 'antd';

const InvitationCenter: React.FC = () => {
  const columns = [
    { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
    { title: '应聘职位', dataIndex: 'position', key: 'position' },
    { title: '邀约状态', dataIndex: 'status', key: 'status',
      render: (status: string) => <Tag color="cyan">{status}</Tag>
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">邀约中心</h1>
      </div>
      <Card>
        <Table columns={columns} dataSource={[]} rowKey="id" locale={{ emptyText: '暂无数据' }} />
      </Card>
    </div>
  );
};

export default InvitationCenter;
