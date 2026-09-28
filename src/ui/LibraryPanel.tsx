import { useEffect, useMemo, useState } from 'react';
import { hairSlotForPack, libraryTabFor, type ImportedPack } from '../library/importer';
import { chooseAndScanLibrary } from '../library/platform';
import { applyAge, applyArchetype, applyFullHairStyle, applyPresentation, clone, ensureRequiredGear, makeEquip, newCharacter } from '../model/character';
import { ACCESSORY_BY_ID, FACIAL_HAIR_STYLES, FULL_HAIR_STYLES, accessoriesFor, hairStylesFor, lookSlotsFor, type HairSlot } from '../model/looks';
import { BODY_POSES, CLIPS, POSE_LABELS, POSE_NAMES, VISEME_KEYS, PF_KEYS, type PerformanceState } from '../model/performance';
import { ARCHETYPES, BODY_PRESETS, HAIR_COLORS, HEAD_PRESETS, SKIN_TONES, STYLE_PRESETS } from '../model/presets';
import { BODY_KINDS, libraryOf, type BodyKind, type Identity } from '../model/types';
import { useStore } from '../state/store';
import { clearThumbnails, type ThumbFrame, type ThumbJob } from '../viewport/thumbnails';
import { Note } from './controls';
import { Icon } from './icons';
import { useThumbnail } from './useThumbnail';

export const LIB_CATEGORIES = ['Actor', 'Head', 'Body', 'Hair', 'Facial Hair', 'Elements', 'Outfit', 'Accessory', 'Material', 'Motion', 'Expression', 'Favorites'] as const;
type Cat = (typeof LIB_CATEGORIES)[number];

export function isCategoryDisabled(c: string, kind: BodyKind): boolean {
  return (c === 'Facial Hair' && kind !== 'adult') || (c === 'Hair' && (kind === 'robot' || kind === 'beast'));
}

interface Item {
  key: string;
  name: string;
  group: string;
  /** Icon shown when there is no render or swatch. */
  icon: string;
  swatch?: string;
  active?: boolean;
  tag?: string;
  info: string;
  apply: () => void;
  preview?: () => ThumbJob;
}

type Edit = (id: Identity) => Identity | void;

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

const valuesEdit = (values: Record<string, number>): Edit => (id) => {
  for (const [k, v] of Object.entries(values)) {
    if (v === 0) delete id.values[k];
    else id.values[k] = v;
  }
};

const HEAD_LOOKS = new Set(['muzzle', 'ears', 'pupil', 'fangs', 'whiskers', 'beak', 'mane', 'horns', 'frill', 'optic', 'antenna', 'robotMouth', 'beastHorns', 'beastCrest', 'beastEarFin', 'beastPupil']);
function lookFrame(slot: string): ThumbFrame {
  if (HEAD_LOOKS.has(slot)) return 'head';
  if (slot === 'hands') return 'hands';
  if (slot === 'feet' || slot === 'legs') return 'feet';
  return 'body';
}
function equipFrame(slot: string): ThumbFrame {
  if (/^(headgear|headwear|eyewear)$/.test(slot)) return 'head';
  if (slot === 'footwear') return 'feet';
  if (/^(robot_armor_arm|organic|weapon_r|weapon_l)$/.test(slot)) return 'hands';
  if (/^(armor|robot_armor_chest|panel_kit|collar)$/.test(slot)) return 'bust';
  return 'body';
}

function accessoryGroup(slot: string): string {
  if (/^(headgear|headwear|eyewear)$/.test(slot)) return 'Head and face';
  if (/^weapon_/.test(slot)) return 'Weapons';
  if (slot === 'footwear') return 'Footwear';
  if (/armor|panel_kit/.test(slot)) return 'Armor';
  return 'Gear';
}

function equipEdit(eid: string, def: { slot: string; colors: Record<string, string>; exclusive?: boolean }): Edit {
  return (id) => {
    if (def.exclusive ?? true) id.equipped = id.equipped.filter((e) => e.slot !== def.slot);
    id.equipped = id.equipped.filter((e) => e.id !== eid);
    id.equipped.push(makeEquip(eid, def));
    return ensureRequiredGear(id);
  };
}

function packPreview(p: ImportedPack): { edit: Edit; frame: ThumbFrame } | null {
  const tab = libraryTabFor(p);
  if (tab === 'Actor' || tab === 'Material') {
    const preset = p.preset as Partial<Identity> | null;
    if (!preset) return null;
    return {
      frame: 'body',
      edit: (id) => {
        if (preset.values) id.values = { ...id.values, ...preset.values };
        if (preset.looks) id.looks = { ...id.looks, ...preset.looks };
        if (preset.colors) id.colors = { ...id.colors, ...preset.colors };
      },
    };
  }
  if (!p.mainAsset || tab === 'Head' || tab === 'Motion') return null;
  if (tab === 'Body') return { frame: 'body', edit: (id) => { id.body = p.id; } };
  if (tab === 'Hair') {
    const slot = hairSlotForPack(p);
    return {
      frame: 'head',
      edit: (id) => {
        const piece = { id: `pack:${p.id}`, volume: 0, width: 0, length: 0, root: id.hair.back.root, tip: id.hair.back.tip, highlight: 0.6 };
        if (slot === 'extra') id.hair.extras = [...id.hair.extras.filter((x) => x.id !== piece.id), piece];
        else id.hair[slot] = piece;
      },
    };
  }
  return { frame: equipFrame(p.slot), edit: equipEdit(p.id, { slot: p.slot, colors: {}, exclusive: true }) };
}

function packItems(packs: ImportedPack[], tab: string, identity: Identity, job: (frame: ThumbFrame, edit?: Edit) => () => ThumbJob): Item[] {
  const lib = libraryOf(identity.bodyKind);
  return packs
    .filter((p) => p.library === lib && libraryTabFor(p) === tab)
    .map((p) => {
      const pv = packPreview(p);
      return {
        key: `pack:${p.id}`,
        name: p.displayName,
        group: 'Imported',
        icon: 'import',
        tag: 'pack',
        active: identity.body === p.id || identity.equipped.some((e) => e.id === p.id) || Object.values(identity.hair).flat().some((h) => (h as { id: string }).id === `pack:${p.id}`),
        info: `${p.category} in the ${p.library.replace('_', ' ')} library${p.mainAsset ? '' : '. No model file, only presets'}.`,
        apply: () => useStore.getState().applyPack(p),
        preview: pv ? job(pv.frame, pv.edit) : undefined,
      };
    });
}

/** Everything a thumbnail depends on besides the item itself. Sliders are left out; use Refresh after big shape edits. */
function baseSignature(id: Identity, packs: ImportedPack[]): string {
  const h = id.hair;
  return [
    id.bodyKind, id.archetype, id.style, id.body ?? '',
    Object.values(id.colors).join(','),
    [h.front.id, h.back.id, h.sides.id, ...h.extras.map((e) => e.id), h.back.root, h.back.tip].join(','),
    Object.values(id.looks).join(','),
    id.equipped.map((e) => e.id).join(','),
    packs.map((p) => p.id).join(','),
  ].join('|');
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
    const derive = (edit?: Edit): Identity => {
      if (!edit) return identity;
      const x = clone(identity);
      return edit(x) ?? x;
    };
    const job = (frame: ThumbFrame, edit?: Edit, p?: Partial<PerformanceState>) => () => ({ identity: derive(edit), frame, perf: { bodyPose: perf.bodyPose, ...p } });
    const commit = (edit: Edit) => () => st().commit(edit);
    switch (cat) {
      case 'Actor':
        for (const b of BODY_KINDS) {
          add({
            key: `new:${b.id}`, name: `New ${b.id === 'beast' ? 'dragon' : b.label.toLowerCase()}`, group: 'New character', icon: b.id === 'beast' ? 'dragon' : b.id === 'robot' ? 'robot' : b.id === 'child' ? 'child' : 'actor',
            info: `${b.hint} Opens dressed with the ${b.id === 'robot' ? 'Legends' : 'current'} style.`, active: kind === b.id, apply: () => st().newCharacter(b.id),
            preview: () => ({ identity: newCharacter(b.id, identity.style), frame: 'body', perf: { bodyPose: 'apose' } }),
          });
        }
        if (humanoid) {
          for (const a of ARCHETYPES) add({ key: `arch:${a.id}`, name: a.label, group: 'Species', icon: 'actor', active: identity.archetype === a.id, info: `${a.label} elements. Age, presentation, and your other sliders are kept, and every slider stays editable.`, apply: () => st().setArchetype(a.id), preview: job('bust', (x) => applyArchetype(x, a.id)) });
        }
        for (const f of family) add({ key: `fam:${f.label}`, name: f.label, group: 'Family', icon: 'family', info: `Open the ${f.label.toLowerCase()} member of the family you made.`, apply: () => st().loadIdentity(f.identity), preview: () => ({ identity: f.identity, frame: 'body' }) });
        out.push(...packItems(packs, 'Actor', identity, job));
        break;
      case 'Head':
        if (humanoid) for (const h of HEAD_PRESETS) add({ key: `head:${h.id}`, name: h.label, group: 'Head presets', icon: 'head', info: `Applies the ${h.label.toLowerCase()} head shape. Other sliders are kept.`, apply: commit(valuesEdit(h.values)), preview: job('head', valuesEdit(h.values)) });
        for (const b of baked.filter((x) => x.scope === 'Head')) add({ key: `baked:${b.name}`, name: b.name, group: 'Baked presets', icon: 'head', info: 'A preset you baked from the Morphs tab.', apply: commit(valuesEdit(b.values)), preview: job('head', valuesEdit(b.values)) });
        out.push(...packItems(packs, 'Head', identity, job));
        break;
      case 'Body':
        if (humanoid) for (const b of BODY_PRESETS) add({ key: `body:${b.id}`, name: b.label, group: 'Body presets', icon: 'body', info: `Applies the ${b.label.toLowerCase()} build.`, apply: commit(valuesEdit(b.values)), preview: job('body', valuesEdit(b.values)) });
        if (kind === 'adult') {
          for (const p of ['feminine', 'neutral', 'masculine'] as const) add({ key: `pres:${p}`, name: p[0].toUpperCase() + p.slice(1), group: 'Presentation', icon: 'body', info: 'Moves only the presentation sliders. Every one of them stays editable.', apply: () => st().setPresentation(p), preview: job('body', (x) => applyPresentation(x, p)) });
        }
        if (kind === 'adult' || kind === 'beast') {
          for (const a of [['youngAdult', 'Young adult'], ['adult', 'Adult'], ['old', 'Old']] as const) add({ key: `age:${a[0]}`, name: a[1], group: 'Age', icon: 'body', info: `Sets the age sliders to the ${a[1].toLowerCase()} preset.`, apply: () => st().setAge(a[0]), preview: job(kind === 'beast' ? 'body' : 'bust', (x) => applyAge(x, a[0])) });
        }
        for (const b of baked.filter((x) => x.scope === 'Body')) add({ key: `baked:${b.name}`, name: b.name, group: 'Baked presets', icon: 'body', info: 'A preset you baked from the Morphs tab.', apply: commit(valuesEdit(b.values)), preview: job('body', valuesEdit(b.values)) });
        out.push(...packItems(packs, 'Body', identity, job));
        break;
      case 'Hair':
        if (!humanoid) break;
        for (const f of FULL_HAIR_STYLES.filter((x) => kind !== 'child' || x.child)) add({ key: `fullhair:${f.id}`, name: f.label, group: 'Full styles', icon: 'hair', info: 'Sets front, back, sides, and extras at once. You can swap any group afterwards.', apply: () => st().applyFullHair(f.id), preview: job('hair', (x) => applyFullHairStyle(x, f.id)) });
        for (const slot of ['front', 'back', 'sides', 'extra'] as HairSlot[]) {
          const title = slot === 'front' ? 'Front' : slot === 'back' ? 'Back and length' : slot === 'sides' ? 'Sides' : 'Extras (stack)';
          for (const hs of hairStylesFor(slot, kind)) {
            const active = slot === 'extra' ? identity.hair.extras.some((e) => e.id === hs.id) : identity.hair[slot].id === hs.id;
            const toggle: Edit = (id) => {
              if (slot === 'extra') {
                const has = id.hair.extras.some((e) => e.id === hs.id);
                const tpl = id.hair.back;
                id.hair.extras = has ? id.hair.extras.filter((e) => e.id !== hs.id) : [...id.hair.extras, { id: hs.id, volume: 0, width: 0, length: 0, root: tpl.root, tip: tpl.tip, highlight: tpl.highlight }];
              } else id.hair[slot] = { ...id.hair[slot], id: hs.id };
            };
            const show: Edit = (id) => {
              if (slot === 'extra') {
                const tpl = id.hair.back;
                if (!id.hair.extras.some((e) => e.id === hs.id)) id.hair.extras = [...id.hair.extras, { id: hs.id, volume: 0, width: 0, length: 0, root: tpl.root, tip: tpl.tip, highlight: tpl.highlight }];
              } else id.hair[slot] = { ...id.hair[slot], id: hs.id };
            };
            add({
              key: `hair:${slot}:${hs.id}`, name: hs.label, group: title, icon: 'hair', active,
              info: slot === 'extra' ? 'Extras stack. Apply again to remove.' : `Replaces the ${slot} hair group.`,
              apply: commit(toggle),
              preview: job('hair', show),
            });
          }
        }
        for (const c of HAIR_COLORS) add({ key: `haircol:${c.id}`, name: c.label, group: 'Hair color', icon: 'palette', swatch: `linear-gradient(180deg, ${c.root}, ${c.tip})`, info: 'Root to tip color for every hair group.', apply: commit((id) => {
          for (const p of [id.hair.front, id.hair.back, id.hair.sides, ...id.hair.extras]) {
            p.root = c.root;
            p.tip = c.tip;
          }
          id.colors.brow = c.root;
        }) });
        out.push(...packItems(packs, 'Hair', identity, job));
        break;
      case 'Facial Hair':
        if (kind !== 'adult') break;
        for (const f of FACIAL_HAIR_STYLES) {
          const group = f.kind === 'moustache' ? 'Moustache' : f.kind === 'sideburns' ? 'Sideburns' : 'Beard';
          const edit: Edit = (id) => {
            id.facialHair[f.kind] = { ...id.facialHair[f.kind], id: f.id };
          };
          add({ key: `fh:${f.kind}:${f.id}`, name: f.label, group, icon: 'facialHair', active: identity.facialHair[f.kind].id === f.id, info: `Sets the ${f.kind}. Facial hair is adult only.`, apply: commit(edit), preview: job('head', edit) });
        }
        out.push(...packItems(packs, 'Facial Hair', identity, job));
        break;
      case 'Elements':
        for (const slot of lookSlotsFor(kind)) {
          for (const o of slot.options) {
            const edit: Edit = (id) => {
              id.looks[slot.slot] = o.id;
            };
            add({ key: `look:${slot.slot}:${o.id}`, name: o.label, group: slot.label, icon: 'elements', active: identity.looks[slot.slot] === o.id, info: `${slot.label}: ${o.label}. Mix with any other element. The matching sliders appear under Morphs.`, apply: () => st().setLook(slot.slot, o.id), preview: job(lookFrame(slot.slot), edit) });
          }
        }
        out.push(...packItems(packs, 'Elements', identity, job));
        break;
      case 'Outfit':
      case 'Accessory':
        for (const a of accessoriesFor(kind).filter((x) => x.category === cat)) {
          const on = identity.equipped.some((e) => e.id === a.id);
          add({
            key: `acc:${a.id}`, name: a.label, group: cat === 'Outfit' ? 'Outfits' : accessoryGroup(a.slot), icon: cat === 'Outfit' ? 'outfit' : 'accessory', active: on,
            info: `Slot ${a.slot}, socket ${a.socket}.${a.hides.length ? ` Hides ${a.hides.join(' and ')} while worn.` : ''} Apply to ${on ? 'take it off' : 'put it on'}.`,
            apply: () => {
              const e = st().identity.equipped.find((x) => x.id === a.id);
              if (e) st().unequip(e.uid);
              else st().equip(a.id);
            },
            preview: job(equipFrame(a.slot), on ? undefined : equipEdit(a.id, a)),
          });
        }
        out.push(...packItems(packs, cat, identity, job));
        break;
      case 'Material':
        for (const s of Object.values(STYLE_PRESETS)) add({ key: `style:${s.id}`, name: s.label, group: 'Picture style', icon: 'palette', swatch: `linear-gradient(135deg, ${s.background[0]}, ${s.background[1]})`, active: identity.style === s.id, info: s.hint, apply: () => st().setStyle(s.id) });
        if (humanoid) for (const t of SKIN_TONES) add({ key: `skin:${t.id}`, name: t.label, group: 'Skin tone', icon: 'palette', swatch: t.color, active: identity.colors.skin === t.color, info: 'Base skin color.', apply: () => st().setColor('skin', t.color) });
        out.push(...packItems(packs, 'Material', identity, job));
        break;
      case 'Motion':
        for (const p of BODY_POSES) add({ key: `pose:${p.id}`, name: p.label, group: 'Body pose', icon: 'pose', active: perf.bodyPose === p.id, info: 'Body pose for checking fit. Performance only, never saved into identity.', apply: () => st().setPerf({ bodyPose: p.id }), preview: job('body', undefined, { bodyPose: p.id }) });
        for (const c of CLIPS) add({ key: `clip:${c.id}`, name: c.label, group: 'Face clips', icon: 'play', active: perf.clip?.id === c.id, info: `${c.duration.toFixed(2)} seconds${c.loop ? ', loops' : ''}.`, apply: () => st().playClip(c.id) });
        out.push(...packItems(packs, 'Motion', identity, job));
        break;
      case 'Expression':
        for (const p of POSE_NAMES) add({ key: `expr:${p}`, name: POSE_LABELS[p], group: 'Expressions', icon: 'expression', active: perf.pose === p, info: 'Preview an expression. Edit its keys in the Face panel.', apply: () => st().setPerf({ pose: perf.pose === p ? null : p }), preview: job('head', undefined, { pose: p, poseWeight: 1 }) });
        for (const k of VISEME_KEYS) {
          const def = PF_KEYS.find((x) => x.key === k)!;
          add({ key: `vis:${k}`, name: def.label, group: 'Visemes', icon: 'expression', active: perf.viseme === k, info: 'Hold a viseme to check the mouth.', apply: () => st().setPerf({ viseme: perf.viseme === k ? null : k }), preview: job('head', undefined, { viseme: k }) });
        }
        break;
      case 'Favorites':
        break;
    }
    return { items: out, hiddenPacks };
  }, [cat, identity, packs, family, perf.bodyPose, perf.pose, perf.viseme, perf.clip]);
}

function usePersisted<T extends string | number>(key: string, initial: T): [T, (v: T) => void] {
  const [v, setV] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key);
      if (raw == null) return initial;
      return (typeof initial === 'number' ? Number(raw) : raw) as T;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(key, String(v));
    } catch {
      /* storage unavailable */
    }
  }, [key, v]);
  return [v, setV];
}

function Card({ item, sig, selected, fav, onSelect, onFav }: { item: Item; sig: string; selected: boolean; fav: boolean; onSelect: () => void; onFav: () => void }) {
  const [ref, url] = useThumbnail<HTMLDivElement>(item.preview ? `${item.key}#${sig}` : null, item.preview);
  const pending = !!item.preview && url === null;
  return (
    <div
      className={`card${selected ? ' sel' : ''}${item.active ? ' active' : ''}`}
      onClick={onSelect}
      onDoubleClick={() => item.apply()}
      title={`${item.name}. Double-click to apply.`}
    >
      <div ref={ref} className={`thumb${pending ? ' skel' : ''}${item.swatch ? ' swatch-tile' : ''}`} style={item.swatch ? { background: item.swatch } : undefined}>
        {url ? <img src={url} alt="" draggable={false} /> : !item.swatch && !pending && <Icon name={item.icon} size={22} stroke={1.5} />}
        {item.tag && <span className="pack-chip">{item.tag}</span>}
      </div>
      <div className="name">{item.name}</div>
      {item.active && <span className="check"><Icon name="check" size={10} stroke={3} /></span>}
      <button className={`fav${fav ? ' on' : ''}`} title={fav ? 'Remove from favorites' : 'Add to favorites'} onClick={(e) => {
        e.stopPropagation();
        onFav();
      }}><Icon name="star" size={12} stroke={fav ? 2.4 : 1.8} /></button>
    </div>
  );
}

export function LibraryPanel() {
  const ui = useStore((s) => s.ui);
  const identity = useStore((s) => s.identity);
  const packs = useStore((s) => s.packs);
  const favorites = useStore((s) => s.favorites);
  const cat = (LIB_CATEGORIES as readonly string[]).includes(ui.libraryCategory) ? (ui.libraryCategory as Cat) : 'Actor';
  const { items, hiddenPacks } = useItems(cat);
  const favItems = useFavoriteItems();
  const [sel, setSel] = useState<string | null>(null);
  const [view, setView] = usePersisted<'grid' | 'list'>('creator.libView', 'grid');
  const [thumb, setThumb] = usePersisted<number>('creator.thumbSize', 76);
  const q = ui.librarySearch.trim().toLowerCase();
  const list = (cat === 'Favorites' ? favItems : items).filter((i) => !q || i.name.toLowerCase().includes(q) || i.group.toLowerCase().includes(q));
  const groups = new Map<string, Item[]>();
  for (const i of list) groups.set(i.group, [...(groups.get(i.group) ?? []), i]);
  const selected = list.find((i) => i.key === sel) ?? null;
  const st = useStore.getState;
  const kind = identity.bodyKind;
  const bodyPose = useStore((s) => s.perf.bodyPose);
  const sig = useMemo(() => `${baseSignature(identity, packs)}|${bodyPose}`, [identity, packs, bodyPose]);

  return (
    <>
      <div className="panel-head">
        <span className="title">{cat}</span>
        <span className="sub">{kind === 'beast' ? 'full beast' : libraryOf(kind)} library</span>
        <span className="grow" />
        <button className="icon-btn" title="Render the thumbnails again" onClick={() => clearThumbnails()}><Icon name="refresh" /></button>
        <button className="icon-btn" title="Import a library folder" onClick={async () => {
          const scan = await chooseAndScanLibrary();
          if (scan) st().importScan(scan);
        }}><Icon name="import" /></button>
      </div>
      <div className="lib-tools">
        <div className="search">
          <Icon name="search" size={14} />
          <input placeholder={`Search ${cat.toLowerCase()}`} value={ui.librarySearch} onChange={(e) => st().setUI({ librarySearch: e.target.value })} />
          {ui.librarySearch && <button className="icon-btn sm" onClick={() => st().setUI({ librarySearch: '' })}><Icon name="close" size={13} /></button>}
        </div>
        <button className={`icon-btn${view === 'grid' ? ' on' : ''}`} title="Grid" onClick={() => setView('grid')}><Icon name="grid" /></button>
        <button className={`icon-btn${view === 'list' ? ' on' : ''}`} title="List" onClick={() => setView('list')}><Icon name="list" /></button>
      </div>
      {view === 'grid' && (
        <div className="lib-size" title="Thumbnail size">
          <Icon name="image" size={12} />
          <input className="rng" type="range" min={56} max={132} value={thumb} onChange={(e) => setThumb(Number(e.target.value))} />
          <Icon name="image" size={16} />
        </div>
      )}
      <div className="panel-body" style={{ ['--thumb' as string]: `${thumb}px` }}>
        {[...groups.entries()].map(([g, arr]) => (
          <div key={g}>
            <div className="group-title">
              <span>{g}</span>
              <span>{arr.length}</span>
            </div>
            <div className={`cards${view === 'list' ? ' list' : ''}`}>
              {arr.map((i) => (
                <Card key={i.key} item={i} sig={sig} selected={sel === i.key} fav={favorites.includes(`lib:${i.key}`)} onSelect={() => setSel(i.key)} onFav={() => st().toggleFavorite(`lib:${i.key}`)} />
              ))}
            </div>
          </div>
        ))}
        {list.length === 0 && (
          <div className="empty">
            <Icon name={cat === 'Favorites' ? 'star' : 'search'} size={28} stroke={1.4} />
            {cat === 'Favorites' ? 'Star any library item to keep it here.' : isCategoryDisabled(cat, kind) ? 'Not used by this body.' : q ? 'Nothing matches the search.' : 'Nothing here yet. Import a library folder to add more.'}
          </div>
        )}
        {hiddenPacks > 0 && <Note>{hiddenPacks} imported item{hiddenPacks === 1 ? '' : 's'} from other libraries are hidden. Humanoid, robot, and full beast items never mix.</Note>}
      </div>
      <div className="lib-foot">
        <div className="info">{selected ? <><b>{selected.name}</b>{selected.info}</> : 'Click an item to read about it. Double-click to apply.'}</div>
        <div className="row nowrap">
          <button className="btn primary grow" disabled={!selected} onClick={() => selected?.apply()}><Icon name="check" size={14} stroke={2.2} />Apply</button>
          {ACCESSORY_BY_ID[selected?.key.replace('acc:', '') ?? ''] && (
            <button className="btn" onClick={() => st().setUI({ rightPanel: 'modify', modifyTab: 'attribute' })}>Edit worn items</button>
          )}
        </div>
      </div>
    </>
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
