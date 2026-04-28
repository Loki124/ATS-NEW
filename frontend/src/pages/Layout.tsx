import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, message } from 'antd';
import type { MenuProps } from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  TeamOutlined,
  UserAddOutlined,
  CalendarOutlined,
  GiftOutlined,
  RiseOutlined,
  BellOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { store } from '../store';
import { logout } from '../store/userSlice';
import './Layout.css';

const { Header, Sider, Content } = Layout;

const LayoutPage: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const userState = store.getState().user as any;

  const menuItems: MenuProps['items'] = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '工作台',
    },
    {
      key: 'demand',
      icon: <FileTextOutlined />,
      label: '需求管理',
      children: [
        { key: '/demands', label: '需求列表' },
        { key: '/positions', label: '职位管理' },
      ],
    },
    {
      key: 'candidate',
      icon: <TeamOutlined />,
      label: '候选人',
      children: [
        { key: '/candidates', label: '候选人管理' },
        { key: '/screenings', label: '简历筛选' },
        { key: '/talent-pool', label: '人才库' },
        { key: '/my-resumes', label: '我找的简历' },
      ],
    },
    {
      key: 'interview',
      icon: <CalendarOutlined />,
      label: '面试管理',
      children: [
        { key: '/interviews', label: '面试安排' },
        { key: '/invitations', label: '邀约中心' },
      ],
    },
    {
      key: 'offer',
      icon: <GiftOutlined />,
      label: 'Offer管理',
      children: [
        { key: '/offers', label: 'Offer列表' },
        { key: '/onboardings', label: '待入职' },
      ],
    },
    {
      key: 'report',
      icon: <RiseOutlined />,
      label: '数据中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      children: [
        { key: '/settings/account', label: '账号设置' },
        { key: '/settings/process', label: '流程管理' },
        { key: '/settings/stage', label: '阶段配置' },
        { key: '/settings/scoring', label: '评分规则' },
        { key: '/settings/dictionary', label: '数据字典' },
        { key: '/settings/company', label: '公司信息' },
      ],
    },
  ];

  const userMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserAddOutlined />,
      label: '个人中心',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: '账号设置',
      onClick: () => navigate('/settings/account'),
    },
    { type: 'divider' },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: () => {
        store.dispatch(logout());
        message.success('已退出登录');
        navigate('/login');
      },
    },
  ];

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    if (typeof key === 'string' && key.startsWith('/')) {
      navigate(key);
    }
  };

  const getSelectedKeys = () => {
    const path = location.pathname;
    const selectedKeys: string[] = [path];
    const openKeys: string[] = [];

    menuItems?.forEach((item: any) => {
      if (item?.children) {
        item.children.forEach((child: any) => {
          if (child?.key === path) {
            openKeys.push(item.key);
          }
        });
      }
    });

    return { selectedKeys, openKeys };
  };

  const { selectedKeys, openKeys } = getSelectedKeys();

  return (
    <Layout className="app-layout">
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        className="app-sider"
        width={240}
      >
        <div className="logo-container">
          <div className="logo">
            <div className="logo-icon">
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
              </svg>
            </div>
            {!collapsed && <span className="logo-text">ATS招聘系统</span>}
          </div>
        </div>

        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={selectedKeys}
          defaultOpenKeys={openKeys}
          items={menuItems}
          onClick={handleMenuClick}
          className="side-menu"
        />
      </Sider>

      <Layout>
        <Header className="app-header">
          <div className="header-left">
            <button
              className="trigger-btn"
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            </button>

            <div className="search-box">
              <SearchOutlined className="search-icon" />
              <input type="text" placeholder="搜索候选人、职位、需求..." />
            </div>
          </div>

          <div className="header-right">
            <Badge count={5} size="small">
              <button className="header-icon-btn" onClick={() => navigate('/notifications')}>
                <BellOutlined />
              </button>
            </Badge>

            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" trigger={['click']}>
              <div className="user-info">
                <Avatar size={36} className="user-avatar">
                  {userState?.realName?.[0] || 'A'}
                </Avatar>
                <div className="user-details">
                  <span className="user-name">{userState?.realName || '管理员'}</span>
                  <span className="user-role">{userState?.role === 'admin' ? '超级管理员' : '用户'}</span>
                </div>
              </div>
            </Dropdown>
          </div>
        </Header>

        <Content className="app-content">
          <div className="content-wrapper">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default LayoutPage;
