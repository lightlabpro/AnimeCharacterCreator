import { useRef, useState } from 'react';
import { applyArchetype } from '../model/character';
import { MIX_SCOPES, WHEEL_SLOTS, scopeControlIds, slotDirection, wheelWeights, type MixScope, type MixerSlot } from '../model/mixer';
import { POSE_LABELS, POSE_NAMES } from '../model/performance';
import { ARCHETYPES } from '../model/presets';
import { openTextFile, saveTextFile } from '../library/platform';
import { useStore } from '../state/store';
import { Section, Seg } from './controls';

const SIZE = 260;
const C = SIZE / 2;
const R = 96;

export function MixerPanel() {
  const mixer = useStore((s) => s.mixer);
  const id = useStore((s) => s.identity);
  const family = useStore((s) => s.family);
  const perfPose = useStore((s) => s.perf.pose);
  const st = useStore.getState;
  const svgRef = useRef<SVGSVGElement>(null);
  const [dragging, setDragging] = useState(false);
  const humanoid = id.bodyKind === 'adult' || id.bodyKind === 'child';
  const filled = mixer.slots.map((s) => !!s);
  const weights = wheelWeights(mixer.handle, filled);
  const hasSlots = filled.some(Boolean);

  const toHandle = (ev: React.PointerEvent): [number, number] => {
    const r = svgRef.current!.getBoundingClientRect();
    let x = ((ev.clientX - r.left) / r.width) * SIZE - C;
    let y = ((ev.clientY - r.top) / r.height) * SIZE - C;
    const len = Math.hypot(x, y);
    if (len > R) {
      x = (x / len) * R;
      y = (y / len) * R;
    }
    return [x / R, y / R];
  };

  const down = (ev: React.PointerEvent) => {
    if (mixer.mode !== 'mix' || !hasSlots) return;
    (ev.target as Element).setPointerCapture?.(ev.pointerId);
    setDragging(true);
    st().mixerBegin();
    st().mixerSetHandle(toHandle(ev));
  };
  const move = (ev: React.PointerEvent) => {
    if (dragging) st().mixerSetHandle(toHandle(ev));
  };
  const up = () => {
    if (!dragging) return;
    setDragging(false);
    st().mixerEnd();
  };

  const saveWheel = async () => {
    const path = await saveTextFile('face-wheel.json', JSON.stringify({ format: 'face-wheel', scope: mixer.scope, slots: mixer.slots }, null, 2));
    if (path) st().toast(`Saved the wheel to ${path}`);
  };
  const loadWheel = async () => {
    const f = await openTextFile();
    if (!f) return;
    try {
      const data = JSON.parse(f.text);
      if (data?.format !== 'face-wheel' || !Array.isArray(data.slots)) throw new Error('not a face wheel file');
      const slots: (MixerSlot | null)[] = Array.from({ length: WHEEL_SLOTS }, (_, i) => data.slots[i] ?? null);
      st().setMixer({ slots, scope: data.scope ?? mixer.scope, handle: [0, 0] });
      st().toast(`Loaded ${slots.filter(Boolean).length} faces into the wheel.`);
    } catch (e) {
      st().toast(`Could not load that wheel: ${(e as Error).message}`);
    }
  };

  return (
    <div className="panel-body">
      <div className="note">
        Fill the wheel with faces, then drag the handle toward the faces you want to blend. Only the chosen scope changes. Each drag is one undo step.
      </div>
      <div className="row between" style={{ margin: '6px 0' }}>
        <Seg value={mixer.mode} options={[{ id: 'mix', label: 'Mix' }, { id: 'edit', label: 'Edit slots' }]} onChange={(m) => st().setMixer({ mode: m })} />
        <button className="btn small" onClick={() => st().setMixer({ handle: [0, 0] })} title="Move the handle back to the center. The current face is kept.">Center</button>
      </div>
      <div className="field">
        <label>Scope</label>
        <select value={mixer.scope} onChange={(e) => st().setMixer({ scope: e.target.value as MixScope })}>
          {MIX_SCOPES.filter((s) => humanoid || !['muzzle', 'ears'].includes(s.id)).map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
        </select>
      </div>

      <svg ref={svgRef} className="wheel" width={SIZE} height={SIZE} viewBox={`0 0 ${SIZE} ${SIZE}`} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
        <circle cx={C} cy={C} r={R} fill="var(--bg0)" stroke="var(--line2)" />
        <circle cx={C} cy={C} r={R * 0.5} fill="none" stroke="var(--line)" strokeDasharray="3 4" />
        {Array.from({ length: WHEEL_SLOTS }, (_, i) => {
          const [dx, dy] = slotDirection(i);
          return <line key={`l${i}`} x1={C} y1={C} x2={C + dx * R} y2={C + dy * R} stroke="var(--line)" />;
        })}
        {Array.from({ length: WHEEL_SLOTS }, (_, i) => {
          const [dx, dy] = slotDirection(i);
          const s = mixer.slots[i];
          const w = weights[i];
          const x = C + dx * (R + 18);
          const y = C + dy * (R + 18);
          return (
            <g key={i} className={`slot${s ? ' filled' : ''}`} onPointerDown={(ev) => {
              if (mixer.mode !== 'edit') return;
              ev.stopPropagation();
              if (s) st().mixerClear(i);
              else st().mixerCapture(i, st().identity, `${st().identity.name}`);
            }}>
              <circle className="bg" cx={x} cy={y} r={17} />
              {w > 0.01 && <circle cx={x} cy={y} r={17} fill="none" stroke="var(--accent2)" strokeWidth={2} strokeDasharray={`${w * 107} 107`} transform={`rotate(-90 ${x} ${y})`} />}
              <text x={x} y={y}>{s ? s.label.slice(0, 5) : i + 1}</text>
            </g>
          );
        })}
        <circle className="handle" cx={C + mixer.handle[0] * R} cy={C + mixer.handle[1] * R} r={9} style={{ opacity: hasSlots ? 1 : 0.35 }} />
      </svg>
      {!hasSlots && <div className="hint" style={{ textAlign: 'center' }}>The wheel is empty. Switch to Edit slots and click a slot to capture the current face, or fill slots below.</div>}

      <Section title="Slots" count={`${filled.filter(Boolean).length}/${WHEEL_SLOTS}`}>
        <div className="slot-list">
          {mixer.slots.map((s, i) => (
            <div key={i} className="slot-card">
              <div className="t">{i + 1}. {s ? s.label : 'Empty'}</div>
              <div className="w">{s ? `${Object.keys(s.values).length} values · weight ${Math.round(weights[i] * 100)}%` : 'No face'}</div>
              <div className="row tight">
                <button className="btn small" onClick={() => st().mixerCapture(i, st().identity, st().identity.name)} title="Store the current face in this slot">Capture</button>
                {s && <button className="btn small" onClick={() => st().mixerClear(i)}>Clear</button>}
              </div>
              {humanoid && (
                <select className="inp" value="" onChange={(e) => {
                  const a = ARCHETYPES.find((x) => x.id === e.target.value);
                  if (a) st().mixerCapture(i, applyArchetype(st().identity, a.id), a.label);
                }}>
                  <option value="">Fill from species…</option>
                  {ARCHETYPES.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
                </select>
              )}
              {family.length > 0 && (
                <select className="inp" value="" onChange={(e) => {
                  const f = family[Number(e.target.value)];
                  if (f) st().mixerCapture(i, f.identity, f.label);
                }}>
                  <option value="">Fill from family…</option>
                  {family.map((f, fi) => <option key={fi} value={fi}>{f.label}</option>)}
                </select>
              )}
            </div>
          ))}
        </div>
      </Section>

      <Section title="Wheel tools">
        <div className="row">
          <button className="btn small" onClick={() => st().randomize(scopeControlIds(st().mixer.scope))}>Randomize scope</button>
          <button className="btn small" onClick={saveWheel}>Save wheel</button>
          <button className="btn small" onClick={loadWheel}>Load wheel</button>
          <button className="btn small danger" onClick={() => st().setMixer({ slots: Array(WHEEL_SLOTS).fill(null), handle: [0, 0] })}>Clear all</button>
        </div>
        <div className="row" style={{ marginTop: 6 }}>
          <button className="btn small" disabled={id.bodyKind !== 'adult' && id.bodyKind !== 'beast'} onClick={() => st().makeFamily()}>Make family</button>
          {family.map((f, i) => <button key={i} className="btn small ghost" onClick={() => st().loadIdentity(f.identity)} title="Open this family member">{f.label}</button>)}
        </div>
      </Section>

      <Section title="Preview with an expression" defaultOpen={false}>
        <div className="hint" style={{ marginBottom: 6 }}>Check that the blended face still reads well while emoting. This does not change the character.</div>
        <div className="chips">
          <button className={`chip${!perfPose ? ' on' : ''}`} onClick={() => st().setPerf({ pose: null })}>Neutral</button>
          {POSE_NAMES.filter((p) => p !== 'Neutral').map((p) => <button key={p} className={`chip${perfPose === p ? ' on' : ''}`} onClick={() => st().setPerf({ pose: p, poseWeight: 1 })}>{POSE_LABELS[p]}</button>)}
        </div>
      </Section>
    </div>
  );
}
