import { useTranslation } from 'react-i18next';
import { Empty, Typography } from 'antd';

export function StubPage({ titleKey, milestone }: { titleKey: string; milestone: string }) {
  const { t } = useTranslation();
  return (
    <>
      <Typography.Title level={4} style={{ marginTop: 0 }}>
        {t(titleKey)}
      </Typography.Title>
      <Empty description={t('stub.comingIn', { milestone })} />
    </>
  );
}
