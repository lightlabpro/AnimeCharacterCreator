import { useEffect, useRef, useState } from 'react';
import { CONTROL_BY_ID } from '../model/controls';
import { BODY_KINDS } from '../model/types';
import { useStore, type RightPanel } from '../state/store';
import { AppearancePanel } from './AppearancePanel';
import { FaceProfilePanel } from './FaceProfilePanel';
import { CATEGORY_ICON, Icon } from './icons';
import { HelpModal, ImportReportModal, Toast } from './ImportReport';
import { LIB_CATEGORIES, LibraryPanel, isCategoryDisabled } from './LibraryPanel';
import { MenuBar, SHORTCUTS, useShortcuts } from './MenuBar';
import { MixerPanel } from './MixerPanel';
import { ModifyPanel } from './ModifyPanel';
import { PlayBar } from './PlayBar';
import { Toolstrip } from './Toolstrip';
import { Viewport, regionLabel, useHover } from './Viewport';

const PANELS: { id: RightPanel; label: string; icon: string }[] = [
  { id: 'modify', label: 'Modify', icon: 'modify' },
  { id: 'mixer', label: 'Face mixer', icon: 'mixer' },
  { id: 'appearance', label: 'Appearance layers', icon: 'appearance' },
  { id: 'face', label: 'Face profile', icon: 'face' },
];

function usePersistedWidth(key: string, initial: number, min: number, max: number) {
  const [w, setW] = useState(() => {
    const saved = Number(localStorage.getItem(key));
    return saved >= min && saved <= max ? saved : initial;
  });
  useEffect(() => {
    localStorage.setItem(key, String(w));
  }, [key, w]);
  return [w, (v: number) => setW(Math.round(Math.min(max, Math.max(min, v))))] as const;
}

function Splitter({ onDrag, side }: { onDrag: (dx: number) => void; side: 'left' | 'right' }) {
  const [drag, setDrag] = useState(false);
  const last = useRef(0);
  return (
    <div
      className={`splitter${drag ? ' drag' : ''}`}
      onPointerDown={(e) => {
        (e.target as Element).setPointerCapture(e.pointerId);
        last.current = e.clientX;
        setDrag(true);
      }}
      onPointerMove={(e) => {
        if (!drag) return;
        const dx = e.clientX - last.current;
        last.current = e.clientX;
        onDrag(side === 'left' ? dx : -dx);
      }}
      onPointerUp={() => setDrag(false)}
      onPointerCancel={() => setDrag(false)}
    />
  );
}

export function App() {
  const panel = useStore((s) => s.ui.rightPanel);
  const cat = useStore((s) => s.ui.libraryCategory);
  const kind = useStore((s) => s.identity.bodyKind);
  const toast = useStore((s) => s.ui.toast);
  const [help, setHelp] = useState(false);
  const [libOpen, setLibOpen] = useState(true);
  const [inspOpen, setInspOpen] = useState(true);
  const [libW, setLibW] = usePersistedWidth('creator.libWidth', 276, 220, 520);
  const [inspW, setInspW] = usePersistedWidth('creator.inspWidth', 344, 300, 620);
  const st = useStore.getState;
  useShortcuts();

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => {
      if (useStore.getState().ui.toast?.nonce === toast.nonce) st().setUI({ toast: null });
    }, 4200);
    return () => clearTimeout(t);
  }, [toast]);

  return (
    <div className="app">
      <MenuBar onHelp={() => setHelp(true)} />
      <div className="workspace">
        <nav className="rail left" aria-label="Library categories">
          {LIB_CATEGORIES.map((c, i) => (
            <span key={c} style={{ display: 'contents' }}>
              {i === LIB_CATEGORIES.length - 1 && <span className="sep" />}
              <button
                className={`rail-btn${cat === c && libOpen ? ' on' : ''}`}
                title={c}
                disabled={isCategoryDisabled(c, kind)}
                onClick={() => {
                  if (cat === c) setLibOpen(!libOpen);
                  else {
                    st().setUI({ libraryCategory: c });
                    setLibOpen(true);
                  }
                }}
              >
                <Icon name={CATEGORY_ICON[c]} size={18} />
              </button>
            </span>
          ))}
          <span className="grow" />
          <button className="rail-btn" title={libOpen ? 'Hide library' : 'Show library'} onClick={() => setLibOpen(!libOpen)}>
            <Icon name="sidebar" size={18} />
          </button>
        </nav>
        {libOpen && (
          <>
            <aside className="panel" style={{ width: libW }}>
              <LibraryPanel />
            </aside>
            <Splitter side="left" onDrag={(dx) => setLibW(libW + dx)} />
          </>
        )}
        <div className="center">
          <main className="viewport">
            <Viewport />
            <Toolstrip />
          </main>
          <PlayBar />
        </div>
        {inspOpen && (
          <>
            <Splitter side="right" onDrag={(dx) => setInspW(inspW + dx)} />
            <aside className="panel" style={{ width: inspW }}>
              <div className="panel-head">
                <span className="title">{PANELS.find((p) => p.id === panel)?.label}</span>
              </div>
              {panel === 'modify' && <ModifyPanel />}
              {panel === 'mixer' && <MixerPanel />}
              {panel === 'appearance' && <AppearancePanel />}
              {panel === 'face' && <FaceProfilePanel />}
            </aside>
          </>
        )}
        <nav className="rail right" aria-label="Inspector panels">
          {PANELS.map((p) => (
            <button
              key={p.id}
              className={`rail-btn${panel === p.id && inspOpen ? ' on' : ''}`}
              title={p.label}
              onClick={() => {
                if (panel === p.id) setInspOpen(!inspOpen);
                else {
                  st().setUI({ rightPanel: p.id });
                  setInspOpen(true);
                }
              }}
            >
              <Icon name={p.icon} size={18} />
            </button>
          ))}
          <span className="grow" />
          <button className="rail-btn" title="Keyboard and mouse" onClick={() => setHelp(true)}>
            <Icon name="keyboard" size={18} />
          </button>
          <button className="rail-btn" title={inspOpen ? 'Hide inspector' : 'Show inspector'} onClick={() => setInspOpen(!inspOpen)}>
            <Icon name="sidebarRight" size={18} />
          </button>
        </nav>
      </div>
      <StatusBar />
      <ImportReportModal />
      {help && <HelpModal onClose={() => setHelp(false)} shortcuts={SHORTCUTS} />}
      <Toast />
    </div>
  );
}

const KIND_ICON: Record<string, string> = { adult: 'actor', child: 'child', robot: 'robot', beast: 'dragon' };

function StatusBar() {
  const hover = useHover();
  const kind = useStore((s) => s.identity.bodyKind);
  const past = useStore((s) => s.past.length);
  const future = useStore((s) => s.future.length);
  const packs = useStore((s) => s.packs.length);
  const filePath = useStore((s) => s.filePath);
  const drag = useStore((s) => s.ui.shapeDrag);
  return (
    <footer className="statusbar">
      <span className="si"><Icon name={KIND_ICON[kind]} size={13} /><b>{BODY_KINDS.find((b) => b.id === kind)?.label}</b></span>
      <span className="si"><Icon name="drag" size={13} />{hover.region ? <b>{regionLabel(hover.region)}</b> : 'No region'}</span>
      {drag && hover.dragKeys.length > 0 && <span className="si">Drag edits <b>{hover.dragKeys.map((k) => CONTROL_BY_ID[k]?.label ?? k).join(', ')}</b></span>}
      <span className="si"><Icon name="undo" size={13} /><b className="num">{past}</b><Icon name="redo" size={13} /><b className="num">{future}</b></span>
      <span className="si"><Icon name="folder" size={13} /><b className="num">{packs}</b> imported</span>
      <span className="si push"><Icon name="file" size={13} />{filePath ?? 'Not saved yet'}</span>
    </footer>
  );
}
