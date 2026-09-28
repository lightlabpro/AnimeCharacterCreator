import { useEffect, useState } from 'react';
import { BODY_KINDS } from '../model/types';
import { useStore, type RightPanel } from '../state/store';
import { AppearancePanel } from './AppearancePanel';
import { FaceProfilePanel } from './FaceProfilePanel';
import { HelpModal, ImportReportModal, Toast } from './ImportReport';
import { LibraryPanel } from './LibraryPanel';
import { MenuBar, SHORTCUTS, useShortcuts } from './MenuBar';
import { MixerPanel } from './MixerPanel';
import { ModifyPanel } from './ModifyPanel';
import { PlayBar } from './PlayBar';
import { Toolstrip } from './Toolstrip';
import { Viewport, regionLabel, useHover } from './Viewport';
import { CONTROL_BY_ID } from '../model/controls';

const PANELS: { id: RightPanel; label: string }[] = [
  { id: 'modify', label: 'Modify' },
  { id: 'mixer', label: 'Mixer' },
  { id: 'appearance', label: 'Appearance' },
  { id: 'face', label: 'Face' },
];

export function App() {
  const panel = useStore((s) => s.ui.rightPanel);
  const toast = useStore((s) => s.ui.toast);
  const [help, setHelp] = useState(false);
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
      <aside className="panel left">
        <LibraryPanel />
      </aside>
      <main className="viewport">
        <Viewport />
        <Toolstrip />
      </main>
      <PlayBar />
      <aside className="panel right">
        <div className="tabs big">
          {PANELS.map((p) => <button key={p.id} className={panel === p.id ? 'on' : ''} onClick={() => st().setUI({ rightPanel: p.id })}>{p.label}</button>)}
        </div>
        {panel === 'modify' && <ModifyPanel />}
        {panel === 'mixer' && <MixerPanel />}
        {panel === 'appearance' && <AppearancePanel />}
        {panel === 'face' && <FaceProfilePanel />}
      </aside>
      <StatusBar />
      <ImportReportModal />
      {help && <HelpModal onClose={() => setHelp(false)} shortcuts={SHORTCUTS} />}
      <Toast />
    </div>
  );
}

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
      <span>Body <b>{BODY_KINDS.find((b) => b.id === kind)?.label}</b></span>
      <span>Hover <b>{hover.region ? regionLabel(hover.region) : '—'}</b></span>
      {drag && hover.dragKeys.length > 0 && <span>Drag edits <b>{hover.dragKeys.map((k) => CONTROL_BY_ID[k]?.label ?? k).join(', ')}</b></span>}
      <span>Undo <b>{past}</b> · Redo <b>{future}</b></span>
      <span>Imported packs <b>{packs}</b></span>
      <span style={{ marginLeft: 'auto' }}>{filePath ?? 'Not saved yet'}</span>
    </footer>
  );
}
