import { ACCESSORY_BY_ID } from '../model/looks';
import { STYLE_PRESETS } from '../model/presets';
import type { StylePreset } from '../model/types';
import { useStore } from '../state/store';
import { saveView, takeScreenshot } from './MenuBar';
import { regionLabel, useHover } from './Viewport';

const CAMS: [string, string, string][] = [
  ['front', 'Front', '1'],
  ['threeQuarter', '¾', '2'],
  ['side', 'Side', '3'],
  ['back', 'Back', ''],
  ['face', 'Face', '4'],
  ['upper', 'Upper', ''],
  ['frame', 'Frame', '0'],
];

export function Toolstrip() {
  const ui = useStore((s) => s.ui);
  const style = useStore((s) => s.identity.style);
  const equipped = useStore((s) => s.identity.equipped);
  const packs = useStore((s) => s.packs);
  const hover = useHover();
  const st = useStore.getState;
  const sel = equipped.find((e) => e.uid === ui.selectedEquip);
  const selName = sel ? ACCESSORY_BY_ID[sel.id]?.label ?? packs.find((p) => p.id === sel.id)?.displayName ?? sel.id : null;

  return (
    <>
      <div className="toolstrip">
        {CAMS.map(([id, label, key]) => (
          <button key={id} onClick={() => st().requestCamera(id)} title={key ? `${label} view (${key})` : `${label} view`}>{label}</button>
        ))}
        <span className="sep" />
        <button className={ui.shapeDrag ? 'on' : ''} onClick={() => st().setUI({ shapeDrag: !ui.shapeDrag })} title="Drag body regions to edit their sliders (D)">Drag shape</button>
        <button className={ui.turntable ? 'on' : ''} onClick={() => st().setUI({ turntable: !ui.turntable })} title="Turntable (T)">Turntable</button>
        <span className="sep" />
        {(Object.keys(STYLE_PRESETS) as StylePreset[]).map((s) => (
          <button key={s} className={style === s ? 'on' : ''} onClick={() => st().setStyle(s)} title={STYLE_PRESETS[s].hint}>{STYLE_PRESETS[s].label}</button>
        ))}
        <span className="sep" />
        <button onClick={takeScreenshot} title="Save a PNG of the viewport">Shot</button>
        <button onClick={saveView} title="Remember this camera">Save view</button>
      </div>

      <div className="vp-right">
        {sel && (
          <div className="gizmo-bar">
            {(['translate', 'rotate', 'scale'] as const).map((m, i) => (
              <button key={m} className={ui.gizmoMode === m ? 'on' : ''} onClick={() => st().setUI({ gizmoMode: m })} title={`${'WER'[i]}`}>
                {m === 'translate' ? 'Move' : m === 'rotate' ? 'Rotate' : 'Scale'}
              </button>
            ))}
            <button onClick={() => st().updateEquip(sel.uid, (e) => { e.offset = { p: [0, 0, 0], r: [0, 0, 0], s: 1 }; })} title="Reset the fit">Reset</button>
            <button onClick={() => st().setUI({ selectedEquip: null })} title="Deselect (Esc)">✕</button>
          </div>
        )}
        {ui.savedViews.length > 0 && (
          <div className="gizmo-bar">
            {ui.savedViews.map((v) => <button key={v.name} onClick={() => st().requestCamera(v.name)}>{v.name}</button>)}
          </div>
        )}
      </div>

      <div className="vp-corner">
        {selName && <div className="vp-badge">Selected <b>{selName}</b></div>}
        {hover.region && (
          <div className="vp-badge">
            <b>{regionLabel(hover.region)}</b>
            {ui.shapeDrag ? (hover.dragKeys.length ? ' · drag to shape' : ' · click to open its sliders') : ' · click to open its sliders'}
          </div>
        )}
        {ui.shapeDrag && !hover.region && <div className="vp-badge">Drag shape is on. Hover a body region, then drag.</div>}
      </div>
    </>
  );
}
