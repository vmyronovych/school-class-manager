import { useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Alert, Button, Flex, Table, Typography } from 'antd';
import { DownloadOutlined, FolderOutlined, ArrowUpOutlined, ReloadOutlined } from '@ant-design/icons';
import { request, downloadPupilFile, errorCode, type PupilFile } from '../api/panel';

export function StudentFiles() {
  const { login = '' } = useParams();
  const [search, setSearch] = useSearchParams();
  const path = search.get('path') ?? '';
  const { t } = useTranslation();
  const [downloading, setDownloading] = useState<string>();
  const [error, setError] = useState<string>();
  const files = useQuery({ queryKey: ['files', login, path], retry: false,
    queryFn: () => request<PupilFile[]>(`/api/students/${encodeURIComponent(login)}/files?${new URLSearchParams({ path })}`) });
  function navigate(next: string) { setError(undefined); setSearch(next ? { path: next } : {}); }
  async function download(entry: PupilFile) {
    setDownloading(entry.name); setError(undefined);
    try {
      const blob = await downloadPupilFile(login, path ? `${path}/${entry.name}` : entry.name);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url; anchor.download = entry.name; document.body.append(anchor); anchor.click(); anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (failure) { setError(errorCode(failure)); }
    finally { setDownloading(undefined); }
  }
  return <Flex vertical gap={20}>
    <Link to="/students">← {t('files.back')}</Link>
    <Flex justify="space-between" align="center" gap={12} wrap>
      <div><Typography.Title level={2} style={{ margin: 0 }}>{t('files.title', { login })}</Typography.Title>
        <Typography.Text type="secondary">{t('files.hint')}</Typography.Text></div>
      <Button icon={<ReloadOutlined />} loading={files.isFetching} onClick={() => void files.refetch()}>{t('panel.refresh')}</Button>
    </Flex>
    <Flex gap={12} align="center">
      <Button icon={<ArrowUpOutlined />} disabled={!path} onClick={() => navigate(path.split('/').slice(0, -1).join('/'))}>{t('files.up')}</Button>
      <Typography.Text style={{ overflowWrap: 'anywhere' }}>H:/{path}</Typography.Text>
    </Flex>
    {(files.isError || error) && <Alert type="error" showIcon message={t(`panel.errors.${error ?? errorCode(files.error)}`)} />}
    <Table<PupilFile> rowKey="name" dataSource={files.isError ? [] : files.data ?? []} loading={files.isPending} scroll={{ x: 600 }}
      pagination={{ pageSize: 20, hideOnSinglePage: true }} locale={{ emptyText: t('files.empty') }} columns={[
        { title: t('files.name'), dataIndex: 'name', render: (_, entry) => entry.directory
          ? <Button type="link" icon={<FolderOutlined />} onClick={() => navigate(path ? `${path}/${entry.name}` : entry.name)}>{entry.name}</Button>
          : <Typography.Text>{entry.name}</Typography.Text> },
        { title: t('files.size'), render: (_, entry) => entry.directory ? '—' : `${(entry.size ?? 0).toLocaleString('uk-UA')} ${t('files.bytes')}` },
        { title: t('files.modified'), render: (_, entry) => new Date(entry.modified).toLocaleString('uk-UA') },
        { title: t('panel.actions'), render: (_, entry) => !entry.directory && <Button icon={<DownloadOutlined />} loading={downloading === entry.name}
          disabled={!!downloading} onClick={() => void download(entry)}>{t('files.download')}</Button> },
      ]} />
  </Flex>;
}
