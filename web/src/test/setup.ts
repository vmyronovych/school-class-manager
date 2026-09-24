import '@testing-library/jest-dom/vitest';
import '../i18n';

// antd (Grid, Table) читає matchMedia, якого немає в jsdom.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// rc-table міряє скролбар через getComputedStyle(el, '::-webkit-scrollbar') — jsdom не вміє псевдоелементи.
const getComputedStyle = window.getComputedStyle.bind(window);
window.getComputedStyle = (elt: Element) => getComputedStyle(elt);
