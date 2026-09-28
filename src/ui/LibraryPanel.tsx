import { useMemo, useState } from 'react';
import { libraryTabFor, type ImportedPack } from '../library/importer';
import { chooseAndScanLibrary } from '../library/platform';
import { ACCESSORY_BY_ID, FACIAL_HAIR_STYLES, FULL_HAIR_STYLES, accessoriesFor, hairStylesFor, lookSlotsFor, type HairSlot } from '../model/looks';
import { BODY_POSES, CLIPS, POSE_LABELS, POSE_NAMES, VISEME_KEYS, PF_KEYS } from '../model/performance';
import { ARCHETYPES, BODY_PRESETS, HAIR_COLORS, HEAD_PRESETS, SKIN_TONES, STYLE_PRESETS } from '../model/presets';
import { BODY_KINDS, libraryOf, type BodyKind, type Identity } from '../model/types';
import { useStore } from '../state/store';
import { thumbColor } from './controls';

export const LIB_CATEGORIES = ['Actor', 'Head', 'Body', 'Hair', 'Facial Hair', 'Elements', 'Outfit', 'Accessory', 'Material', 'Motion', 'Expression', 'Favorites'] as const;
type Cat = (typeof LIB_CATEGORIES)[number];

interface Item {
  key: string;
  name: string;
  group: string;
  glyph: string;
  color?: string;
  active?: boolean;
  tag?: string;
  info: string;
  apply: () => void;
}

const USER_PRESETS_KEY = 'creator.bakedPresets';
export function loadBaked(): { name: string; kind: BodyKind; scope: 'Head' | 'Body'; values: Record<string, number> }[] {
  try {
    return JSON.parse(localStorage.getItem(USER_PRESETS_KEY) ?? '[]');
  } catch {
    return [];
  }
}
export function saveBaked(list: ReturnType<typeof loadBaked>) {
  try {
    localStorage.setItem(USER_PRESETS_KEY, JSON.stringify(list));
  } catch {
    /* storage unavailable */
  }
}

function applyValues(values: Record<string, number>, scopeKeys?: string[]) {
  useStore.getState().commit((id) => {
    if (scopeKeys) for (const k of scopeKeys) delete id.values[k];
    for (const [k, v] of Object.entries(values)) {
      if (v === 0) delete id.values[k];
      else id.values[k] = v;
    }
  });
}

function initials(s: string) {
  return s.split(/[\s-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join('');
}

function packItems(packs: ImportedPack[], tab: string, identity: Identity): Item[] {
  const lib = libraryOf(identity.bodyKind);
  return packs
    .filter((p) => p.library === lib && libraryTabFor(p) === tab)
    .map((p) => ({
      key: `pack:${p.id}`,
      name: p.displayName,
      group: 'Imported',
      glyph: initials(p.displayName),
      tag: 'pack',
      active: identity.body === p.id || identity.equipped.some((e) => e.id === p.id) || Object.values(identity.hair).flat().some((h) => (h as { id: string }).id === `pack:${p.id}`),
      info: `${p.displayName}. ${p.category} in the ${p.library.replace('_', ' ')} library${p.mainAsset ? '' : '. No model file, only presets'}.`,
      apply: () => useStore.getState().applyPack(p),
    }));
}

function useItems(cat: Cat): { items: Item[]; hiddenPacks: number } {
  const identity = useStore((s) => s.identity);
  const packs = useStore((s) => s.packs);
  const family = useStore((s) => s.family);
  const perf = useStore((s) => s.perf);
  return useMemo(() => {
    const st = useStore.getState;
    const kind = identity.bodyKind;
    const humanoid = kind === 'adult' || kind === 'child';
    const out: Item[] = [];
    const add = (i: Item) => out.push(i);
    const lib = libraryOf(kind);
    const hiddenPacks = packs.filter((p) => p.library !== lib).length;
    const baked = loadBaked().filter((b) => b.kind === kind);
    switch (cat) {
      case 'Actor':
        for (const b of BODY_KINDS) add({ key: `new:${b.id}`, name: `New ${b.label.toLowerCase()}`, group: 'New character', glyph: b.id === 'beast' ? 'D' : b.id === 'robot' ? 'R' : b.id === 'child' ? 'C' : 'A', info: `${b.hint} Opens dressed with the ${b.id === 'robot' ? 'Legends' : 'current'} style.`, active: kind === b.id, apply: () => st().newCharacter(b.id) });
        if (humanoid) {
          for (const a of ARCHETYPES) add({ key: `arch:${a.id}`, name: a.label, group: 'Species', glyph: initials(a.label), active: identity.archetype === a.id, info: `${a.label} elements. Age, presentation, and your other sliders are kept, and every slider stays editable.`, apply: () => st().setArchetype(a.id) });
        }
        for (const f of family) add({ key: `fam:${f.label}`, name: f.label, group: 'Family', glyph: initials(f.label), info: `Open the ${f.label.toLowerCase()} member of the family you made.`, apply: () => st().loadIdentity(f.identity) });
        out.push(...packItems(packs, 'Actor', identity));
        break;
      case 'Head':
        if (humanoid) for (const h of HEAD_PRESETS) add({ key: `head:${h.id}`, name: h.label, group: 'Head presets', glyph: initials(h.label), info: `Applies the ${h.label.toLowerCase()} head shape. Other sliders are kept.`, apply: () => applyValues(h.values) });
        for (const b of baked.filter((x) => x.scope === 'Head')) add({ key: `baked:${b.name}`, name: b.name, group: 'Baked presets', glyph: 'B', info: 'A preset you baked from the Morphs tab.', apply: () => applyValues(b.values) });
        out.push(...packItems(packs, 'Head', identity));
        break;
      case 'Body':
        if (humanoid) for (const b of BODY_PRESETS) add({ key: `body:${b.id}`, name: b.label, group: 'Body presets', glyph: initials(b.label), info: `Applies the ${b.label.toLowerCase()} build.`, apply: () => applyValues(b.values) });
        if (kind === 'adult') {
          for (const p of ['feminine', 'neutral', 'masculine'] as const) add({ key: `pres:${p}`, name: p[0].toUpperCase() + p.slice(1), group: 'Presentation', glyph: p[0].toUpperCase(), info: 'Moves only the presentation sliders. Every one of them stays editable.', apply: () => st().setPresentation(p) });
        }
        if (kind === 'adult' || kind === 'beast') {
          for (const a of [['youngAdult', 'Young adult'], ['adult', 'Adult'], ['old', 'Old']] as const) add({ key: `age:${a[0]}`, name: a[1], group: 'Age', glyph: a[1][0], info: `Sets the age sliders to the ${a[1].toLowerCase()} preset.`, apply: () => st().setAge(a[0]) });
        }
        for (const b of baked.filter((x) => x.scope === 'Body')) add({ key: `baked:${b.name}`, name: b.name, group: 'Baked presets', glyph: 'B', info: 'A preset you baked from the Morphs tab.', apply: () => applyValues(b.values) });
        out.push(...packItems(packs, 'Body', identity));
        break;
      case 'Hair':
        if (!humanoid) break;
        for (const f of FULL_HAIR_STYLES.filter((x) => kind !== 'child' || x.child)) add({ key: `fullhair:${f.id}`, name: f.label, group: 'Full styles', glyph: initials(f.label), info: `Sets front, back, sides, and extras at once. You can swap any group afterwards.`, apply: () => st().applyFullHair(f.id) });
        for (const slot of ['front', 'back', 'sides', 'extra'] as HairSlot[]) {
          const title = slot === 'front' ? 'Front' : slot === 'back' ? 'Back and length' : slot === 'sides' ? 'Sides' : 'Extras (stack)';
          for (const hs of hairStylesFor(slot, kind)) {
            const active = slot === 'extra' ? identity.hair.extras.some((e) => e.id === hs.id) : identity.hair[slot].id === hs.id;
            add({
              key: `hair:${slot}:${hs.id}`, name: hs.label, group: title, glyph: initials(hs.label), active,
              info: slot === 'extra' ? 'Extras stack. Double-click again to remove.' : `Replaces the ${slot} hair group.`,
              apply: () => st().commit((id) => {
                if (slot === 'extra') {
                  const has = id.hair.extras.some((e) => e.id === hs.id);
                  const tpl = id.hair.back;
                  id.hair.extras = has ? id.hair.extras.filter((e) => e.id !== hs.id) : [...id.hair.extras, { id: hs.id, volume: 0, width: 0, length: 0, root: tpl.root, tip: tpl.tip, highlight: tpl.highlight }];
                } else id.hair[slot] = { ...id.hair[slot], id: hs.id };
              }),
            });
          }
        }
        for (const c of HAIR_COLORS) add({ key: `haircol:${c.id}`, name: c.label, group: 'Hair color', glyph: '', color: `linear-gradient(180deg, ${c.root}, ${c.tip})`, info: 'Root to tip color for every hair group.', apply: () => st().commit((id) => {
          for (const p of [id.hair.front, id.hair.back, id.hair.sides, ...id.hair.extras]) {
            p.root = c.root;
            p.tip = c.tip;
          }
          id.colors.brow = c.root;
        }) });
        out.push(...packItems(packs, 'Hair', identity));
        break;
      case 'Facial Hair':
        if (kind !== 'adult') break;
        for (const f of FACIAL_HAIR_STYLES) {
          const group = f.kind === 'moustache' ? 'Moustache' : f.kind === 'sideburns' ? 'Sideburns' : 'Beard';
          add({ key: `fh:${f.kind}:${f.id}`, name: f.label, group, glyph: initials(f.label), active: identity.facialHair[f.kind].id === f.id, info: `Sets the ${f.kind}. Facial hair is adult only.`, apply: () => st().commit((id) => {
            id.facialHair[f.kind] = { ...id.facialHair[f.kind], id: f.id };
          }) });
        }
        out.push(...packItems(packs, 'Facial Hair', identity));
        break;
      case 'Elements':
        for (const slot of lookSlotsFor(kind)) {
          for (const o of slot.options) add({ key: `look:${slot.slot}:${o.id}`, name: o.label, group: slot.label, glyph: initials(o.label), active: identity.looks[slot.slot] === o.id, info: `${slot.label}: ${o.label}. Mix with any other element. The matching sliders appear under Morphs.`, apply: () => st().setLook(slot.slot, o.id) });
        }
        out.push(...packItems(packs, 'Elements', identity));
        break;
      case 'Outfit':
      case 'Accessory':
        for (const a of accessoriesFor(kind).filter((x) => x.category === cat)) {
          const on = identity.equipped.some((e) => e.id === a.id);
          add({
            key: `acc:${a.id}`, name: a.label, group: cat === 'Outfit' ? 'Outfits' : a.slot.replace(/_/g, ' '), glyph: initials(a.label), active: on,
            info: `${a.label}. Slot ${a.slot}, socket ${a.socket}.${a.hides.length ? ` Hides ${a.hides.join(' and ')} while worn.` : ''} Double-click to ${on ? 'take off' : 'put on'}.`,
            apply: () => {
              const e = st().identity.equipped.find((x) => x.id === a.id);
              if (e) st().unequip(e.uid);
              else st().equip(a.id);
            },
          });
        }
        out.push(...packItems(packs, cat, identity));
        break;
      case 'Material':
        for (const s of Object.values(STYLE_PRESETS)) add({ key: `style:${s.id}`, name: s.label, group: 'Picture style', glyph: s.label[0], color: `linear-gradient(135deg, ${s.background[0]}, ${s.background[1]})`, active: identity.style === s.id, info: s.hint, apply: () => st().setStyle(s.id) });
        if (humanoid) for (const t of SKIN_TONES) add({ key: `skin:${t.id}`, name: t.label, group: 'Skin tone', glyph: '', color: t.color, active: identity.colors.skin === t.color, info: 'Base skin color.', apply: () => st().setColor('skin', t.color) });
        out.push(...packItems(packs, 'Material', identity));
        break;
      case 'Motion':
        for (const p of BODY_POSES) add({ key: `pose:${p.id}`, name: p.label, group: 'Body pose', glyph: initials(p.label), active: perf.bodyPose === p.id, info: 'Body pose for checking fit. Performance only, never saved into identity.', apply: () => st().setPerf({ bodyPose: p.id }) });
        for (const c of CLIPS) add({ key: `clip:${c.id}`, name: c.label, group: 'Face clips', glyph: '▶', active: perf.clip?.id === c.id, info: `${c.label}, ${c.duration.toFixed(2)} seconds${c.loop ? ', loops' : ''}.`, apply: () => st().playClip(c.id) });
        out.push(...packItems(packs, 'Motion', identity));
        break;
      case 'Expression':
        for (const p of POSE_NAMES) add({ key: `expr:${p}`, name: POSE_LABELS[p], group: 'Expressions', glyph: initials(POSE_LABELS[p]), active: perf.pose === p, info: 'Preview an expression. Edit its keys in the Face panel.', apply: () => st().setPerf({ pose: perf.pose === p ? null : p }) });
        for (const k of VISEME_KEYS) {
          const def = PF_KEYS.find((x) => x.key === k)!;
          add({ key: `vis:${k}`, name: def.label, group: 'Visemes', glyph: def.label.slice(0, 2), active: perf.viseme === k, info: 'Hold a viseme to check the mouth.', apply: () => st().setPerf({ viseme: perf.viseme === k ? null : k }) });
        }
        break;
      case 'Favorites':
        break;
    }
    return { items: out, hiddenPacks };
  }, [cat, identity, packs, family, perf]);
}

export function LibraryPanel() {
  const ui = useStore((s) => s.ui);
  const identity = useStore((s) => s.identity);
  const favorites = useStore((s) => s.favorites);
  const cat = (LIB_CATEGORIES as readonly string[]).includes(ui.libraryCategory) ? (ui.libraryCategory as Cat) : 'Actor';
  const { items, hiddenPacks } = useItems(cat);
  const favItems = useFavoriteItems();
  const [sel, setSel] = useState<string | null>(null);
  const q = ui.librarySearch.trim().toLowerCase();
  const list = (cat === 'Favorites' ? favItems : items).filter((i) => !q || i.name.toLowerCase().includes(q) || i.group.toLowerCase().includes(q));
  const groups = new Map<string, Item[]>();
  for (const i of list) groups.set(i.group, [...(groups.get(i.group) ?? []), i]);
  const selected = list.find((i) => i.key === sel) ?? null;
  const st = useStore.getState;
  const kind = identity.bodyKind;
  const disabledCat = (c: Cat) => (c === 'Facial Hair' && kind !== 'adult') || (c === 'Hair' && (kind === 'robot' || kind === 'beast'));

  return (
    <aside className="panel left">
      <div className="panel-head">
        Library <span className="sub">{identity.bodyKind === 'beast' ? 'full beast' : libraryOf(identity.bodyKind)}</span>
        <span className="grow" />
        <button className="btn small" onClick={async () => {
          const scan = await chooseAndScanLibrary();
          if (scan) st().importScan(scan);
        }} title="Choose the library root or one category folder">Import…</button>
      </div>
      <div className="lib-cats">
        {LIB_CATEGORIES.map((c) => (
          <button key={c} className={c === cat ? 'on' : ''} disabled={disabledCat(c)} onClick={() => st().setUI({ libraryCategory: c })}>
            {c}
          </button>
        ))}
      </div>
      <div style={{ padding: '8px 10px 0' }}>
        <div className="search">
          <span style={{ color: 'var(--faint)' }}>⌕</span>
          <input placeholder={`Search ${cat.toLowerCase()}`} value={ui.librarySearch} onChange={(e) => st().setUI({ librarySearch: e.target.value })} />
          {ui.librarySearch && <button className="icon-btn" onClick={() => st().setUI({ librarySearch: '' })}>✕</button>}
        </div>
      </div>
      <div className="panel-body">
        {[...groups.entries()].map(([g, arr]) => (
          <div key={g}>
            <div className="group-title">
              <span>{g}</span>
              <span>{arr.length}</span>
            </div>
            <div className="cards">
              {arr.map((i) => {
                const fav = favorites.includes(`lib:${i.key}`);
                return (
                  <div
                    key={i.key}
                    className={`card${sel === i.key ? ' sel' : ''}${i.active ? ' active' : ''}`}
                    onClick={() => setSel(i.key)}
                    onDoubleClick={() => i.apply()}
                    title={`${i.name}. Double-click to apply.`}
                  >
                    {i.tag && <span className="tag">{i.tag}</span>}
                    <div className="thumb" style={{ background: i.color ?? thumbColor(i.group + i.name) }}>{i.glyph}</div>
                    <div className="name">{i.name}</div>
                    <button className={`fav${fav ? ' on' : ''}`} onClick={(e) => {
                      e.stopPropagation();
                      st().toggleFavorite(`lib:${i.key}`);
                    }}>{fav ? '★' : '☆'}</button>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
        {list.length === 0 && (
          <div className="empty">
            {cat === 'Favorites' ? 'Star any library item to keep it here.' : disabledCat(cat) ? 'Not used by this body.' : q ? 'Nothing matches the search.' : 'Nothing here yet. Import a library folder to add more.'}
          </div>
        )}
        {hiddenPacks > 0 && <div className="note">{hiddenPacks} imported item{hiddenPacks === 1 ? '' : 's'} from other libraries are hidden. Humanoid, robot, and full beast items never mix.</div>}
      </div>
      <div className="lib-foot">
        <div className="info">{selected ? selected.info : 'Click an item to read about it. Double-click to apply.'}</div>
        <div className="row">
          <button className="btn primary grow" disabled={!selected} onClick={() => selected?.apply()}>Apply</button>
          {ACCESSORY_BY_ID[selected?.key.replace('acc:', '') ?? ''] && (
            <button className="btn" onClick={() => st().setUI({ rightPanel: 'modify', modifyTab: 'attribute' })}>Edit worn items</button>
          )}
        </div>
      </div>
    </aside>
  );
}

/** Favorites across every category, built from the same item lists. */
function useFavoriteItems(): Item[] {
  const favorites = useStore((s) => s.favorites);
  const a = useItems('Actor').items;
  const b = useItems('Head').items;
  const c = useItems('Body').items;
  const d = useItems('Hair').items;
  const e = useItems('Facial Hair').items;
  const f = useItems('Elements').items;
  const g = useItems('Outfit').items;
  const h = useItems('Accessory').items;
  const i = useItems('Material').items;
  const j = useItems('Motion').items;
  const k = useItems('Expression').items;
  return useMemo(() => [...a, ...b, ...c, ...d, ...e, ...f, ...g, ...h, ...i, ...j, ...k].filter((x) => favorites.includes(`lib:${x.key}`)), [a, b, c, d, e, f, g, h, i, j, k, favorites]);
}
