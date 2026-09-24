import { render, screen, within } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { App } from './App';
import { routes } from './router';

function renderAt(path: string) {
  return render(<App router={createMemoryRouter(routes, { initialEntries: [path] })} />);
}

describe('AppLayout', () => {
  it('shows five navigation items', async () => {
    renderAt('/');

    const menu = await screen.findByRole('menu');
    for (const label of ['Огляд', 'Учні', 'Файли', 'Сервер', 'Налаштування']) {
      expect(within(menu).getByText(label)).toBeInTheDocument();
    }
  });

  it('renders the Students page with mockup data', async () => {
    renderAt('/students');

    expect(await screen.findByText('4a.bondar')).toBeInTheDocument();
    expect(screen.getByText('Заблокований')).toBeInTheDocument();
    expect(screen.getByText('Скинути пароль')).toBeInTheDocument();
    expect(screen.getByText('Вибрано: 1')).toBeInTheDocument();
  });
});
