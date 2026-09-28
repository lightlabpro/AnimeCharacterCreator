import { useState } from 'react';
import { LAYER_CATEGORIES, MASKS, MATERIAL_ZONES, flatten, mergeDown, newLayer } from '../model/appearance';
import type { AppearanceLayer, Identity, LayerPage, MaterialZone } from '../model/types';
import { useStore } from '../state/store';
import { ColorRow, Note, Seg, ValueSlider } from './controls';
import { Icon } from './icons';

export function AppearancePanel() {
  const id = useStore((s) => s.identity);
  const st = useStore.getState;
  const [zone, setZone] = useState<MaterialZone>('head');
  const [page, setPage] = useState<LayerPage>('skin');
  const [sel, setSel] = useState<string | null>(null);

  if (id.bodyKind === 'robot') {
    return (
      <div className="panel-body">
        <Note>The robot has no skin layers. Paint, panel, joint, and glow colors are under Modify › Material, and wear is under Morphs.</Note>
      </div>
    );
  }
  const zones = MATERIAL_ZONES.filter((z) => id.bodyKind !== 'beast' || z.id === 'body' || z.id === 'head');
  const all = id.appearance[zone];
  const layers = all.map((l, i) => ({ l, i })).filter(({ l }) => l.page === page || l.category === 'merged');
  const cats = LAYER_CATEGORIES.filter((c) => c.page === page && c.zones.includes(zone) && (!c.adultOnly || id.bodyKind === 'adult'));

  const edit = (fn: (arr: AppearanceLayer[]) => AppearanceLayer[] | void) => (x: Identity) => {
    const arr = x.appearance[zone];
    const out = fn(arr);
    if (out) x.appearance[zone] = out;
  };
  const editLayer = (uid: string, fn: (l: AppearanceLayer) => void) => edit((arr) => {
    const l = arr.find((q) => q.uid === uid);
    if (l) fn(l);
  });
  const move = (index: number, dir: -1 | 1) => st().commit(edit((arr) => {
    const j = index + dir;
    if (j < 0 || j >= arr.length) return;
    [arr[index], arr[j]] = [arr[j], arr[index]];
  }));

  return (
    <>
      <div className="tabs">
        {zones.map((z) => <button key={z.id} className={zone === z.id ? 'on' : ''} onClick={() => setZone(z.id)}>{z.label}</button>)}
      </div>
      <div className="panel-body">
        <div className="row between nowrap" style={{ marginBottom: 6 }}>
          <Seg value={page} options={[{ id: 'skin', label: 'Skin' }, { id: 'makeup', label: 'Makeup' }]} onChange={setPage} />
          <span className="pill">{all.length} layers</span>
        </div>
        <div className="subhead">Add a layer</div>
        {cats.length === 0 ? <div className="hint">No {page} layers apply to this zone.</div> : (
          <div className="chips">
            {cats.map((c) => (
              <button key={c.id} className="chip" onClick={() => {
                const l = newLayer(c.id, zone);
                st().commit(edit((arr) => {
                  arr.push(l);
                }));
                setSel(l.uid);
              }}><Icon name="plus" size={12} stroke={2} />{c.label}</button>
            ))}
          </div>
        )}

        <div className="subhead" style={{ marginTop: 12 }}>Layers, top first</div>
        {layers.length === 0 && <div className="empty"><Icon name="layers" size={28} />No layers yet. Layers stack over the base color from Modify › Material.</div>}
        <div className="layers">
          {[...layers].reverse().map(({ l, i }) => (
            <div key={l.uid} className={`layer${sel === l.uid ? ' sel' : ''}${l.hidden ? ' hidden' : ''}`} onClick={() => setSel(l.uid)}>
              <div className="lt">
                <span className="chip-color" style={{ background: l.children ? 'linear-gradient(135deg,#888,#444)' : l.color }} />
                <span className="nm" title={l.name}>{l.name}{l.children ? ` (${l.children.length})` : ''}</span>
                <button className="icon-btn sm" title={l.hidden ? 'Show' : 'Hide'} onClick={(e) => {
                  e.stopPropagation();
                  st().commit(editLayer(l.uid, (q) => { q.hidden = !q.hidden; }));
                }}><Icon name={l.hidden ? 'eyeOff' : 'eye'} size={14} /></button>
                <button className="icon-btn sm" title="Move up" disabled={i === all.length - 1} onClick={(e) => { e.stopPropagation(); move(i, 1); }}><Icon name="chevronUp" size={14} /></button>
                <button className="icon-btn sm" title="Move down" disabled={i === 0} onClick={(e) => { e.stopPropagation(); move(i, -1); }}><Icon name="chevronDown" size={14} /></button>
                <button className="icon-btn sm" title="Merge into the layer below" disabled={i === 0} onClick={(e) => {
                  e.stopPropagation();
                  st().commit(edit((arr) => mergeDown(arr, i)));
                }}><Icon name="merge" size={14} /></button>
                <button className="icon-btn sm" title="Delete" onClick={(e) => {
                  e.stopPropagation();
                  st().commit(edit((arr) => arr.filter((q) => q.uid !== l.uid)));
                }}><Icon name="trash" size={14} /></button>
              </div>
              {sel === l.uid && (
                <div className="stack body" onClick={(e) => e.stopPropagation()}>
                  {!l.children && (
                    <ColorRow label="Color" value={l.color}
                      onBegin={() => st().beginEdit()} onEnd={() => st().endEdit()}
                      onLive={(c) => st().editLive(editLayer(l.uid, (q) => { q.color = c; }))}
                      onChange={(c) => st().commit(editLayer(l.uid, (q) => { q.color = c; }))} />
                  )}
                  <ValueSlider label="Opacity" value={l.opacity} min={0} max={1}
                    onBegin={() => st().beginEdit()}
                    onLive={(v) => st().editLive(editLayer(l.uid, (q) => { q.opacity = v; }))}
                    onCommit={() => st().endEdit()} />
                  {!l.children && (
                    <div className="field">
                      <label>Mask</label>
                      <select value={l.mask} onChange={(e) => st().commit(editLayer(l.uid, (q) => { q.mask = e.target.value; }))}>
                        {MASKS[zone].map((m) => <option key={m.id} value={m.id}>{m.label}</option>)}
                      </select>
                    </div>
                  )}
                  <div className="field">
                    <label>Name</label>
                    <input type="text" value={l.name} onFocus={() => st().beginEdit()} onBlur={() => st().endEdit()} onChange={(e) => st().editLive(editLayer(l.uid, (q) => { q.name = e.target.value; }))} />
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        {all.length > 1 && (
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn small" onClick={() => st().commit(edit((arr) => flatten(arr)))} title="Combine every visible layer in this zone into one. Hidden layers are dropped."><Icon name="merge" size={13} />Flatten zone</button>
            <button className="btn small danger" onClick={() => st().commit(edit(() => []))}><Icon name="trash" size={13} />Clear zone</button>
          </div>
        )}
      </div>
    </>
  );
}
