import { useMemo } from 'react';
import { changedControls } from '../model/character';
import { CONTROLS, CONTROL_BY_ID, controlPath, controlsFor, isControlVisible } from '../model/controls';
import { ACCESSORY_BY_ID, hairStylesFor, lookSlotsFor, type HairSlot } from '../model/looks';
import { BODY_POSES, POSE_LABELS, POSE_NAMES, PF_KEYS, VISEME_KEYS } from '../model/performance';
import { ARCHETYPES, HAIR_COLORS, SKIN_TONES, STYLE_PRESETS, resolveStyle, type RenderOverrides } from '../model/presets';
import { BODY_KINDS, type BodyKind, type ControlDef, type HairPiece, type Identity } from '../model/types';
import { useStore, type ModifyTab } from '../state/store';
import { regionLabel } from './Viewport';
import { ColorRow, ControlSlider, Note, Section, Seg, Toggle, ValueSlider } from './controls';
import { Icon } from './icons';
import { loadBaked, saveBaked } from './LibraryPanel';

const TABS: { id: ModifyTab; label: string }[] = [
  { id: 'attribute', label: 'Attribute' },
  { id: 'pose', label: 'Pose' },
  { id: 'morphs', label: 'Morphs' },
  { id: 'material', label: 'Material' },
  { id: 'physics', label: 'Physics' },
];

export function ModifyPanel() {
  const tab = useStore((s) => s.ui.modifyTab);
  const st = useStore.getState;
  return (
    <>
      <div className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={tab === t.id ? 'on' : ''} onClick={() => st().setUI({ modifyTab: t.id })}>{t.label}</button>
        ))}
      </div>
      <div className="panel-body">
        {tab === 'attribute' && <AttributeTab />}
        {tab === 'pose' && <PoseTab />}
        {tab === 'morphs' && <MorphsTab />}
        {tab === 'material' && <MaterialTab />}
        {tab === 'physics' && <PhysicsTab />}
      </div>
    </>
  );
}

function AttributeTab() {
  const id = useStore((s) => s.identity);
  const sel = useStore((s) => s.ui.selectedEquip);
  const gizmo = useStore((s) => s.ui.gizmoMode);
  const packs = useStore((s) => s.packs);
  const st = useStore.getState;
  const humanoid = id.bodyKind === 'adult' || id.bodyKind === 'child';
  const selEquip = id.equipped.find((e) => e.uid === sel) ?? null;
  const selDef = selEquip ? ACCESSORY_BY_ID[selEquip.id] : undefined;
  const selPack = selEquip ? packs.find((p) => p.id === selEquip.id) : undefined;
  const ageKeys = id.bodyKind === 'adult' ? 'adult' : id.bodyKind === 'beast' ? 'beast' : null;
  const years = id.values['age.years'] ?? 0;
  return (
    <>
      <Section title="Character">
      <div className="field">
        <label>Name</label>
        <input type="text" value={id.name} onFocus={() => st().beginEdit()} onBlur={() => st().endEdit()} onChange={(e) => st().editLive((x) => {
          x.name = e.target.value;
        })} />
      </div>
      <div className="field">
        <label>Body</label>
        <Seg<BodyKind> full value={id.bodyKind} options={BODY_KINDS.map((b) => ({ id: b.id, label: b.id === 'beast' ? 'Dragon' : b.label.replace(' humanoid', ''), title: b.hint }))} onChange={(k) => st().setBodyKind(k)} />
      </div>
      <div className="field">
        <label>Picture style</label>
        <Seg full value={id.style} options={Object.values(STYLE_PRESETS).map((s) => ({ id: s.id, label: s.label, title: s.hint }))} onChange={(s) => st().setStyle(s)} />
      </div>
      {humanoid && (
        <div className="field">
          <label>Species</label>
          <select value={id.archetype} onChange={(e) => st().setArchetype(e.target.value)}>
            {ARCHETYPES.map((a) => <option key={a.id} value={a.id}>{a.label}</option>)}
          </select>
        </div>
      )}
      {id.bodyKind === 'adult' && (
        <div className="field">
          <label>Presentation</label>
          <div className="seg full">
            {(['feminine', 'neutral', 'masculine'] as const).map((p) => <button key={p} onClick={() => st().setPresentation(p)} title="Moves the presentation sliders. They stay editable.">{p[0].toUpperCase() + p.slice(1)}</button>)}
          </div>
        </div>
      )}
      {ageKeys && (
        <div className="field">
          <label>Age</label>
          <div className="seg full">
            {([['youngAdult', 'Young', years < -30], ['adult', 'Adult', Math.abs(years) <= 30], ['old', 'Old', years > 30]] as const).map(([k, l, on]) => (
              <button key={k} className={on ? 'on' : ''} onClick={() => st().setAge(k)}>{l}</button>
            ))}
          </div>
        </div>
      )}
      {id.bodyKind === 'child' && <Note>The child body is always clothed and general audience. Adult presentation, age, facial hair, and muscle sliders are not part of it.</Note>}
      </Section>

      <Section title="Worn items" count={id.equipped.length}>
        {id.equipped.length === 0 && <div className="empty"><Icon name="outfit" size={28} />Nothing worn. Add outfits and accessories from the library.</div>}
        {id.equipped.map((e) => {
          const def = ACCESSORY_BY_ID[e.id];
          const pk = packs.find((p) => p.id === e.id);
          return (
            <div key={e.uid} className={`equip-row${sel === e.uid ? ' sel' : ''}`} onClick={() => st().setUI({ selectedEquip: sel === e.uid ? null : e.uid })}>
              <Icon name={e.slot === 'outfit' ? 'outfit' : 'accessory'} size={14} />
              <span className="nm">{def?.label ?? pk?.displayName ?? e.id}</span>
              <span className="slot">{e.slot}</span>
              <button className="icon-btn sm" title="Take off" onClick={(ev) => {
                ev.stopPropagation();
                st().unequip(e.uid);
              }}><Icon name="close" size={13} /></button>
            </div>
          );
        })}
        {selEquip && (
          <div className="stack edit-card">
            <div className="row between nowrap">
              <b style={{ fontSize: 12, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{selDef?.label ?? selPack?.displayName ?? selEquip.id}</b>
              <div className="row tight nowrap">
                {(['translate', 'rotate', 'scale'] as const).map((m) => (
                  <button key={m} className={`icon-btn${gizmo === m ? ' on' : ''}`} title={m === 'translate' ? 'Move' : m === 'rotate' ? 'Rotate' : 'Scale'} onClick={() => st().setUI({ gizmoMode: m })}><Icon name={m === 'translate' ? 'move' : m} /></button>
                ))}
              </div>
            </div>
            <div className="hint">Drag the gizmo in the viewport to adjust the fit. Outfits that follow the body shape ignore the offset.</div>
            {Object.entries({ ...(selDef?.colors ?? {}), ...selEquip.colors }).map(([k, v]) => (
              <ColorRow key={k} label={k[0].toUpperCase() + k.slice(1)} value={v}
                onBegin={() => st().beginEdit()} onEnd={() => st().endEdit()}
                onLive={(c) => st().editLive((x) => {
                  const e = x.equipped.find((q) => q.uid === selEquip.uid);
                  if (e) e.colors[k] = c;
                })}
                onChange={(c) => st().updateEquip(selEquip.uid, (e) => {
                  e.colors[k] = c;
                })} />
            ))}
            <ValueSlider label="Wear and damage" value={selEquip.damage} min={0} max={100} step={1} format={(v) => `${Math.round(v)}`}
              onBegin={() => st().beginEdit()}
              onLive={(v) => st().editLive((x) => {
                const e = x.equipped.find((q) => q.uid === selEquip.uid);
                if (e) e.damage = v;
              })}
              onCommit={(v) => {
                st().editLive((x) => {
                  const e = x.equipped.find((q) => q.uid === selEquip.uid);
                  if (e) e.damage = v;
                });
                st().endEdit();
              }} />
            <div className="row">
              <button className="btn small" onClick={() => st().updateEquip(selEquip.uid, (e) => {
                e.offset = { p: [0, 0, 0], r: [0, 0, 0], s: 1 };
              })}><Icon name="reset" size={13} />Reset fit</button>
              <button className="btn small ghost" onClick={() => st().setUI({ selectedEquip: null })}>Deselect</button>
            </div>
          </div>
        )}
      </Section>

      <Section title="Actions">
        <div className="row">
          <button className="btn" onClick={() => st().randomize()} title="Random identity values inside each slider's range"><Icon name="dice" size={14} />Randomize</button>
          <button className="btn" disabled={id.bodyKind !== 'adult'} onClick={() => st().makeChild()} title="Make a child counterpart of this adult"><Icon name="child" size={14} />Make child</button>
          <button className="btn" disabled={id.bodyKind !== 'adult' && id.bodyKind !== 'beast'} onClick={() => st().makeFamily()}><Icon name="family" size={14} />Make family</button>
        </div>
        <div className="row" style={{ marginTop: 6 }}>
          <button className="btn danger" onClick={() => st().resetIdentity()} title="Back to the dressed default for this body. Performance is kept."><Icon name="reset" size={14} />Reset identity</button>
          <button className="btn" onClick={() => st().resetPerformance()} title="Neutral face and pose. Identity is kept."><Icon name="expression" size={14} />Reset performance</button>
        </div>
      </Section>
    </>
  );
}

function PoseTab() {
  const perf = useStore((s) => s.perf);
  const kind = useStore((s) => s.identity.bodyKind);
  const st = useStore.getState;
  const setGaze = (k: 'x' | 'y' | 'converge', v: number) => st().setPerf({ gaze: { ...st().perf.gaze, [k]: v } });
  const setHead = (k: 'yaw' | 'pitch' | 'roll', v: number) => st().setPerf({ head: { ...st().perf.head, [k]: v } });
  return (
    <>
      <Note>Pose and face performance are never saved into the character. Reset Performance brings everything here back to neutral.</Note>
      <Section title="Body pose">
        <div className="chips">
          {BODY_POSES.map((p) => <button key={p.id} className={`chip${perf.bodyPose === p.id ? ' on' : ''}`} onClick={() => st().setPerf({ bodyPose: p.id })}>{p.label}</button>)}
        </div>
        {kind === 'beast' && <div className="hint" style={{ marginTop: 6 }}>The dragon keeps its four-legged stance. Body poses apply to the humanoid and robot.</div>}
      </Section>
      <Section title="Gaze">
        <ValueSlider label="Left and right" value={perf.gaze.x} min={-1} max={1} onLive={(v) => setGaze('x', v)} onReset={() => setGaze('x', 0)} />
        <ValueSlider label="Up and down" value={perf.gaze.y} min={-1} max={1} onLive={(v) => setGaze('y', v)} onReset={() => setGaze('y', 0)} />
        <ValueSlider label="Cross" value={perf.gaze.converge} min={0} max={1} onLive={(v) => setGaze('converge', v)} onReset={() => setGaze('converge', 0)} />
      </Section>
      <Section title="Head">
        <ValueSlider label="Turn" value={perf.head.yaw} min={-1} max={1} onLive={(v) => setHead('yaw', v)} onReset={() => setHead('yaw', 0)} />
        <ValueSlider label="Nod" value={perf.head.pitch} min={-1} max={1} onLive={(v) => setHead('pitch', v)} onReset={() => setHead('pitch', 0)} />
        <ValueSlider label="Tilt" value={perf.head.roll} min={-1} max={1} onLive={(v) => setHead('roll', v)} onReset={() => setHead('roll', 0)} />
      </Section>
      <Section title="Expression library">
        <div className="chips">
          <button className={`chip${!perf.pose ? ' on' : ''}`} onClick={() => st().setPerf({ pose: null })}>None</button>
          {POSE_NAMES.filter((p) => p !== 'Neutral').map((p) => <button key={p} className={`chip${perf.pose === p ? ' on' : ''}`} onClick={() => st().setPerf({ pose: p })}>{POSE_LABELS[p]}</button>)}
        </div>
        <ValueSlider label="Strength" value={perf.poseWeight} min={0} max={1} onLive={(v) => st().setPerf({ poseWeight: v })} onReset={() => st().setPerf({ poseWeight: 1 })} />
      </Section>
      <Section title="Hold a viseme">
        <div className="chips">
          <button className={`chip${!perf.viseme ? ' on' : ''}`} onClick={() => st().setPerf({ viseme: null })}>None</button>
          {VISEME_KEYS.map((k) => <button key={k} className={`chip${perf.viseme === k ? ' on' : ''}`} onClick={() => st().setPerf({ viseme: k })}>{PF_KEYS.find((x) => x.key === k)!.label}</button>)}
        </div>
      </Section>
    </>
  );
}

interface TreeNode {
  id: string;
  label: string;
  count: number;
}

function MorphsTab() {
  const id = useStore((s) => s.identity);
  const node = useStore((s) => s.ui.morphNode);
  const search = useStore((s) => s.ui.morphSearch);
  const favorites = useStore((s) => s.favorites);
  const st = useStore.getState;
  const kind = id.bodyKind;
  const visible = useMemo(() => controlsFor(kind, 'morphs').filter((c) => isControlVisible(c, kind, id.looks)), [kind, id.looks]);
  const used = changedControls(id).filter((k) => CONTROL_BY_ID[k]?.tab === 'morphs');
  const tops = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of visible) {
      const t = controlPath(c, kind)[0];
      m.set(t, (m.get(t) ?? 0) + 1);
    }
    return [...m.entries()];
  }, [visible, kind]);
  const nodes: TreeNode[] = [
    { id: 'Currently Used', label: 'In use', count: used.length },
    { id: 'Favorites', label: 'Favorites', count: favorites.filter((f) => CONTROL_BY_ID[f] && visible.includes(CONTROL_BY_ID[f])).length },
    { id: 'All', label: 'All', count: visible.length },
    ...tops.map(([t, n]) => ({ id: `top:${t}`, label: t, count: n })),
  ];
  const regionNode = node.startsWith('region:') ? node.slice(7) : null;
  if (regionNode) nodes.splice(3, 0, { id: node, label: `Picked: ${regionLabel(regionNode as never)}`, count: visible.filter((c) => c.region === regionNode).length });
  if (kind === 'adult' || kind === 'child') nodes.push({ id: 'Hair', label: 'Hair shape', count: 4 });

  const q = search.trim().toLowerCase();
  let list: ControlDef[];
  if (q) list = visible.filter((c) => c.label.toLowerCase().includes(q) || c.hint.toLowerCase().includes(q) || controlPath(c, kind).join(' ').toLowerCase().includes(q));
  else if (node === 'Currently Used') list = visible.filter((c) => used.includes(c.id));
  else if (node === 'Favorites') list = visible.filter((c) => favorites.includes(c.id));
  else if (regionNode) list = visible.filter((c) => c.region === regionNode);
  else if (node.startsWith('top:')) list = visible.filter((c) => controlPath(c, kind)[0] === node.slice(4));
  else list = visible;

  const groups = new Map<string, ControlDef[]>();
  for (const c of list) {
    const p = controlPath(c, kind);
    const g = p.slice(node.startsWith('top:') && !q ? 1 : 0).join(' › ') || p.join(' › ');
    groups.set(g, [...(groups.get(g) ?? []), c]);
  }
  const lookSlots = lookSlotsFor(kind);
  const lookFor = (group: string) => lookSlots.filter((s) => group.endsWith(s.group) || group === `Elements › ${s.group}`);

  const resetShown = () => st().commit((x) => {
    for (const c of list) delete x.values[c.id];
  });
  const bake = () => {
    const name = window.prompt('Name this preset. It appears in the library under Head or Body.', `${id.name} ${node.startsWith('top:') ? node.slice(4) : 'preset'}`);
    if (!name) return;
    const scope: 'Head' | 'Body' = list.some((c) => controlPath(c, kind)[0] === 'Head') && !list.some((c) => controlPath(c, kind)[0] === 'Body') ? 'Head' : 'Body';
    const values: Record<string, number> = {};
    for (const c of list) if (id.values[c.id]) values[c.id] = id.values[c.id];
    saveBaked([...loadBaked().filter((b) => b.name !== name), { name, kind, scope, values }]);
    st().toast(`Baked ${Object.keys(values).length} slider values into "${name}" under Library › ${scope}.`);
  };

  return (
    <>
      <div className="search" style={{ marginBottom: 8 }}>
        <Icon name="search" size={14} />
        <input placeholder="Search sliders" value={search} onChange={(e) => st().setUI({ morphSearch: e.target.value })} />
        {search && <button className="icon-btn sm" onClick={() => st().setUI({ morphSearch: '' })}><Icon name="close" size={13} /></button>}
      </div>
      <div className="row nowrap" style={{ marginBottom: 10 }}>
        <span className="pill">{list.length} sliders</span>
        <span className="grow" />
        <button className="btn small" onClick={bake} disabled={list.length === 0} title="Save the shown slider values as a reusable library preset"><Icon name="save" size={13} />Bake</button>
        <button className="icon-btn" onClick={() => st().randomize(list.map((c) => c.id))} disabled={list.length === 0} title="Randomize the shown sliders"><Icon name="dice" /></button>
        <button className="icon-btn" onClick={resetShown} disabled={list.length === 0} title="Set the shown sliders back to zero"><Icon name="reset" /></button>
      </div>
      <div className="morph-layout">
        <div className="tree">
          {nodes.map((n, i) => (
            <span key={n.id} style={{ display: 'contents' }}>
              {i === 3 && <span className="tsep" />}
              <button className={node === n.id && !q ? 'on' : ''} onClick={() => st().setUI({ morphNode: n.id, morphSearch: '' })} title={n.label}>
                <span>{n.label}</span>
                <span className="n">{n.count}</span>
              </button>
            </span>
          ))}
        </div>
        <div>
          {node === 'Hair' && !q ? <HairShape id={id} /> : (
            <>
              {[...groups.entries()].map(([g, arr]) => (
                <div key={g}>
                  <div className="subhead">{g}</div>
                  {lookFor(g).map((s) => (
                    <div className="field" key={s.slot} style={{ gridTemplateColumns: '90px 1fr' }}>
                      <label>{s.label}</label>
                      <select value={id.looks[s.slot] ?? s.options[0].id} onChange={(e) => st().setLook(s.slot, e.target.value)}>
                        {s.options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                      </select>
                    </div>
                  ))}
                  {arr.map((c) => <ControlSlider key={c.id} id={c.id} />)}
                </div>
              ))}
              {list.length === 0 && (
                <div className="empty">
                  <Icon name={node === 'Favorites' ? 'star' : 'sliders'} size={28} />
                  {node === 'Currently Used' ? 'No slider has been moved yet.' : node === 'Favorites' ? 'Star a slider to keep it here.' : 'Nothing matches.'}
                </div>
              )}
              {(node === 'All' || node === 'top:Elements') && !q && <HiddenLooks kind={kind} looks={id.looks} />}
            </>
          )}
        </div>
      </div>
    </>
  );
}

/** Looks that have no sliders yet are still choosable, so they stay reachable from Morphs. */
function HiddenLooks({ kind, looks }: { kind: BodyKind; looks: Record<string, string> }) {
  const st = useStore.getState;
  const slots = lookSlotsFor(kind).filter((s) => !CONTROLS.some((c) => isControlVisible(c, kind, looks) && controlPath(c, kind).join(' › ').endsWith(s.group)));
  if (!slots.length) return null;
  return (
    <>
      <div className="subhead">Element looks</div>
      {slots.map((s) => (
        <div className="field" key={s.slot} style={{ gridTemplateColumns: '90px 1fr' }}>
          <label>{s.label}</label>
          <select value={looks[s.slot] ?? s.options[0].id} onChange={(e) => st().setLook(s.slot, e.target.value)}>
            {s.options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
        </div>
      ))}
    </>
  );
}

function HairShape({ id }: { id: Identity }) {
  const st = useStore.getState;
  const slots: { slot: HairSlot; label: string; piece: HairPiece; index?: number }[] = [
    { slot: 'front', label: 'Front', piece: id.hair.front },
    { slot: 'back', label: 'Back and length', piece: id.hair.back },
    { slot: 'sides', label: 'Sides', piece: id.hair.sides },
    ...id.hair.extras.map((p, i) => ({ slot: 'extra' as HairSlot, label: `Extra: ${p.id}`, piece: p, index: i })),
  ];
  const edit = (slot: HairSlot, index: number | undefined, fn: (p: HairPiece) => void) => (x: Identity) => {
    const p = slot === 'extra' ? x.hair.extras[index!] : x.hair[slot];
    if (p) fn(p);
  };
  return (
    <>
      {slots.map(({ slot, label, piece, index }) => (
        <div key={`${slot}${index ?? ''}`}>
          <div className="subhead">{label}</div>
          {slot !== 'extra' && (
            <div className="field" style={{ gridTemplateColumns: '90px 1fr' }}>
              <label>Style</label>
              <select value={piece.id} onChange={(e) => st().commit(edit(slot, index, (p) => {
                p.id = e.target.value;
              }))}>
                {hairStylesFor(slot, id.bodyKind).map((h) => <option key={h.id} value={h.id}>{h.label}</option>)}
                {piece.id.startsWith('pack:') && <option value={piece.id}>Imported</option>}
              </select>
            </div>
          )}
          {(['volume', 'width', 'length'] as const).map((k) => (
            <ValueSlider key={k} label={k[0].toUpperCase() + k.slice(1)} value={piece[k]} min={-100} max={100} step={1} format={(v) => `${Math.round(v)}`}
              onBegin={() => st().beginEdit()}
              onLive={(v) => st().editLive(edit(slot, index, (p) => {
                p[k] = v;
              }))}
              onCommit={(v) => {
                st().editLive(edit(slot, index, (p) => {
                  p[k] = v;
                }));
                st().endEdit();
              }}
              onReset={() => st().commit(edit(slot, index, (p) => {
                p[k] = 0;
              }))} />
          ))}
        </div>
      ))}
    </>
  );
}

const COLOR_KEYS: Record<BodyKind, [string, string][]> = {
  adult: [['skin', 'Skin'], ['lip', 'Lips'], ['nail', 'Nails'], ['iris', 'Iris'], ['sclera', 'Eye white'], ['brow', 'Brows'], ['lash', 'Lashes'], ['surfacePrimary', 'Fur or scales'], ['surfaceSecondary', 'Pattern'], ['belly', 'Belly'], ['mane', 'Mane'], ['horn', 'Horns'], ['beak', 'Beak'], ['membrane', 'Fins and wings'], ['claw', 'Claws']],
  child: [['skin', 'Skin'], ['lip', 'Lips'], ['nail', 'Nails'], ['iris', 'Iris'], ['sclera', 'Eye white'], ['brow', 'Brows'], ['lash', 'Lashes'], ['surfacePrimary', 'Fur or scales'], ['surfaceSecondary', 'Pattern'], ['belly', 'Belly'], ['mane', 'Mane'], ['horn', 'Horns'], ['beak', 'Beak'], ['membrane', 'Fins and wings'], ['claw', 'Claws']],
  robot: [['robotPaint', 'Paint'], ['robotPanel', 'Panels'], ['robotJoint', 'Joints'], ['robotGlow', 'Glow']],
  beast: [['surfacePrimary', 'Scales'], ['surfaceSecondary', 'Pattern'], ['belly', 'Belly'], ['horn', 'Horns and spines'], ['membrane', 'Wing membrane'], ['claw', 'Claws'], ['iris', 'Iris'], ['sclera', 'Eye white']],
};

function MaterialTab() {
  const id = useStore((s) => s.identity);
  const st = useStore.getState;
  const humanoid = id.bodyKind === 'adult' || id.bodyKind === 'child';
  const mats = controlsFor(id.bodyKind, 'material').filter((c) => isControlVisible(c, id.bodyKind, id.looks));
  const matGroups = new Map<string, ControlDef[]>();
  for (const c of mats) {
    const g = controlPath(c, id.bodyKind).slice(1).join(' › ') || 'Material';
    matGroups.set(g, [...(matGroups.get(g) ?? []), c]);
  }
  const liveColor = (key: string) => ({
    onBegin: () => st().beginEdit(),
    onEnd: () => st().endEdit(),
    onLive: (c: string) => st().editLive((x) => {
      x.colors[key] = c;
    }),
    onChange: (c: string) => st().setColor(key, c),
  });
  const surface = id.looks.surface ?? 'skin';
  const relevant = (k: string) => {
    if (!humanoid) return true;
    const L = id.looks;
    if (['surfacePrimary', 'surfaceSecondary', 'belly'].includes(k)) return surface !== 'skin';
    if (k === 'mane') return (L.mane ?? 'none') !== 'none';
    if (k === 'horn') return (L.horns ?? 'none') !== 'none';
    if (k === 'beak') return L.muzzle === 'bird';
    if (k === 'membrane') return (L.wings ?? 'none') !== 'none' || (L.frill ?? 'none') !== 'none' || L.ears === 'fin' || L.tail === 'fish' || L.horns === 'fins';
    if (k === 'claw') return (L.hands ?? 'human') !== 'human' || (L.feet ?? 'human') !== 'human';
    return true;
  };
  return (
    <>
      {humanoid && (
        <Section title="Skin tone">
          <div className="swatches">
            {SKIN_TONES.map((t) => <button key={t.id} className={`swatch${id.colors.skin === t.color ? ' on' : ''}`} style={{ background: t.color }} title={t.label} onClick={() => st().setColor('skin', t.color)} />)}
          </div>
        </Section>
      )}
      <Section title="Colors">
        {COLOR_KEYS[id.bodyKind].filter(([k]) => relevant(k)).map(([k, l]) => <ColorRow key={k} label={l} value={id.colors[k] ?? '#888888'} {...liveColor(k)} />)}
      </Section>
      {humanoid && (
        <Section title="Hair color">
          <div className="swatches" style={{ marginBottom: 6 }}>
            {HAIR_COLORS.map((c) => (
              <button key={c.id} className="swatch" style={{ background: `linear-gradient(180deg, ${c.root}, ${c.tip})` }} title={c.label} onClick={() => st().commit((x) => {
                for (const p of [x.hair.front, x.hair.back, x.hair.sides, ...x.hair.extras]) {
                  p.root = c.root;
                  p.tip = c.tip;
                }
                x.colors.brow = c.root;
              })} />
            ))}
          </div>
          {(['front', 'back', 'sides'] as const).map((slot) => (
            <div key={slot}>
              <ColorRow label={`${slot[0].toUpperCase() + slot.slice(1)} root`} value={id.hair[slot].root}
                onBegin={() => st().beginEdit()} onEnd={() => st().endEdit()}
                onLive={(c) => st().editLive((x) => { x.hair[slot].root = c; })}
                onChange={(c) => st().commit((x) => { x.hair[slot].root = c; })} />
              <ColorRow label={`${slot[0].toUpperCase() + slot.slice(1)} tip`} value={id.hair[slot].tip}
                onBegin={() => st().beginEdit()} onEnd={() => st().endEdit()}
                onLive={(c) => st().editLive((x) => { x.hair[slot].tip = c; })}
                onChange={(c) => st().commit((x) => { x.hair[slot].tip = c; })} />
            </div>
          ))}
          <ValueSlider label="Highlight band" value={id.hair.back.highlight} min={0} max={1}
            onBegin={() => st().beginEdit()}
            onLive={(v) => st().editLive((x) => {
              for (const p of [x.hair.front, x.hair.back, x.hair.sides, ...x.hair.extras]) p.highlight = v;
            })}
            onCommit={() => st().endEdit()} />
          <button className="btn small" style={{ marginTop: 4 }} onClick={() => st().commit((x) => {
            for (const p of x.hair.extras) {
              p.root = x.hair.back.root;
              p.tip = x.hair.back.tip;
            }
            x.hair.front = { ...x.hair.front, root: x.hair.back.root, tip: x.hair.back.tip };
            x.hair.sides = { ...x.hair.sides, root: x.hair.back.root, tip: x.hair.back.tip };
          })}>Match all groups to the back</button>
        </Section>
      )}
      {id.bodyKind === 'adult' && (
        <Section title="Facial hair" defaultOpen={false}>
          {(['moustache', 'sideburns', 'beard'] as const).map((k) => (
            <div key={k}>
              <div className="subhead">{k}</div>
              <ColorRow label="Color" value={id.facialHair[k].color} onChange={(c) => st().commit((x) => { x.facialHair[k].color = c; })} />
              {(['length', 'bulk'] as const).map((p) => (
                <ValueSlider key={p} label={p[0].toUpperCase() + p.slice(1)} value={id.facialHair[k][p]} min={-100} max={100} step={1} format={(v) => `${Math.round(v)}`}
                  onBegin={() => st().beginEdit()}
                  onLive={(v) => st().editLive((x) => { x.facialHair[k][p] = v; })}
                  onCommit={() => st().endEdit()} />
              ))}
            </div>
          ))}
        </Section>
      )}
      {[...matGroups.entries()].map(([g, arr]) => (
        <Section key={g} title={g} count={arr.length}>
          {arr.map((c) => <ControlSlider key={c.id} id={c.id} />)}
        </Section>
      ))}
      <RenderSection />
      <div className="hint">Skin layers, makeup, markings, and scars are painted in the Appearance panel.</div>
    </>
  );
}

type NumKey = { [K in keyof RenderOverrides]-?: RenderOverrides[K] extends number | undefined ? K : never }[keyof RenderOverrides];

const RENDER_SLIDERS: { key: NumKey; label: string; min: number; max: number; step?: number }[] = [
  { key: 'shadeShift', label: 'Shade shift', min: -1, max: 1 },
  { key: 'toony', label: 'Toony', min: 0, max: 1 },
  { key: 'outline', label: 'Line width', min: 0, max: 3, step: 0.05 },
  { key: 'lineColorMix', label: 'Line tint', min: 0, max: 1 },
  { key: 'hull', label: 'Outline shell', min: 0, max: 4, step: 0.05 },
  { key: 'rimLit', label: 'Lit rim', min: 0, max: 1 },
  { key: 'rimShadow', label: 'Shadow rim', min: 0, max: 1 },
  { key: 'hatch', label: 'Hatching', min: 0, max: 1 },
  { key: 'grain', label: 'Grain', min: 0, max: 0.15, step: 0.005 },
  { key: 'diffusion', label: 'Diffusion', min: 0, max: 0.6 },
  { key: 'bloom', label: 'Bloom', min: 0, max: 1.5 },
  { key: 'light2Strength', label: 'Light 2', min: 0, max: 1 },
  { key: 'glowEyes', label: 'Glow eyes', min: 0, max: 1 },
  { key: 'gobo', label: 'Dappled light', min: 0, max: 1 },
  { key: 'dof', label: 'Depth of field', min: 0, max: 1 },
  { key: 'particles', label: 'Particles', min: 0, max: 1 },
];

/** Overrides for the current picture style. They stay on this machine and apply to every character in that style. */
function RenderSection() {
  const style = useStore((s) => s.identity.style);
  const overrides = useStore((s) => s.renderOverrides[style]);
  const st = useStore.getState;
  const s = resolveStyle(style, overrides);
  const current: Record<NumKey, number> = {
    shadeShift: s.shadeShift, toony: s.toony, outline: s.outline, lineColorMix: s.lineColorMix, hull: s.hull,
    rimLit: s.screenRim.lit, rimShadow: s.screenRim.shadow, hatch: s.hatch, grain: s.grain, diffusion: s.diffusion, bloom: s.bloom,
    light2Strength: s.light2.strength, glowEyes: s.glowEyes, gobo: s.gobo, dof: s.dof, particles: s.particles,
  };
  const changed = overrides ? Object.keys(overrides).length : 0;
  return (
    <Section title="Render" count={changed ? `${changed} changed` : undefined} defaultOpen={false}
      right={<button className="btn small" disabled={!changed} onClick={() => st().resetRenderOverrides(style)} title="Go back to the preset values">Reset to preset</button>}>
      <div className="hint" style={{ marginBottom: 6 }}>Adjusts the {STYLE_PRESETS[style].label} style for every character. Saved on this computer.</div>
      {RENDER_SLIDERS.map((r) => (
        <ValueSlider key={r.key} label={r.label} value={current[r.key]} min={r.min} max={r.max} step={r.step ?? 0.01}
          onLive={(v) => st().setRenderOverride(style, { [r.key]: v }, false)}
          onCommit={(v) => st().setRenderOverride(style, { [r.key]: v })} />
      ))}
      <div className="field">
        <label>Hatch mode</label>
        <Seg value={s.hatchMode} options={[{ id: 'surface', label: 'Surface', title: 'Strokes stick to the character as it moves' }, { id: 'screen', label: 'Screen', title: 'Strokes stay fixed on the screen' }]}
          onChange={(m) => st().setRenderOverride(style, { hatchMode: m })} />
      </div>
      <ColorRow label="Light 2 color" value={s.light2.color} onLive={(c) => st().setRenderOverride(style, { light2Color: c }, false)} onChange={(c) => st().setRenderOverride(style, { light2Color: c })}
        onEnd={() => st().setRenderOverride(style, {})} />
    </Section>
  );
}

function PhysicsTab() {
  const id = useStore((s) => s.identity);
  const st = useStore.getState;
  const L = id.looks;
  const channels: { key: keyof Identity['physics']; label: string; available: boolean; why: string }[] = [
    { key: 'hair', label: 'Hair', available: id.bodyKind === 'adult' || id.bodyKind === 'child', why: 'Hair sways with head motion.' },
    { key: 'cape', label: 'Cape', available: id.equipped.some((e) => e.slot === 'cape'), why: 'Put on a cape to use this.' },
    { key: 'tail', label: 'Tail', available: id.bodyKind === 'beast' || (L.tail ?? 'none') !== 'none', why: 'Choose a tail to use this.' },
    { key: 'wings', label: 'Wings', available: id.bodyKind === 'beast' || (L.wings ?? 'none') !== 'none', why: 'Choose wings to use this.' },
  ];
  return (
    <>
      <Note>Physics adds secondary motion in the viewport. It is part of the character, so it is saved.</Note>
      {channels.map((c) => {
        const ch = id.physics[c.key];
        return (
          <Section key={c.key} title={c.label} right={<Toggle label="On" checked={ch.enabled} onChange={(v) => st().commit((x) => { x.physics[c.key].enabled = v; })} />}>
            {!c.available && <div className="hint">{c.why}</div>}
            <ValueSlider label="Amount" value={ch.amount} disabled={!ch.enabled} onBegin={() => st().beginEdit()} onLive={(v) => st().editLive((x) => { x.physics[c.key].amount = v; })} onCommit={() => st().endEdit()} />
            <ValueSlider label="Stiffness" value={ch.stiffness} disabled={!ch.enabled} onBegin={() => st().beginEdit()} onLive={(v) => st().editLive((x) => { x.physics[c.key].stiffness = v; })} onCommit={() => st().endEdit()} />
          </Section>
        );
      })}
    </>
  );
}