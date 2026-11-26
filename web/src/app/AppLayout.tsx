import { useEffect, useState } from 'react';
import { Outlet } from 'react-router';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Card, Flex, Form, Input, Layout, Spin, Typography } from 'antd';
import { BookOutlined, LogoutOutlined } from '@ant-design/icons';
import { ApiFailure, errorCode, request, type Teacher } from '../api/panel';

export function AppLayout() {
  const { t } = useTranslation();
  const cache = useQueryClient();
  const [expired, setExpired] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [form] = Form.useForm<{ login: string; password: string }>();
  const session = useQuery({ queryKey: ['session'], queryFn: () => request<Teacher>('/api/me'), retry: false });
  useEffect(() => {
    const expire = () => {
      setExpired(true);
      cache.removeQueries({ queryKey: ['students'] });
      cache.removeQueries({ queryKey: ['files'] });
    };
    window.addEventListener('scm-session-expired', expire);
    return () => window.removeEventListener('scm-session-expired', expire);
  }, [cache]);

  async function signIn(values: { login: string; password: string }) {
    setBusy(true); setError(undefined);
    try {
      const teacher = await request<Teacher>('/api/auth/login', values);
      form.resetFields(['password']);
      cache.removeQueries({ queryKey: ['files'] });
      cache.setQueryData(['session'], teacher);
      setExpired(false);
    } catch (failure) { setError(errorCode(failure)); }
    finally { setBusy(false); }
  }
  async function signOut() {
    setBusy(true); setError(undefined);
    try {
      await request('/api/auth/logout', {});
      setExpired(true); cache.clear();
    } catch (failure) { setError(errorCode(failure)); }
    finally { setBusy(false); }
  }
  if (session.isPending && !expired) return <Flex justify="center" style={{ padding: 100 }}><Spin size="large" /></Flex>;
  if (!session.data || expired || session.error) {
    const serverError = session.error && !(session.error instanceof ApiFailure && [401, 403].includes(session.error.status));
    return <Flex justify="center" align="center" style={{ minHeight: '100vh', padding: 24 }}>
      <Card style={{ width: 420 }}>
        <BookOutlined style={{ fontSize: 30, color: '#1677ff' }} />
        <Typography.Title level={3}>{t('app.name')}</Typography.Title>
        <Typography.Paragraph type="secondary">{t('panel.signInHint')}</Typography.Paragraph>
        {(error || serverError) && <Alert type="error" showIcon message={t(`panel.errors.${error ?? 'unavailable'}`)} style={{ marginBottom: 16 }} />}
        <Form form={form} layout="vertical" onFinish={(values) => void signIn(values)} disabled={busy}>
          <Form.Item name="login" label={t('panel.login')} rules={[{ required: true, message: t('panel.required') }]}>
            <Input autoComplete="username" autoFocus />
          </Form.Item>
          <Form.Item name="password" label={t('panel.password')} rules={[{ required: true, message: t('panel.required') }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button block type="primary" htmlType="submit" loading={busy}>{t('panel.signIn')}</Button>
        </Form>
      </Card>
    </Flex>;
  }
  return <Layout style={{ minHeight: '100vh' }}>
    <Layout.Header style={{ padding: '0 24px', background: '#001529', height: 'auto', minHeight: 64 }}>
      <Flex justify="space-between" align="center" wrap gap={12}>
        <Typography.Text strong style={{ color: '#fff', fontSize: 18 }}><BookOutlined /> {t('app.name')}</Typography.Text>
        <Flex align="center" gap={16}>
          <Typography.Text style={{ color: '#fff' }}>{session.data.displayName}</Typography.Text>
          <Button icon={<LogoutOutlined />} onClick={() => void signOut()} loading={busy}>{t('panel.signOut')}</Button>
        </Flex>
      </Flex>
    </Layout.Header>
    <Layout.Content style={{ padding: 24, width: '100%', maxWidth: 1200, margin: '0 auto' }}>
      {error && <Alert type="error" message={t(`panel.errors.${error}`)} />}
      <Outlet />
    </Layout.Content>
  </Layout>;
}
