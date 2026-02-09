import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App.tsx';

// 屏蔽 React DevTools 在控制台的推广提示
const origLog = console.log;
console.log = (...args: unknown[]) => {
  const msg = args[0];
  if (typeof msg === 'string' && msg.includes('Download the React DevTools')) return;
  origLog.apply(console, args);
};

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
