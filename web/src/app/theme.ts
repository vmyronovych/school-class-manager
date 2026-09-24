import type { ThemeConfig } from 'antd';

// Стандартні токени antd, як у мокапі (docs/mockups.md).
export const theme: ThemeConfig = {
  token: {
    colorPrimary: '#1677ff',
    borderRadius: 6,
    borderRadiusLG: 8,
  },
  components: {
    Layout: {
      siderBg: '#001529',
      headerBg: '#ffffff',
      headerHeight: 56,
      headerPadding: '0 24px',
      bodyBg: '#f5f5f5',
    },
  },
};
