import { useTranslation } from 'react-i18next';
import { Button, Card, Col, Descriptions, Empty, Flex, List, Row, Typography } from 'antd';
import { KeyOutlined } from '@ant-design/icons';
import { mockSnapshots, type StudentRow } from './mockData';
import { StatusTag } from './StatusTag';

export function StudentCard({ student }: { student?: StudentRow }) {
  const { t } = useTranslation();

  if (!student) {
    return (
      <Card>
        <Empty description={t('students.card.empty')} />
      </Card>
    );
  }

  const lastLogon = [student.lastLogon, student.lastLogonPc].filter(Boolean).join(', ');
  const folder = student.folderFiles
    ? t('students.card.folderValue', { files: student.folderFiles, size: student.folderSize })
    : student.folderSize;

  return (
    <Card title={student.name} extra={<StatusTag status={student.status} />}>
      <Flex vertical gap={20}>
        <Descriptions
          column={1}
          size="small"
          items={[
            { key: 'login', label: t('students.card.login'), children: <Typography.Text code>{student.login}</Typography.Text> },
            { key: 'class', label: t('students.card.class'), children: student.classDisplay },
            { key: 'lastLogon', label: t('students.card.lastLogon'), children: lastLogon },
            { key: 'folder', label: t('students.card.folder'), children: folder },
            {
              key: 'password',
              label: t('students.card.password'),
              children: student.passwordChangedAt
                ? t('students.card.passwordChanged', { date: student.passwordChangedAt })
                : '—',
            },
          ]}
        />
        <Flex vertical gap={8}>
          <Button type="primary" size="large" icon={<KeyOutlined />} block>
            {t('students.card.resetPassword')}
          </Button>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Button size="large" block>
                {t('students.card.files')}
              </Button>
            </Col>
            <Col span={12}>
              <Button size="large" block>
                {t('students.card.unlock')}
              </Button>
            </Col>
            <Col span={12}>
              <Button size="large" block>
                {t('students.card.move')}
              </Button>
            </Col>
            <Col span={12}>
              <Button size="large" danger block>
                {t('students.card.disable')}
              </Button>
            </Col>
          </Row>
        </Flex>
        <List
          size="small"
          bordered
          header={
            <Flex justify="space-between" align="center">
              <Typography.Text strong>{t('students.card.snapshots')}</Typography.Text>
              <Button type="link" size="small">
                {t('students.card.allSnapshots')}
              </Button>
            </Flex>
          }
          dataSource={mockSnapshots}
          renderItem={(when) => (
            <List.Item
              actions={[
                <Button key="restore" type="link" size="small">
                  {t('students.card.restore')}
                </Button>,
              ]}
            >
              {when}
            </List.Item>
          )}
        />
      </Flex>
    </Card>
  );
}
