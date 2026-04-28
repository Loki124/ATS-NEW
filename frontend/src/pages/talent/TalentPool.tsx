import React from 'react';
import { Table, Card, Tag } from 'antd';

const TalentPool: React.FC = () => {
  const columns = [
    { title: '姓名', dataIndex: 'name', key: 'name' },
    { title: '手机号', dataIndex: 'phone', key: 'phone' },
    { title: '最高学历', dataIndex: 'education', key: 'education' },
    { title: '人才库类型', dataIndex: 'type', key: 'type',
      render: (type: string) => <Tag color="orange">{type}</Tag>
    },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">人才库</h1>
      </div>
      <Card>
        <Table columns={columns} dataSource={[]} rowKey="id" locale={{ emptyText: '暂无数据' }} />
      </Card>
    </div>
  );
};

export default TalentPool;
