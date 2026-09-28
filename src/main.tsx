import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './ui/App';
import './ui/styles.css';
import { useStore } from './state/store';

if (import.meta.env.DEV) (window as unknown as { creatorStore: typeof useStore }).creatorStore = useStore;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
