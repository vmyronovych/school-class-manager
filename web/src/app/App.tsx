import { useState } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import type { RouterProviderProps } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { App as AntApp, ConfigProvider } from 'antd';
import ukUA from 'antd/locale/uk_UA';
import { routes } from './router';
import { theme } from './theme';

export function App({ router }: { router?: RouterProviderProps['router'] }) {
  const [queryClient] = useState(() => new QueryClient());
  const [appRouter] = useState(() => router ?? createBrowserRouter(routes));

  return (
    <ConfigProvider locale={ukUA} theme={theme}>
      <AntApp>
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={appRouter} />
        </QueryClientProvider>
      </AntApp>
    </ConfigProvider>
  );
}
