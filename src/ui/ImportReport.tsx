import { Fragment } from 'react';
import { useStore } from '../state/store';
import { Note } from './controls';
import { Icon } from './icons';

const LIB_LABEL: Record<string, string> = { humanoid: 'Humanoid', robot: 'Robot', full_beast: 'Full beast' };

export function ImportReportModal() {
  const report = useStore((s) => s.report);
  const show = useStore((s) => s.ui.showImportReport);
  const st = useStore.getState;
  if (!show || !report) return null;
  const close = () => st().setUI({ showImportReport: false });
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && close()}>
      <div className="modal">
        <header>
          <div className="ico-box"><Icon name="import" size={17} /></div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <h2>Import report</h2>
            <div className="sub" title={report.folder}>{report.folder}</div>
          </div>
          <span className="pill accent">{report.kind === 'root' ? 'Library root' : 'Category folder'}</span>
          <button className="icon-btn" title="Close" onClick={close}><Icon name="close" /></button>
        </header>
        <div className="body">
          <div className="stats">
            <div className="stat good"><div className="v">{report.added.length}</div><div className="k">Added</div></div>
            <div className="stat"><div className="v">{report.replaced.length}</div><div className="k">Replaced</div></div>
            <div className={`stat${report.skipped.length ? ' bad' : ''}`}><div className="v">{report.skipped.length}</div><div className="k">Skipped</div></div>
          </div>
          {report.notes.map((n, i) => <Note key={i}>{n}</Note>)}
          {report.added.length > 0 && (
            <table className="tbl">
              <thead>
                <tr><th /><th>Item</th><th>Library</th><th>Category</th></tr>
              </thead>
              <tbody>
                {report.added.map((a) => (
                  <tr key={a.id}>
                    <td className="st good"><Icon name="success" size={15} /></td>
                    <td>{a.name}{report.replaced.includes(a.id) && <span className="pill" style={{ marginLeft: 6 }}>replaced</span>}</td>
                    <td className="why">{LIB_LABEL[a.library] ?? a.library}</td>
                    <td className="why">{a.category}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {report.skipped.length > 0 && (
            <table className="tbl">
              <thead>
                <tr><th /><th>Skipped</th><th>Reason</th></tr>
              </thead>
              <tbody>
                {report.skipped.map((s, i) => (
                  <tr key={i}>
                    <td className="st bad"><Icon name="error" size={15} /></td>
                    <td style={{ whiteSpace: 'nowrap' }}>{s.item}</td>
                    <td className="why">{s.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {!report.added.length && !report.skipped.length && <div className="empty"><Icon name="folder" size={28} stroke={1.4} />Nothing with a manifest was found in that folder.</div>}
        </div>
        <footer>
          <button className="btn primary" onClick={close}>Done</button>
        </footer>
      </div>
    </div>
  );
}

/** "Ctrl+Y or Ctrl+Shift+Z" and "1 / 2 / 3" become keycaps; anything written as words stays text. */
function Keys({ spec }: { spec: string }) {
  const alts = spec.split(/ or | \/ /);
  return (
    <>
      {alts.map((alt, i) => (
        <Fragment key={i}>
          {i > 0 && <span className="hint" style={{ margin: '0 4px' }}>{spec.includes(' or ') ? 'or' : '/'}</span>}
          {alt.split('+').map((k, j) => (
            <Fragment key={j}>
              {j > 0 && <span className="hint">+</span>}
              <span className="kbd">{k}</span>
            </Fragment>
          ))}
        </Fragment>
      ))}
    </>
  );
}

const isKeySpec = (s: string) => !/\b[a-z]{3,}\b/.test(s.replace(/\bor\b/g, ''));

const MOUSE: [string, string][] = [
  ['Left drag', 'Orbit the camera'],
  ['Right drag or Shift drag', 'Pan'],
  ['Wheel', 'Zoom'],
  ['Click a body region', 'Open its sliders in Modify › Morphs'],
  ['Click worn gear', 'Select it and show the fit gizmo'],
];

export function HelpModal({ onClose, shortcuts }: { onClose: () => void; shortcuts: [string, string][] }) {
  const keys = shortcuts.filter(([k]) => isKeySpec(k));
  const mouse = [...MOUSE, ...shortcuts.filter(([k]) => !isKeySpec(k))];
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ width: 'min(680px, 92vw)' }}>
        <header>
          <div className="ico-box"><Icon name="keyboard" size={17} /></div>
          <h2 style={{ flex: 1 }}>Keyboard and mouse</h2>
          <button className="icon-btn" title="Close" onClick={onClose}><Icon name="close" /></button>
        </header>
        <div className="body">
          <table className="tbl">
            <thead><tr><th style={{ width: '46%' }}>Keyboard</th><th /></tr></thead>
            <tbody>
              {keys.map(([k, v]) => <tr key={k}><td><Keys spec={k} /></td><td className="why">{v}</td></tr>)}
            </tbody>
          </table>
          <table className="tbl">
            <thead><tr><th style={{ width: '46%' }}>Mouse</th><th /></tr></thead>
            <tbody>
              {mouse.map(([k, v]) => <tr key={k}><td>{k}</td><td className="why">{v}</td></tr>)}
            </tbody>
          </table>
        </div>
        <footer><button className="btn primary" onClick={onClose}>Close</button></footer>
      </div>
    </div>
  );
}

export function Toast() {
  const toast = useStore((s) => s.ui.toast);
  const st = useStore.getState;
  if (!toast) return null;
  const warn = /could not|cannot|failed|belongs to/i.test(toast.text);
  return (
    <div key={toast.nonce} className="toast" onClick={() => st().setUI({ toast: null })} role="status">
      <span className="ico" style={warn ? { color: 'var(--warn)' } : undefined}><Icon name={warn ? 'warning' : 'info'} size={15} /></span>
      <span>{toast.text}</span>
    </div>
  );
}
