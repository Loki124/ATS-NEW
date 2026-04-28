import React from 'react';
import { Table, Card, Tag } from 'antd';

const ResumeList: React.FC = () => {
  const columns = [
    { title: '简历名称', dataIndex: 'name', key: 'name' },
    { title: '候选人', dataIndex: 'candidate', key: 'candidate' },
    { title: '来源', dataIndex: 'source', key: 'source' },
    { title: '上传时间', dataIndex: 'time', key: 'time' },
  ];

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">我找的简历</h1>
      </div>
      <Card>
        <Table columns={columns} dataSource={[]} rowKey="id" locale={{ emptyText: '暂无数据' }} />
      </Card>
    </div>
  );
};

export default ResumeList;
