import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { App } from './App';
import { routes } from './router';
import { transferableAbortController } from 'node:util';

const teacher = { login: 'teacher1', displayName: 'Учитель', role: 'Teacher', sid: 'test-sid' };
const pupil = { login: 'student1', displayName: 'Іван Петренко', enabled: true, homeDirectory: null };
let signedIn = true;
let failList = false;
let failFiles = false;
const calls: string[] = [];

beforeEach(() => {
  // React Router uses Node's Request; pair it with a Node AbortSignal, not jsdom's.
  vi.stubGlobal('AbortController', transferableAbortController().constructor);
  signedIn = true; failList = false; failFiles = false; calls.length = 0;
  vi.stubGlobal('fetch', vi.fn(async (path: string, options?: RequestInit) => {
    calls.push(path);
    if (path === '/api/me') return Response.json(signedIn ? teacher : { code: 'credentials' }, { status: signedIn ? 200 : 401 });
    if (path === '/api/auth/csrf') return Response.json({ token: 'test-csrf' });
    if (path === '/api/auth/login') { signedIn = true; return Response.json(teacher); }
    if (path === '/api/auth/logout') { signedIn = false; return new Response(null, { status: 204 }); }
    if (path === '/api/students' && options?.method === 'GET') return Response.json(failList ? { code: 'unavailable' } : [pupil], { status: failList ? 503 : 200 });
    if (path.startsWith('/api/students/student1/files?')) {
      if (failFiles) return Response.json({ code: 'forbidden' }, { status: 403 });
      const nested = new URL(path, 'https://localhost').searchParams.get('path');
      return Response.json(nested ? [{ name: 'Робота #1.txt', directory: false, size: 12, modified: '2026-11-26T06:30:00Z' }]
        : [{ name: 'Урок 1', directory: true, size: null, modified: '2026-11-26T06:30:00Z' }]);
    }
    if (path.startsWith('/api/students/student1/download?')) return new Response('test pupil work');
    if (path.endsWith('/reset-password')) return Response.json({ login: 'student1', password: 'example-new-secret' });
    if (path === '/api/students' && options?.method === 'POST') return Response.json({ login: 'student3', password: 'example-created-secret' });
    throw new Error(`Unexpected endpoint ${path}`);
  }));
});
afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function renderApp() { render(<App router={createMemoryRouter(routes, { initialEntries: ['/students'] })} />); }

describe('Pupil panel', () => {
  it('opens pupil folders, downloads a named file and navigates back', async () => {
    const objectUrl = vi.fn(() => 'blob:test');
    const revoke = vi.fn();
    vi.stubGlobal('URL', class extends URL { static createObjectURL = objectUrl; static revokeObjectURL = revoke; });
    let savedName: string | undefined;
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) { savedName = this.download; });
    renderApp();
    // Wait for query data before expensive accessible-role searches through antd.
    // Otherwise role polling can starve query notifications on Node 20 in CI.
    expect(await screen.findByText(pupil.displayName)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Файли' }));
    expect(await screen.findByText('Файли учня student1')).toBeInTheDocument();
    fireEvent.click(await screen.findByRole('button', { name: /Урок 1/ }));
    expect(await screen.findByText('Робота #1.txt')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Завантажити/ }));
    await waitFor(() => expect(click).toHaveBeenCalledOnce());
    expect(savedName).toBe('Робота #1.txt');
    expect(calls.some(path => path.includes('/download?') && new URL(path, 'https://localhost').searchParams.get('path') === 'Урок 1/Робота #1.txt')).toBe(true);
    fireEvent.click(screen.getByRole('button', { name: /На рівень вище/ }));
    expect(await screen.findByRole('button', { name: /Урок 1/ })).toBeInTheDocument();
    await waitFor(() => expect(revoke).toHaveBeenCalledWith('blob:test'), { timeout: 2000 });
  }, 15000);
  it('shows file access refusal instead of exposing cached file entries', async () => {
    renderApp();
    expect(await screen.findByText(pupil.displayName)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Файли' }));
    expect(await screen.findByRole('button', { name: /Урок 1/ })).toBeInTheDocument();
    failFiles = true;
    fireEvent.click(screen.getByRole('button', { name: /Оновити/ }));
    expect(await screen.findByText('Цей обліковий запис не має права виконувати операцію.')).toBeInTheDocument();
    expect(screen.queryByText('Урок 1')).not.toBeInTheDocument();
  }, 10000);
  it('shows real API pupils and no mock dashboard', async () => {
    renderApp();
    expect(await screen.findByText('Іван Петренко')).toBeInTheDocument();
    expect(screen.queryByText('4a.bondar')).not.toBeInTheDocument();
    expect(screen.queryByText('Огляд')).not.toBeInTheDocument();
  });
  it('requires a teacher login before loading pupils', async () => {
    signedIn = false; renderApp();
    expect(await screen.findByRole('button', { name: 'Увійти' })).toBeInTheDocument();
    expect(calls).not.toContain('/api/students');
    fireEvent.change(screen.getByLabelText('Логін'), { target: { value: 'teacher1' } });
    fireEvent.change(screen.getByLabelText('Пароль'), { target: { value: 'example-only' } });
    fireEvent.click(screen.getByRole('button', { name: 'Увійти' }));
    expect(await screen.findByText('Іван Петренко')).toBeInTheDocument();
  });
  it('confirms reset and clears the displayed secret when closed', async () => {
    renderApp();
    expect(await screen.findByText(pupil.displayName)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /Скинути пароль/ }));
    expect(calls.some(path => path.endsWith('/reset-password'))).toBe(false);
    const buttons = screen.getAllByRole('button', { name: /Скинути пароль/ });
    fireEvent.click(buttons[buttons.length - 1]);
    expect(await screen.findByText('example-new-secret')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Зберіг дані' }));
    await waitFor(() => expect(screen.queryByText('example-new-secret')).not.toBeInTheDocument());
  }, 10000);
  it('shows server failure instead of invented pupils', async () => {
    failList = true; renderApp();
    expect(await screen.findByText('Не вдалося зв’язатися із сервером. Спробуйте ще раз.')).toBeInTheDocument();
    expect(screen.queryByText('student1')).not.toBeInTheDocument();
  });
});
