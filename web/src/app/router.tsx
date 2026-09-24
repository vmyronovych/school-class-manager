import type { RouteObject } from 'react-router';
import { AppLayout } from './AppLayout';
import { Dashboard } from '../pages/Dashboard';
import { Students } from '../pages/Students';
import { Files } from '../pages/Files';
import { Server } from '../pages/Server';
import { Settings } from '../pages/Settings';

export const routes: RouteObject[] = [
  {
    path: '/',
    element: <AppLayout />,
    children: [
      { index: true, element: <Dashboard /> },
      { path: 'students', element: <Students /> },
      { path: 'files', element: <Files /> },
      { path: 'server', element: <Server /> },
      { path: 'settings', element: <Settings /> },
    ],
  },
];
