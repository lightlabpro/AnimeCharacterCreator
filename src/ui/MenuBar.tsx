import { useEffect, useRef, useState } from 'react';
import { chooseAndScanLibrary, isDesktop } from '../library/platform';
import { BODY_KINDS } from '../model/types';
import { useStore } from '../state/store';
import { Icon } from './icons';
import { getEngine } from './Viewport';

interface Item {
  label: string;
  icon?: string;
  checked?: boolean;
  kbd?: string;
  run?: () => void;
  disabled?: boolean;
  sep?: boolean;
}

export async function importLibrary() {
  const st = useStore.getState;
  try {
    const scan = await chooseAndScanLibrary();
    if (scan) st().importScan(scan);
  } catch (e) {
    st().toast(`Import failed: ${(e as Error).message}`);
  }
}

export function takeScreenshot() {
  const url = getEngine()?.screenshot();
  if (!url) return;
  const a = document.createElement('a');
  a.href = url;
  a.download = `${useStore.getState().identity.name.replace(/[^\w\- ]+/g, '').trim() || 'character'}.png`;
  a.click();
}

export function saveView() {
  const st = useStore.getState;
  const v = getEngine()?.currentView();
  if (!v) return;
  const name = `View ${st().ui.savedViews.length + 1}`;
  st().setUI({ savedViews: [...st().ui.savedViews, { name, ...v }] });
  st().toast(`Saved the camera as "${name}". Find it under View.`);
}

export const SHORTCUTS: [string, string][] = [
  ['Ctrl+N', 'New character'],
  ['Ctrl+O', 'Open character'],
  ['Ctrl+S', 'Save character'],
  ['Ctrl+I', 'Import library'],
  ['Ctrl+Z', 'Undo'],
  ['Ctrl+Y or Ctrl+Shift+Z', 'Redo'],
  ['1 / 2 / 3 / 4 / 0', 'Front, three-quarter, side, face, frame all'],
  ['T', 'Turntable on or off'],
  ['D', 'Drag body regions on or off'],
  ['W / E / R', 'Gizmo move, rotate, scale'],
  ['B', 'Blink'],
  ['Esc', 'Deselect and close menus'],
  ['Double-click a slider', 'Reset it to zero'],
  ['Drag a body region', 'Edit its sliders. Front and side views drive different axes.'],
];

export function useShortcuts() {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      const typing = !!t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable);
      const st = useStore.getState();
      const mod = e.ctrlKey || e.metaKey;
      const k = e.key.toLowerCase();
      if (mod) {
        if (typing && (k === 'z' || k === 'y')) return;
        const act: Record<string, () => void> = {
          z: () => (e.shiftKey ? st.redo() : st.undo()),
          y: () => st.redo(),
          s: () => void st.saveCharacter(),
          o: () => void st.openCharacter(),
          n: () => st.newCharacter(st.identity.bodyKind),
          i: () => void importLibrary(),
        };
        if (act[k]) {
          e.preventDefault();
          act[k]();
        }
        return;
      }
      if (typing || e.altKey) return;
      const cams: Record<string, string> = { '1': 'front', '2': 'threeQuarter', '3': 'side', '4': 'face', '0': 'frame' };
      if (cams[k]) st.requestCamera(cams[k]);
      else if (k === 't') st.setUI({ turntable: !st.ui.turntable });
      else if (k === 'd') st.setUI({ shapeDrag: !st.ui.shapeDrag });
      else if (k === 'w') st.setUI({ gizmoMode: 'translate' });
      else if (k === 'e') st.setUI({ gizmoMode: 'rotate' });
      else if (k === 'r') st.setUI({ gizmoMode: 'scale' });
      else if (k === 'b') st.playClip('blink', false);
      else if (k === 'escape') st.setUI({ selectedEquip: null, highlight: null });
      else return;
      e.preventDefault();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
}

export function MenuBar({ onHelp }: { onHelp: () => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const past = useStore((s) => s.past.length);
  const future = useStore((s) => s.future.length);
  const name = useStore((s) => s.identity.name);
  const filePath = useStore((s) => s.filePath);
  const ui = useStore((s) => s.ui);
  const report = useStore((s) => s.report);
  const saved = useStore((s) => s.savedIdentity === s.identity);
  const st = useStore.getState;

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(null);
    };
    const esc = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(null);
    window.addEventListener('mousedown', close);
    window.addEventListener('keydown', esc);
    return () => {
      window.removeEventListener('mousedown', close);
      window.removeEventListener('keydown', esc);
    };
  }, []);

  const KIND_ICON: Record<string, string> = { adult: 'actor', child: 'child', robot: 'robot', beast: 'dragon' };
  const menus: Record<string, Item[]> = {
    File: [
      ...BODY_KINDS.map((b, i) => ({ label: `New ${b.label.toLowerCase()}`, icon: KIND_ICON[b.id], kbd: i === 0 ? 'Ctrl+N' : undefined, run: () => st().newCharacter(b.id) })),
      { label: '', sep: true },
      { label: 'Open character…', icon: 'folder', kbd: 'Ctrl+O', run: () => void st().openCharacter() },
      { label: 'Save character…', icon: 'save', kbd: 'Ctrl+S', run: () => void st().saveCharacter() },
      { label: '', sep: true },
      { label: 'Import library…', icon: 'import', kbd: 'Ctrl+I', run: () => void importLibrary() },
      { label: 'Last import report', icon: 'file', disabled: !report, run: () => st().setUI({ showImportReport: true }) },
      { label: '', sep: true },
      { label: 'Save screenshot', icon: 'camera', run: takeScreenshot },
    ],
    Edit: [
      { label: 'Undo', icon: 'undo', kbd: 'Ctrl+Z', disabled: !past, run: () => st().undo() },
      { label: 'Redo', icon: 'redo', kbd: 'Ctrl+Y', disabled: !future, run: () => st().redo() },
      { label: '', sep: true },
      { label: 'Randomize identity', icon: 'dice', run: () => st().randomize() },
      { label: 'Reset identity', icon: 'reset', run: () => st().resetIdentity() },
      { label: 'Reset performance', icon: 'expression', run: () => st().resetPerformance() },
      { label: '', sep: true },
      { label: 'Deselect', icon: 'close', kbd: 'Esc', run: () => st().setUI({ selectedEquip: null }) },
    ],
    View: [
      { label: 'Front', icon: 'camFront', kbd: '1', run: () => st().requestCamera('front') },
      { label: 'Three-quarter', icon: 'camQuarter', kbd: '2', run: () => st().requestCamera('threeQuarter') },
      { label: 'Side', icon: 'camSide', kbd: '3', run: () => st().requestCamera('side') },
      { label: 'Back', icon: 'camBack', run: () => st().requestCamera('back') },
      { label: 'Face close-up', icon: 'camFace', kbd: '4', run: () => st().requestCamera('face') },
      { label: 'Upper body', icon: 'camUpper', run: () => st().requestCamera('upper') },
      { label: 'Frame all', icon: 'frame', kbd: '0', run: () => st().requestCamera('frame') },
      { label: '', sep: true },
      { label: 'Turntable', icon: 'turntable', checked: ui.turntable, kbd: 'T', run: () => st().setUI({ turntable: !ui.turntable }) },
      { label: 'Drag body regions', icon: 'drag', checked: ui.shapeDrag, kbd: 'D', run: () => st().setUI({ shapeDrag: !ui.shapeDrag }) },
      { label: 'Save current view', icon: 'bookmark', run: saveView },
      ...ui.savedViews.map((v) => ({ label: `Go to ${v.name}`, icon: 'bookmark', run: () => st().requestCamera(v.name) })),
      ...(ui.savedViews.length ? [{ label: 'Forget saved views', icon: 'trash', run: () => st().setUI({ savedViews: [] }) }] : []),
      { label: '', sep: true },
      { label: 'Modify', icon: 'modify', run: () => st().setUI({ rightPanel: 'modify' }) },
      { label: 'Face mixer', icon: 'mixer', run: () => st().setUI({ rightPanel: 'mixer' }) },
      { label: 'Appearance layers', icon: 'appearance', run: () => st().setUI({ rightPanel: 'appearance' }) },
      { label: 'Face profile', icon: 'face', run: () => st().setUI({ rightPanel: 'face' }) },
    ],
    Help: [
      { label: 'Keyboard and mouse', icon: 'keyboard', run: onHelp },
      { label: isDesktop ? 'Running as the desktop app' : 'Running in a browser. Import uses a folder picker.', icon: 'info', disabled: true },
    ],
  };

  return (
    <div className="menubar" ref={ref}>
      <div className="left">
        <div className="brand"><span className="logo"><Icon name="sparkle" size={13} stroke={2.2} /></span>Character Creator</div>
        {Object.entries(menus).map(([m, items]) => (
          <div key={m} className={`menu${open === m ? ' open' : ''}`}>
            <button onMouseDown={() => setOpen(open === m ? null : m)} onMouseEnter={() => open && setOpen(m)}>{m}</button>
            {open === m && (
              <div className="menu-pop">
                {items.map((it, i) => (it.sep ? <hr key={i} /> : (
                  <button key={i} disabled={it.disabled} onClick={() => {
                    setOpen(null);
                    it.run?.();
                  }}>
                    <span className="mi">{it.checked ? <Icon name="check" size={14} /> : it.icon ? <Icon name={it.icon} size={15} /> : null}</span>
                    <span className="ml">{it.label}</span>
                    {it.kbd && <span className="kbd">{it.kbd}</span>}
                  </button>
                )))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="doc-title" title={filePath ?? 'Not saved yet'}>
        <span className={`dot${saved ? ' saved' : ''}`} title={saved ? 'All changes saved' : 'Unsaved changes'} />
        <b>{name}</b>
        <span>{filePath ? filePath.split(/[\\/]/).pop() : 'Unsaved'}</span>
      </div>
      <div className="right">
        <button className="icon-btn" title="Undo (Ctrl+Z)" disabled={!past} onClick={() => st().undo()}><Icon name="undo" /></button>
        <button className="icon-btn" title="Redo (Ctrl+Y)" disabled={!future} onClick={() => st().redo()}><Icon name="redo" /></button>
        <button className="icon-btn" title="Save (Ctrl+S)" onClick={() => void st().saveCharacter()}><Icon name="save" /></button>
        <button className="btn small" style={{ marginLeft: 4 }} onClick={() => void importLibrary()} title="Import library (Ctrl+I)"><Icon name="import" size={14} />Import</button>
      </div>
    </div>
  );
}

