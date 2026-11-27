import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Flex, Form, Input, Modal, Popconfirm, Table, Typography } from 'antd';
import type { components } from '../api/client';
import { errorCode, request, type Teacher } from '../api/panel';

type Device = components['schemas']['DeviceView'];

export function Devices() {
  const { t } = useTranslation();
  const session = useQueryClient().getQueryData<Teacher>(['session']);
  const admin = session?.role === 'Admin';
  const devices = useQuery({ queryKey: ['devices'], queryFn: () => request<Device[]>('/api/devices'), retry: false });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [issued, setIssued] = useState<{ name: string; key: string }>();
  async function register(name: string, replace: boolean) {
    setBusy(true); setError(undefined);
    try {
      const { key } = await request<{ key: string }>('/api/devices', { computerName: name, replace });
      setIssued({ name, key });
      await devices.refetch();
    } catch (failure) { setError(errorCode(failure)); }
    finally { setBusy(false); }
  }

  return <Flex vertical gap={16}>
    <Flex justify="space-between" align="center">
      <Typography.Title level={2}>{t('devices.title')}</Typography.Title>
      <Button onClick={() => void devices.refetch()} loading={devices.isFetching}>{t('panel.refresh')}</Button>
    </Flex>
    {admin && <Form layout="inline" onFinish={({ name }) => void register(name.trim(), false)}>
      <Form.Item name="name" label={t('devices.pc')} rules={[{ required: true }, { pattern: /^[a-z0-9](?:[a-z0-9-]{0,13}[a-z0-9])?$/i, message: t('devices.nameHint') }]}>
        <Input maxLength={15} />
      </Form.Item>
      <Button type="primary" loading={busy} htmlType="submit">{t('devices.add')}</Button>
    </Form>}
    {(devices.isError || error) && <Alert type="error" message={t(`panel.errors.${error ?? errorCode(devices.error)}`)} />}
    <Table<Device> rowKey="computerName" dataSource={devices.isError ? [] : devices.data} loading={devices.isPending} scroll={{ x: 850 }}
      locale={{ emptyText: t('devices.empty') }} columns={[
        { title: t('devices.pc'), dataIndex: 'computerName' },
        { title: t('devices.lastSeen'), render: (_, d) => d.receivedAt ? new Date(d.receivedAt).toLocaleString('uk-UA') : t('devices.waiting') },
        { title: t('devices.domain'), render: (_, d) => d.status?.domain ?? '—' },
        { title: t('devices.version'), render: (_, d) => d.status?.agentVersion ?? '—' },
        { title: 'Windows', render: (_, d) => d.status ? `${d.status.windowsEdition} (${d.status.windowsBuild})` : '—' },
        { title: t('devices.free'), render: (_, d) => d.status?.systemDriveFreeGiB ?? '—' },
        { title: t('devices.profiles'), render: (_, d) => d.status?.nonSystemProfileCount ?? '—' },
        { title: 'Shared PC', render: (_, d) => d.status?.sharedPcEnabled == null ? '—' : t(d.status.sharedPcEnabled ? 'devices.on' : 'devices.off') },
        ...(admin ? [{ title: t('panel.actions'), render: (_: unknown, d: Device) =>
          d.managed ? t('devices.managed') : <Popconfirm title={t('devices.confirmRotate')} onConfirm={() => void register(d.computerName!, true)}>
            <Button disabled={busy}>{t('devices.rotate')}</Button>
          </Popconfirm> }] : []),
      ]} />
    <Modal open={!!issued} title={t('devices.key', { name: issued?.name })} onCancel={() => setIssued(undefined)} footer={null}>
      <Typography.Paragraph>{t('devices.copyHint')}</Typography.Paragraph>
      {issued && <Typography.Paragraph code copyable>{issued.key}</Typography.Paragraph>}
    </Modal>
  </Flex>;
}
