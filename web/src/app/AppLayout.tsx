import { useMemo } from 'react';
import { Link, Outlet, useLocation } from 'react-router';
import { useTranslation } from 'react-i18next';
import { Avatar, Badge, Breadcrumb, Button, Flex, Layout, Menu, Typography, theme } from 'antd';
import {
  AppstoreOutlined,
  BellOutlined,
  BookOutlined,
  DatabaseOutlined,
  FolderOutlined,
  SettingOutlined,
  TeamOutlined,
} from '@ant-design/icons';

const { Sider, Header, Content } = Layout;

const navItems = [
  { key: '/', icon: <AppstoreOutlined />, label: 'nav.dashboard' },
  { key: '/students', icon: <TeamOutlined />, label: 'nav.students' },
  { key: '/files', icon: <FolderOutlined />, label: 'nav.files' },
  { key: '/server', icon: <DatabaseOutlined />, label: 'nav.server' },
  { key: '/settings', icon: <SettingOutlined />, label: 'nav.settings' },
] as const;

// Статичні дані мокапу; з M4 — з /api/server/status і /api/me.
const mock = { host: 'dc1', uptimeDays: 12, user: 'viktor.admin', initials: 'VA' };

export function AppLayout() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { token } = theme.useToken();

  const current = useMemo(
    () => navItems.find((i) => i.key !== '/' && pathname.startsWith(i.key)) ?? navItems[0],
    [pathname],
  );

  const breadcrumb = [{ title: t(current.label) }];
  if (current.key === '/students') breadcrumb.push({ title: t('students.allClasses') });

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220} theme="dark" breakpoint="lg" collapsedWidth={0}>
        <Flex vertical style={{ height: '100%' }}>
          <Flex align="center" gap={10} style={{ height: 64, padding: '0 20px' }}>
            <BookOutlined style={{ fontSize: 24, color: token.colorPrimary }} />
            <Flex vertical>
              <Typography.Text strong style={{ color: '#fff', fontSize: 15, lineHeight: 1.2 }}>
                {t('app.name')}
              </Typography.Text>
              <Typography.Text style={{ color: '#a6adb4', fontSize: 11, lineHeight: 1.2 }}>
                {t('app.server')}
              </Typography.Text>
            </Flex>
          </Flex>
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[current.key]}
            items={navItems.map((i) => ({
              key: i.key,
              icon: i.icon,
              label: <Link to={i.key}>{t(i.label)}</Link>,
            }))}
          />
          <div style={{ flex: 1 }} />
          <div style={{ padding: '16px 20px', borderTop: '1px solid rgba(255,255,255,0.1)' }}>
            <Badge
              status="success"
              text={
                <Typography.Text style={{ color: '#a6adb4', fontSize: 13 }}>
                  {t('app.serverOnline', { host: mock.host, count: mock.uptimeDays })}
                </Typography.Text>
              }
            />
          </div>
        </Flex>
      </Sider>
      <Layout>
        <Header style={{ borderBottom: `1px solid ${token.colorSplit}` }}>
          <Flex align="center" justify="space-between" style={{ height: '100%' }}>
            <Breadcrumb items={breadcrumb} />
            <Flex align="center" gap={12}>
              <Button type="text" icon={<BellOutlined />} aria-label={t('app.notifications')} />
              <Flex align="center" gap={8}>
                <Avatar style={{ backgroundColor: token.colorPrimary }}>{mock.initials}</Avatar>
                <Typography.Text>{mock.user}</Typography.Text>
              </Flex>
            </Flex>
          </Flex>
        </Header>
        <Content style={{ padding: '20px 24px 24px' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}
