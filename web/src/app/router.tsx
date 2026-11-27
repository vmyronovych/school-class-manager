import { Devices } from '../pages/Devices';
import { Navigate, type RouteObject } from 'react-router';
import { AppLayout } from './AppLayout';
import { Students } from '../pages/Students';
import { StudentFiles } from '../pages/StudentFiles';

export const routes: RouteObject[] = [{ path: '/', element: <AppLayout />, children: [
  { index: true, element: <Navigate to="/students" replace /> },
  { path: 'devices', element: <Devices /> },
  { path: 'students', element: <Students /> },
  { path: 'students/:login/files', element: <StudentFiles /> },
  { path: '*', element: <Navigate to="/students" replace /> },
]}];
