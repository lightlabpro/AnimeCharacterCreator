import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './ui/App';
import '@fontsource-variable/inter';
import './ui/styles.css';
import { useStore } from './state/store';
import { captureViews, type CaptureOptions } from './viewport/cleanCapture';

if (import.meta.env.DEV) (window as unknown as { creatorStore: typeof useStore }).creatorStore = useStore;

/** Test and validation hook: add ?capture to the URL (always on in dev). Headless scripts call window.creator.captureViews(). */
if (import.meta.env.DEV || new URLSearchParams(window.location.search).has('capture')) {
  (window as unknown as { creator: unknown }).creator = {
    store: useStore,
    captureViews: (opts?: CaptureOptions) => {
      const s = useStore.getState();
      return captureViews(s.identity, new Map(s.packs.map((p) => [p.id, p])), { overrides: s.renderOverrides, ...opts });
    },
  };
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
