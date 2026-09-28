import { useState } from 'react';
import { DEFAULT_POSES, PF_KEYS, POSE_LABELS, POSE_NAMES, VISEME_SHAPES, WRINKLE_REGIONS, poseWeights, type PFKeyDef } from '../model/performance';
import type { FaceProfile } from '../model/types';
import { useStore } from '../state/store';
import { Note, Section, Seg, ValueSlider } from './controls';
import { Icon } from './icons';

const GROUPS: PFKeyDef['group'][] = ['Eyes', 'Brows', 'Jaw', 'Visemes', 'Emotions', 'Tongue'];

export function FaceProfilePanel() {
  const profile = useStore((s) => s.identity.faceProfile);
  const perf = useStore((s) => s.perf);
  const kind = useStore((s) => s.identity.bodyKind);
  const st = useStore.getState;
  const [mode, setMode] = useState<'manual' | 'expression'>('manual');
  const [editing, setEditing] = useState<string>('Happy');
  const [group, setGroup] = useState<PFKeyDef['group']>('Eyes');

  const editProfile = (fn: (p: FaceProfile) => void, live = false) => (live ? st().editLive : st().commit)((x) => {
    fn(x.faceProfile);
  });
  const current = poseWeights(editing, profile);
  const isCustom = !!profile.expressions[editing];

  const startEditing = (name: string) => {
    setEditing(name);
    st().setPerf({ pose: name, poseWeight: 1, viseme: null, manual: {} });
  };

  const keys = PF_KEYS.filter((k) => k.group === group && (kind !== 'robot' || k.group !== 'Tongue'));

  return (
    <div className="panel-body">
      <Note>
        The face profile is how this character emotes. Expression edits are saved with the character; manual keys are live performance only and are cleared by Reset Performance.
      </Note>
      <div className="field">
        <label>Rig mode</label>
        <Seg full value={profile.rig} options={[{ id: 'hybrid', label: 'Hybrid', title: 'Bones for jaw and eyes, shapes for the rest' }, { id: 'bone', label: 'Bones' }, { id: 'morph', label: 'Shapes' }]} onChange={(r) => editProfile((p) => { p.rig = r; })} />
      </div>
      <div className="field">
        <label>Edit</label>
        <Seg full value={mode} options={[{ id: 'manual', label: 'Manual keys' }, { id: 'expression', label: 'Expressions' }]} onChange={(m) => {
          setMode(m);
          if (m === 'expression') startEditing(editing);
        }} />
      </div>

      {mode === 'expression' && (
        <Section title="Expression set" count={Object.keys(profile.expressions).length ? `${Object.keys(profile.expressions).length} edited` : undefined}>
          <div className="chips" style={{ marginBottom: 8 }}>
            {POSE_NAMES.filter((p) => p !== 'Neutral').map((p) => (
              <button key={p} className={`chip${editing === p ? ' on' : ''}`} onClick={() => startEditing(p)}>{POSE_LABELS[p]}{profile.expressions[p] ? ' •' : ''}</button>
            ))}
          </div>
          <div className="hint" style={{ marginBottom: 6 }}>Editing {POSE_LABELS[editing]}. The viewport shows the pose while you edit.</div>
          <div className="tabs inline">
            {GROUPS.filter((g) => g !== 'Visemes').map((g) => <button key={g} className={group === g ? 'on' : ''} onClick={() => setGroup(g)}>{g}</button>)}
          </div>
          {keys.filter((k) => k.group !== 'Visemes').map((k) => (
            <ValueSlider key={k.key} label={k.label} value={current[k.key] ?? 0} min={0} max={1}
              onBegin={() => st().beginEdit()}
              onLive={(v) => editProfile((p) => {
                p.expressions[editing] = { ...poseWeights(editing, p), [k.key]: v };
              }, true)}
              onCommit={() => st().endEdit()}
              onReset={() => editProfile((p) => {
                const w = { ...poseWeights(editing, p) };
                if (DEFAULT_POSES[editing]?.[k.key]) w[k.key] = DEFAULT_POSES[editing][k.key];
                else delete w[k.key];
                p.expressions[editing] = w;
              })} />
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn small" disabled={!isCustom} onClick={() => editProfile((p) => { delete p.expressions[editing]; })}>Revert {POSE_LABELS[editing]}</button>
            <button className="btn small" onClick={() => editProfile((p) => {
              p.expressions[editing] = { ...poseWeights(editing, p), ...perf.manual };
            })} title="Add the current manual keys to this expression">Add manual keys</button>
            <button className="btn small danger" disabled={!Object.keys(profile.expressions).length} onClick={() => editProfile((p) => { p.expressions = {}; })}>Revert all</button>
          </div>
        </Section>
      )}

      {mode === 'manual' && (
        <Section title="Face keys" count={Object.keys(perf.manual).length || undefined}>
          <div className="tabs inline">
            {GROUPS.map((g) => <button key={g} className={group === g ? 'on' : ''} onClick={() => setGroup(g)}>{g}</button>)}
          </div>
          {keys.map((k) => (
            <ValueSlider key={k.key} label={k.label} value={perf.manual[k.key] ?? 0} min={0} max={1}
              onLive={(v) => st().setPerfKey(k.key, v)}
              onReset={() => st().setPerfKey(k.key, 0)} />
          ))}
          <div className="row" style={{ marginTop: 8 }}>
            <button className="btn small" onClick={() => {
              const m = { ...st().perf.manual };
              for (const k of keys) delete m[k.key];
              st().setPerf({ manual: m });
            }}>Reset {group.toLowerCase()}</button>
            <button className="btn small" onClick={() => st().setPerf({ manual: {} })}>Neutral</button>
          </div>
        </Section>
      )}

      <Section title="Viseme set" defaultOpen={false}>
        <div className="hint" style={{ marginBottom: 6 }}>Click to hold a mouth shape. Talking in the play bar cycles through these.</div>
        <div className="chips">
          <button className={`chip${!perf.viseme ? ' on' : ''}`} onClick={() => st().setPerf({ viseme: null })}>Rest</button>
          {Object.keys(VISEME_SHAPES).map((k) => (
            <button key={k} className={`chip${perf.viseme === k ? ' on' : ''}`} onClick={() => st().setPerf({ viseme: k })}>{PF_KEYS.find((p) => p.key === k)!.label}</button>
          ))}
        </div>
      </Section>

      {kind !== 'robot' && (
        <Section title="Wrinkles">
          <div className="hint" style={{ marginBottom: 6 }}>How strongly each area creases when the face moves. Wrinkles only show while an expression drives them.</div>
          {WRINKLE_REGIONS.map((r) => (
            <ValueSlider key={r.id} label={r.label} value={profile.wrinkles[r.id] ?? 0.5} min={0} max={1}
              onBegin={() => st().beginEdit()}
              onLive={(v) => editProfile((p) => { p.wrinkles[r.id] = v; }, true)}
              onCommit={() => st().endEdit()}
              onReset={() => editProfile((p) => { p.wrinkles[r.id] = 0.5; })} />
          ))}
          <div className="row" style={{ marginTop: 6 }}>
            <button className="btn small" onClick={() => st().playClip('wrinkles', true)}><Icon name="play" size={12} />Preview wrinkles</button>
            <button className="btn small" onClick={() => st().stopClip()}><Icon name="stop" size={12} />Stop</button>
          </div>
        </Section>
      )}

      <div className="row" style={{ marginTop: 8 }}>
        <button className="btn danger" onClick={() => editProfile((p) => {
          p.expressions = {};
          p.wrinkles = { forehead: 0.5, brow: 0.5, eyes: 0.5, nose: 0.4, mouth: 0.5 };
          p.rig = 'hybrid';
        })}><Icon name="reset" size={14} />Reset face profile</button>
        <button className="btn" onClick={() => st().resetPerformance()}><Icon name="expression" size={14} />Reset performance</button>
      </div>
    </div>
  );
}
