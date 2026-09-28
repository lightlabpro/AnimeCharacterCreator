import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { ACCESSORY_BY_ID } from '../model/looks';
import { STYLE_PRESETS } from '../model/presets';
import type { StylePreset } from '../model/types';
import { useStore } from '../state/store';
import { Icon } from './icons';
import { saveView, takeScreenshot } from './MenuBar';
import { getEngine, regionLabel, useHover } from './Viewport';

const CAMS: [string, string, string, string][] = [
  ['front', 'Front', '1', 'camFront'],
  ['threeQuarter', 'Three-quarter', '2', 'camQuarter'],
  ['side', 'Side', '3', 'camSide'],
  ['back', 'Back', '', 'camBack'],
  ['face', 'Face', '4', 'camFace'],
  ['upper', 'Upper body', '', 'camUpper'],
  ['frame', 'Frame all', '0', 'frame'],
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
        {CAMS.map(([id, label, key, icon]) => (
          <button key={id} className={`tb${key ? '' : ' opt'}`} onClick={() => st().requestCamera(id)} title={key ? `${label} (${key})` : label}>
            <Icon name={icon} />
          </button>
        ))}
        <span className="sep" />
        <button className={`tb${ui.shapeDrag ? ' on' : ''}`} onClick={() => st().setUI({ shapeDrag: !ui.shapeDrag })} title="Drag body regions to shape them (D)">
          <Icon name="drag" />
        </button>
        <button className={`tb${ui.turntable ? ' on' : ''}`} onClick={() => st().setUI({ turntable: !ui.turntable })} title="Turntable (T)">
          <Icon name="turntable" />
        </button>
        <span className="sep" />
        <span className="opt" style={{ display: 'inline-flex', color: 'var(--dim)' }}><Icon name="palette" size={15} /></span>
        <select className="tb-select" value={style} onChange={(e) => st().setStyle(e.target.value as StylePreset)} title={STYLE_PRESETS[style].hint}>
          {(Object.keys(STYLE_PRESETS) as StylePreset[]).map((s) => <option key={s} value={s}>{STYLE_PRESETS[s].label}</option>)}
        </select>
        <span className="sep opt" />
        <button className="tb opt" onClick={takeScreenshot} title="Save a PNG of the viewport"><Icon name="camera" /></button>
        <button className="tb opt" onClick={saveView} title="Remember this camera"><Icon name="bookmark" /></button>
        {ui.savedViews.length > 0 && (
          <select className="tb-select opt" value="" onChange={(e) => e.target.value && st().requestCamera(e.target.value)} title="Saved views">
            <option value="">Views</option>
            {ui.savedViews.map((v) => <option key={v.name} value={v.name}>{v.name}</option>)}
          </select>
        )}
      </div>

      <div className="vp-right">
        {sel && (
          <div className="gizmo-bar">
            <span className="lbl" title={selName ?? ''}>{selName}</span>
            {(['translate', 'rotate', 'scale'] as const).map((m, i) => (
              <button key={m} className={`tb${ui.gizmoMode === m ? ' on' : ''}`} onClick={() => st().setUI({ gizmoMode: m })} title={`${m === 'translate' ? 'Move' : m === 'rotate' ? 'Rotate' : 'Scale'} (${'WER'[i]})`}>
                <Icon name={m === 'translate' ? 'move' : m} />
              </button>
            ))}
            <button className="tb" onClick={() => st().updateEquip(sel.uid, (e) => { e.offset = { p: [0, 0, 0], r: [0, 0, 0], s: 1 }; })} title="Reset the fit"><Icon name="reset" /></button>
            <button className="tb" onClick={() => st().setUI({ selectedEquip: null })} title="Deselect (Esc)"><Icon name="close" /></button>
          </div>
        )}
      </div>

      <div className="vp-corner">
        {hover.region && (
          <div className="vp-badge">
            <Icon name="drag" size={13} />
            <b>{regionLabel(hover.region)}</b>
            <span>{ui.shapeDrag && hover.dragKeys.length ? 'Drag to shape' : 'Click to open its sliders'}</span>
          </div>
        )}
        {ui.shapeDrag && !hover.region && <div className="vp-badge"><Icon name="drag" size={13} />Drag shape is on. Hover a body region, then drag.</div>}
      </div>

      <AxisWidget />
    </>
  );
}

const AXES: { v: [number, number, number]; label: string; color: string; cam?: string }[] = [
  { v: [1, 0, 0], label: 'X', color: '#f06a6a', cam: 'side' },
  { v: [0, 1, 0], label: 'Y', color: '#3ecf8e', cam: 'frame' },
  { v: [0, 0, 1], label: 'Z', color: '#4f8cff', cam: 'front' },
  { v: [-1, 0, 0], label: '', color: '#f06a6a' },
  { v: [0, -1, 0], label: '', color: '#3ecf8e' },
  { v: [0, 0, -1], label: '', color: '#4f8cff', cam: 'back' },
];

function AxisWidget() {
  const [q, setQ] = useState<[number, number, number, number]>([0, 0, 0, 1]);
  const last = useRef('');
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const v = getEngine()?.viewQuaternion();
      if (v) {
        const k = v.map((x) => x.toFixed(3)).join();
        if (k !== last.current) {
          last.current = k;
          setQ(v);
        }
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);
  const inv = new THREE.Quaternion(q[0], q[1], q[2], q[3]).invert();
  const C = 39;
  const R = 26;
  const pts = AXES.map((a) => {
    const p = new THREE.Vector3(...a.v).applyQuaternion(inv);
    return { ...a, x: C + p.x * R, y: C - p.y * R, z: p.z };
  }).sort((a, b) => a.z - b.z);
  return (
    <div className="axis" title="View orientation. Click an axis to snap the camera.">
      <svg width={78} height={78}>
        {pts.filter((p) => p.label).map((p) => <line key={`l${p.label}`} x1={C} y1={C} x2={p.x} y2={p.y} stroke={p.color} strokeWidth={2} strokeLinecap="round" opacity={0.85} />)}
        {pts.map((p, i) => (
          <g key={i} className={`ax${p.label ? '' : ' neg'}`} onClick={() => p.cam && useStore.getState().requestCamera(p.cam)} style={{ cursor: p.cam ? 'pointer' : 'default' }}>
            <circle cx={p.x} cy={p.y} r={p.label ? 8 : 5.5} fill={p.label ? p.color : 'rgba(20,22,26,0.9)'} stroke={p.color} strokeWidth={p.label ? 0 : 1.5} opacity={p.z < -0.2 ? 0.55 : 1} />
            {p.label && <text x={p.x} y={p.y}>{p.label}</text>}
          </g>
        ))}
      </svg>
    </div>
  );
}
