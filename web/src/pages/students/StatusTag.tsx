import { useTranslation } from 'react-i18next';
import { Tag } from 'antd';
import type { StudentStatus } from './mockData';

const colors: Record<StudentStatus, string> = {
  Active: 'success',
  Locked: 'warning',
  NeverLoggedIn: 'default',
  Disabled: 'error',
};

export function StatusTag({ status }: { status: StudentStatus }) {
  const { t } = useTranslation();
  return <Tag color={colors[status]}>{t(`students.status.${status}`)}</Tag>;
}
