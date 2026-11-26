import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Flex, Form, Input, Modal, Table, Tag, Typography } from 'antd';
import { PlusOutlined, ReloadOutlined, KeyOutlined } from '@ant-design/icons';
import { errorCode, request, type Credentials, type NewPupil, type Pupil } from '../api/panel';

export function Students() {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const pupils = useQuery({ queryKey: ['students'], queryFn: () => request<Pupil[]>('/api/students'), retry: false });
  const [query, setQuery] = useState('');
  const [creating, setCreating] = useState(false);
  const [reset, setReset] = useState<Pupil>();
  const [credentials, setCredentials] = useState<Credentials>();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string>();
  const [form] = Form.useForm<NewPupil>();

  async function mutate(body?: NewPupil) {
    setPending(true); setError(undefined); setCredentials(undefined);
    try {
      const result = body
        ? await request<Credentials>('/api/students', body)
        : await request<Credentials>(`/api/students/${encodeURIComponent(reset!.login)}/reset-password`, {});
      setCreating(false); setReset(undefined); if (body) form.resetFields(); setCredentials(result);
      await pupils.refetch();
    } catch (failure) { setError(errorCode(failure)); }
    finally { setPending(false); }
  }
  const search = query.trim().toLocaleLowerCase('uk');
  const rows = (pupils.data ?? []).filter(p => `${p.login} ${p.displayName}`.toLocaleLowerCase('uk').includes(search));
  return <Flex vertical gap={20}>
    <Flex justify="space-between" align="center" wrap gap={12}>
      <div><Typography.Title level={2} style={{ margin: 0 }}>{t('nav.students')}</Typography.Title>
        <Typography.Text type="secondary">{t('panel.subtitle')}</Typography.Text></div>
      <Flex gap={8}>
        <Button icon={<ReloadOutlined />} loading={pupils.isFetching} onClick={() => void pupils.refetch()}>{t('panel.refresh')}</Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => { setCreating(true); setError(undefined); }}>{t('panel.add')}</Button>
      </Flex>
    </Flex>
    {pupils.isError && <Alert type="error" showIcon message={t(`panel.errors.${errorCode(pupils.error)}`)} />}
    <Input.Search aria-label={t('panel.search')} placeholder={t('panel.search')} allowClear value={query} onChange={e => setQuery(e.target.value)} style={{ maxWidth: 420 }} />
    <Table<Pupil> rowKey="login" dataSource={rows} loading={pupils.isPending} scroll={{ x: 620 }}
      pagination={{ pageSize: 15, hideOnSinglePage: true }} locale={{ emptyText: t('panel.empty') }} columns={[
        { title: t('panel.login'), dataIndex: 'login', render: (value: string) => <Typography.Text code>{value}</Typography.Text> },
        { title: t('panel.name'), dataIndex: 'displayName' },
        { title: t('panel.status'), render: (_, row) => <Tag color={row.enabled ? 'green' : 'default'}>{t(row.enabled ? 'panel.active' : 'panel.disabled')}</Tag> },
        { title: t('panel.actions'), render: (_, row) => <Flex gap={8} wrap>
          <Button onClick={() => void navigate(`/students/${encodeURIComponent(row.login)}/files`)}>{t('files.open')}</Button>
          <Button icon={<KeyOutlined />} onClick={() => { setReset(row); setError(undefined); }}>{t('panel.reset')}</Button>
        </Flex> },
      ]} />
    <Modal title={t('panel.add')} open={creating} destroyOnHidden closable={!pending} maskClosable={!pending}
      onCancel={() => { setCreating(false); setError(undefined); }} onOk={() => form.submit()} confirmLoading={pending}
      okText={t('panel.create')} cancelText={t('panel.cancel')} cancelButtonProps={{ disabled: pending }}>
      {error && <Alert type="error" showIcon message={t(`panel.errors.${error}`)} />}
      <Form form={form} layout="vertical" onFinish={values => void mutate(values)} disabled={pending}>
        <Form.Item name="login" label={t('panel.login')} extra={t('panel.loginHint')}
          rules={[{ required: true, message: t('panel.required') }, { pattern: /^[a-z][a-z0-9.-]{0,63}$/, message: t('panel.loginHint') }]}>
          <Input autoComplete="off" maxLength={64} />
        </Form.Item>
        <Form.Item name="surname" label={t('panel.surname')} rules={[{ required: true, whitespace: true, message: t('panel.required') }]}><Input maxLength={64} /></Form.Item>
        <Form.Item name="givenName" label={t('panel.givenName')} rules={[{ required: true, whitespace: true, message: t('panel.required') }]}><Input maxLength={64} /></Form.Item>
        <Typography.Paragraph type="secondary">{t('panel.createHint')}</Typography.Paragraph>
      </Form>
    </Modal>
    <Modal title={t('panel.reset')} open={!!reset} closable={!pending} maskClosable={!pending}
      onCancel={() => { setReset(undefined); setError(undefined); }} onOk={() => void mutate()} confirmLoading={pending}
      okText={t('panel.reset')} cancelText={t('panel.cancel')} cancelButtonProps={{ disabled: pending }}>
      <Typography.Paragraph>{t('panel.resetHint', { login: reset?.login })}</Typography.Paragraph>
      {error && <Alert type="error" showIcon message={t(`panel.errors.${error}`)} />}
    </Modal>
    <Modal destroyOnHidden title={t('panel.credentials')} open={!!credentials} onCancel={() => setCredentials(undefined)}
      footer={<Button type="primary" onClick={() => setCredentials(undefined)}>{t('panel.saved')}</Button>}>
      <Typography.Paragraph>{t('panel.login')}: <Typography.Text code>{credentials?.login}</Typography.Text></Typography.Paragraph>
      <Typography.Paragraph>{t('panel.password')}: <Typography.Text code copyable={credentials ? { text: credentials.password } : false}>{credentials?.password}</Typography.Text></Typography.Paragraph>
      <Alert type="info" showIcon message={t('panel.secretHint')} />
    </Modal>
  </Flex>;
}
