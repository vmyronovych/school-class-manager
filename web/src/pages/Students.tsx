import { useMemo, useState } from 'react';
import type { Key } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, Flex, Input, Radio, Table, Typography } from 'antd';
import type { TableColumnsType } from 'antd';
import { IdcardOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';
import { mockClasses, mockStudents, mockSummary, type StudentRow, type StudentStatus } from './students/mockData';
import { StatusTag } from './students/StatusTag';
import { StudentCard } from './students/StudentCard';

const ALL = 'all';
const TEACHERS = 'teachers';
const statuses: StudentStatus[] = ['Active', 'Locked', 'NeverLoggedIn', 'Disabled'];

export function Students() {
  const { t } = useTranslation();
  const [classFilter, setClassFilter] = useState<string>(ALL);
  const [query, setQuery] = useState('');
  const [selectedKeys, setSelectedKeys] = useState<Key[]>(['ivanenko.petro.2016']);
  const [activeLogin, setActiveLogin] = useState<string | undefined>('ivanenko.petro.2016');

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return mockStudents.filter(
      (s) =>
        (classFilter === ALL || s.classCode === classFilter) &&
        (q === '' || s.name.toLowerCase().includes(q) || s.login.includes(q)),
    );
  }, [classFilter, query]);

  // Вчителів у статичних даних немає — вкладка порожня до сесії 3.
  const visible = classFilter === TEACHERS ? [] : rows;

  const columns: TableColumnsType<StudentRow> = [
    {
      title: t('students.columns.login'),
      dataIndex: 'login',
      width: 160,
      sorter: (a, b) => a.login.localeCompare(b.login),
      render: (login: string) => <Typography.Text code>{login}</Typography.Text>,
    },
    {
      title: t('students.columns.name'),
      dataIndex: 'name',
      sorter: (a, b) => a.name.localeCompare(b.name, 'uk'),
      render: (name: string, row) => (
        <Typography.Link onClick={() => setActiveLogin(row.login)}>{name}</Typography.Link>
      ),
    },
    { title: t('students.columns.class'), dataIndex: 'classDisplay', width: 70 },
    {
      title: t('students.columns.status'),
      dataIndex: 'status',
      width: 140,
      filters: statuses.map((s) => ({ text: t(`students.status.${s}`), value: s })),
      onFilter: (value, row) => row.status === value,
      render: (status: StudentStatus) => <StatusTag status={status} />,
    },
    { title: t('students.columns.lastLogon'), dataIndex: 'lastLogon', width: 150 },
    { title: t('students.columns.folder'), dataIndex: 'folderSize', width: 80, align: 'right' },
  ];

  return (
    <Flex vertical gap={16}>
      <Flex justify="space-between" align="flex-start">
        <div>
          <Typography.Title level={4} style={{ margin: 0 }}>
            {t('nav.students')}
          </Typography.Title>
          <Typography.Text type="secondary">{t('students.summary', mockSummary)}</Typography.Text>
        </div>
        <Flex gap={8}>
          <Button size="large" icon={<UploadOutlined />}>
            {t('students.importCsv')}
          </Button>
          <Button size="large" icon={<IdcardOutlined />}>
            {t('students.loginCards')}
          </Button>
          <Button size="large" type="primary" icon={<PlusOutlined />}>
            {t('students.addStudent')}
          </Button>
        </Flex>
      </Flex>

      <Flex align="center" gap={16}>
        <Radio.Group value={classFilter} onChange={(e) => setClassFilter(e.target.value as string)}>
          <Radio.Button value={ALL}>{t('students.filterAll')}</Radio.Button>
          {mockClasses.map((c) => (
            <Radio.Button key={c.code} value={c.code}>
              {c.display}
            </Radio.Button>
          ))}
          <Radio.Button value={TEACHERS}>{t('students.filterTeachers')}</Radio.Button>
        </Radio.Group>
        <Input.Search
          allowClear
          placeholder={t('students.searchPlaceholder')}
          style={{ maxWidth: 360 }}
          onSearch={setQuery}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div style={{ flex: 1 }} />
        <Typography.Text type="secondary">{t('students.selected', { count: selectedKeys.length })}</Typography.Text>
      </Flex>

      <Flex gap={16} align="flex-start">
        <div style={{ flex: 1, minWidth: 0 }}>
          <Table<StudentRow>
            rowKey="login"
            size="middle"
            columns={columns}
            dataSource={visible}
            rowSelection={{ selectedRowKeys: selectedKeys, onChange: setSelectedKeys }}
            pagination={{
              pageSize: 10,
              showTotal: () => t('students.total', { total: mockSummary.accounts }),
            }}
          />
        </div>
        <div style={{ width: 340, flexShrink: 0 }}>
          <StudentCard student={mockStudents.find((s) => s.login === activeLogin)} />
        </div>
      </Flex>
    </Flex>
  );
}
