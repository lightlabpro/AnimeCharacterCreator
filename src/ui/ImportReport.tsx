import { useStore } from '../state/store';

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
          <h2>Import report</h2>
          <span className="pill cool">{report.kind === 'root' ? 'Library root' : 'Category folder'}</span>
          <span className="hint" style={{ marginLeft: 'auto' }}>{report.folder}</span>
        </header>
        <div className="body">
          <div className="row" style={{ marginBottom: 10 }}>
            <span className="pill good">{report.added.length} added</span>
            {report.replaced.length > 0 && <span className="pill">{report.replaced.length} replaced</span>}
            <span className={`pill${report.skipped.length ? ' bad' : ''}`}>{report.skipped.length} skipped</span>
          </div>
          {report.notes.map((n, i) => <div key={i} className="note">{n}</div>)}
          {report.added.length > 0 && (
            <>
              <div className="subhead">Added</div>
              <ul className="report-list">
                {report.added.map((a) => (
                  <li key={a.id}>
                    <span className="grow">{a.name}</span>
                    <span className="pill">{LIB_LABEL[a.library] ?? a.library}</span>
                    <span className="pill">{a.category}</span>
                    {report.replaced.includes(a.id) && <span className="pill">replaced</span>}
                  </li>
                ))}
              </ul>
            </>
          )}
          {report.skipped.length > 0 && (
            <>
              <div className="subhead">Skipped</div>
              <ul className="report-list">
                {report.skipped.map((s, i) => (
                  <li key={i}>
                    <span style={{ minWidth: 180 }}>{s.item}</span>
                    <span className="why">{s.reason}</span>
                  </li>
                ))}
              </ul>
            </>
          )}
          {!report.added.length && !report.skipped.length && <div className="empty">Nothing with a manifest was found in that folder.</div>}
        </div>
        <footer>
          <button className="btn primary" onClick={close}>Done</button>
        </footer>
      </div>
    </div>
  );
}

export function HelpModal({ onClose, shortcuts }: { onClose: () => void; shortcuts: [string, string][] }) {
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <header><h2>Keyboard and mouse</h2></header>
        <div className="body">
          <table className="kbd-table">
            <tbody>
              {shortcuts.map(([k, v]) => <tr key={k}><td>{k}</td><td>{v}</td></tr>)}
              <tr><td>Left drag</td><td>Orbit the camera</td></tr>
              <tr><td>Right drag or Shift drag</td><td>Pan</td></tr>
              <tr><td>Wheel</td><td>Zoom</td></tr>
              <tr><td>Click a body region</td><td>Open its sliders in Modify › Morphs</td></tr>
              <tr><td>Click worn gear</td><td>Select it and show the fit gizmo</td></tr>
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
  return (
    <div key={toast.nonce} className="toast" onClick={() => st().setUI({ toast: null })}>{toast.text}</div>
  );
}
