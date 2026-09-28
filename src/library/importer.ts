import type { LibraryTag } from '../model/types';

export interface ScannedFile {
  path: string;
  text?: string;
}

export interface ScanResult {
  root: string;
  files: ScannedFile[];
  assets: ScannedFile[];
  /** True when absolute paths are unavailable, so the library tree above the chosen folder is unknown. */
  relativeOnly?: boolean;
}

export interface ImportedPack {
  id: string;
  displayName: string;
  library: LibraryTag;
  slot: string;
  socket: string | null;
  category: string;
  folder: string;
  mainAsset: string | null;
  assets: string[];
  preset: unknown | null;
  raw: Record<string, unknown>;
}

export interface ImportReport {
  folder: string;
  kind: 'root' | 'category';
  added: { id: string; name: string; library: LibraryTag; category: string }[];
  replaced: string[];
  skipped: { item: string; reason: string }[];
  notes: string[];
}

export const LIBRARY_TAGS: LibraryTag[] = ['humanoid', 'robot', 'full_beast'];

export const CATEGORY_ROOTS: Record<LibraryTag, string[]> = {
  humanoid: ['bodies', 'morphs', 'hair', 'facial_hair', 'elements', 'outfits', 'accessories', 'materials', 'motions', 'presets'],
  robot: ['body', 'parts', 'materials', 'motions'],
  full_beast: ['body', 'elements', 'accessories', 'materials', 'motions', 'presets'],
};

const SOCKETED_CATEGORIES = ['hair', 'facial_hair', 'elements', 'accessories', 'parts'];

function norm(p: string): string {
  return p.replace(/\\/g, '/').replace(/\/+$/, '');
}

function dirname(p: string): string {
  const n = norm(p);
  const i = n.lastIndexOf('/');
  return i < 0 ? '' : n.slice(0, i);
}

function basename(p: string): string {
  const n = norm(p);
  return n.slice(n.lastIndexOf('/') + 1);
}

/** Finds which library tree a folder sits in, and the category path below it. */
export function locateInTree(folder: string): { tree: LibraryTag | null; category: string } {
  const segs = norm(folder).split('/');
  for (let i = segs.length - 1; i >= 0; i -= 1) {
    if ((LIBRARY_TAGS as string[]).includes(segs[i])) {
      return { tree: segs[i] as LibraryTag, category: segs.slice(i + 1, segs.length).join('/') };
    }
  }
  return { tree: null, category: '' };
}

function categoryFromPackFolder(folder: string, tree: LibraryTag): string {
  const { category } = locateInTree(folder);
  const parts = category.split('/').filter(Boolean);
  if (parts.length === 0) return '';
  const root = parts[0];
  if (!CATEGORY_ROOTS[tree].includes(root)) return root;
  if (parts.length >= 3) return `${parts[0]}/${parts[1]}`;
  if (parts.length === 2 && ['hair', 'elements', 'accessories', 'bodies'].includes(root)) return parts.join('/');
  return root;
}

function guessCategoryFromSlot(slot: string, library: LibraryTag): string {
  const s = slot.toLowerCase();
  if (library === 'humanoid') {
    if (s.startsWith('hair_')) return `hair/${s.replace('hair_', '').replace('side', 'sides').replace('sidess', 'sides').replace('extra', 'extras').replace('extrass', 'extras')}`;
    if (s.startsWith('facial') || ['moustache', 'beard', 'sideburns'].includes(s)) return 'facial_hair';
    if (s.startsWith('body')) return s.includes('child') ? 'bodies/child' : 'bodies/adult';
    if (s.startsWith('element_')) return `elements/${s.replace('element_', '')}`;
    if (s === 'outfit') return 'outfits';
    if (s === 'material') return 'materials';
    if (s === 'motion') return 'motions';
    if (s === 'preset') return 'presets';
    return 'accessories';
  }
  if (library === 'robot') return s.startsWith('body') ? 'body' : s === 'material' ? 'materials' : s === 'motion' ? 'motions' : 'parts';
  return s.startsWith('body') ? 'body' : s === 'material' ? 'materials' : s === 'motion' ? 'motions' : s === 'preset' ? 'presets' : s.startsWith('element') ? 'elements' : 'accessories';
}

function safeParse(text: string | undefined): { ok: true; value: unknown } | { ok: false; error: string } {
  if (text === undefined) return { ok: false, error: 'file could not be read' };
  try {
    return { ok: true, value: JSON.parse(text) };
  } catch (e) {
    return { ok: false, error: (e as Error).message };
  }
}

export function importLibrary(scan: ScanResult, existingIds: Set<string> = new Set()): { packs: ImportedPack[]; report: ImportReport } {
  const root = norm(scan.root);
  const rootLoc = locateInTree(root);
  const hasTreeChildren = scan.files.some((f) => {
    const rel = norm(f.path).slice(root.length + 1);
    const first = rel.split('/')[0];
    return (LIBRARY_TAGS as string[]).includes(first);
  });
  const kind: ImportReport['kind'] = rootLoc.tree === null && hasTreeChildren ? 'root' : 'category';
  const report: ImportReport = { folder: scan.root, kind, added: [], replaced: [], skipped: [], notes: [] };
  const packs: ImportedPack[] = [];

  const manifestFile = scan.files.find((f) => basename(f.path) === 'manifest.json' && dirname(f.path) === root);
  const manifestEntries = new Map<string, { id?: string; library?: string; folder?: string }>();
  if (manifestFile) {
    const parsed = safeParse(manifestFile.text);
    if (!parsed.ok) {
      report.skipped.push({ item: 'manifest.json', reason: `not valid JSON (${parsed.error})` });
    } else {
      const list = (parsed.value as { packs?: unknown })?.packs;
      if (!Array.isArray(list)) {
        report.notes.push('manifest.json has no "packs" list, so each pack.json was read on its own.');
      } else {
        for (const entry of list as { id?: string; library?: string; folder?: string }[]) {
          if (!entry || typeof entry !== 'object' || !entry.folder) {
            report.skipped.push({ item: `manifest entry ${JSON.stringify(entry)}`, reason: 'entry has no folder' });
            continue;
          }
          const abs = norm(`${root}/${entry.folder}`);
          manifestEntries.set(abs, entry);
        }
      }
    }
  } else if (kind === 'root') {
    report.notes.push('No manifest.json at the library root. Each pack.json was read on its own.');
  }

  const packFiles = scan.files.filter((f) => basename(f.path) === 'pack.json');
  const seen = new Set<string>();
  const listedFolders = new Set<string>();

  for (const file of packFiles) {
    const folder = dirname(file.path);
    const label = folder.slice(root.length + 1) || basename(folder);
    const parsed = safeParse(file.text);
    if (!parsed.ok) {
      report.skipped.push({ item: label, reason: `pack.json is not valid JSON (${parsed.error})` });
      continue;
    }
    const raw = parsed.value as Record<string, unknown>;
    const missing = ['id', 'display_name', 'library', 'slot'].filter((k) => typeof raw[k] !== 'string' || !(raw[k] as string).trim());
    if (missing.length) {
      report.skipped.push({ item: label, reason: `pack.json is missing ${missing.join(', ')}` });
      continue;
    }
    const library = raw.library as string;
    if (!(LIBRARY_TAGS as string[]).includes(library)) {
      report.skipped.push({ item: label, reason: `library "${library}" is not humanoid, robot, or full_beast` });
      continue;
    }
    const tag = library as LibraryTag;
    const loc = locateInTree(folder);
    let category: string;
    if (loc.tree) {
      if (loc.tree !== tag) {
        report.skipped.push({ item: label, reason: `pack.json says ${tag} but the folder is inside the ${loc.tree} tree` });
        continue;
      }
      category = categoryFromPackFolder(folder, tag);
      const top = category.split('/')[0];
      if (!CATEGORY_ROOTS[tag].includes(top)) {
        report.skipped.push({ item: label, reason: `"${top || '(tree root)'}" is not a ${tag} category folder` });
        continue;
      }
    } else if (scan.relativeOnly) {
      category = guessCategoryFromSlot(raw.slot as string, tag);
      report.notes.push(`${label}: the folder tree above the chosen folder is not visible here, so the pack's own library tag (${tag}) was used.`);
    } else {
      report.skipped.push({ item: label, reason: 'the folder is not inside a humanoid, robot, or full_beast tree' });
      continue;
    }

    const manifestEntry = manifestEntries.get(folder);
    if (manifestEntry) {
      listedFolders.add(folder);
      if (manifestEntry.library && manifestEntry.library !== tag) {
        report.skipped.push({ item: label, reason: `manifest.json lists it as ${manifestEntry.library} but pack.json says ${tag}` });
        continue;
      }
      if (manifestEntry.id && manifestEntry.id !== raw.id) {
        report.notes.push(`${label}: manifest id "${manifestEntry.id}" differs from pack id "${raw.id}". The pack id was used.`);
      }
    } else if (manifestEntries.size > 0) {
      report.notes.push(`${label} is not listed in manifest.json. It was added anyway.`);
    }

    const id = raw.id as string;
    if (seen.has(id)) {
      report.skipped.push({ item: label, reason: `another pack in this import already uses the id "${id}"` });
      continue;
    }
    seen.add(id);

    const socket = typeof raw.socket === 'string' && raw.socket ? (raw.socket as string) : null;
    if (!socket && SOCKETED_CATEGORIES.includes(category.split('/')[0])) {
      report.notes.push(`${label} has no socket. It will attach at the default point for its slot.`);
    }

    const assets = scan.assets.filter((a) => dirname(a.path) === folder).map((a) => a.path);
    const mainAsset = assets.find((a) => /\.glb$/i.test(a)) ?? assets.find((a) => /\.gltf$/i.test(a)) ?? null;
    let preset: unknown = null;
    const presetFile = scan.assets.find((a) => dirname(a.path) === folder && /\.json$/i.test(a.path) && !/(pack|manifest)\.json$/i.test(a.path) && !/\.gltf$/i.test(a.path));
    if (presetFile?.text) {
      const p = safeParse(presetFile.text);
      if (p.ok) preset = p.value;
    }
    if (!mainAsset && !preset && !['materials', 'motions', 'presets', 'morphs'].includes(category.split('/')[0])) {
      report.notes.push(`${label} has no .glb or .gltf file. It is listed, and the built-in placeholder is shown until a mesh is added.`);
    }

    if (existingIds.has(id)) report.replaced.push(id);
    packs.push({
      id,
      displayName: raw.display_name as string,
      library: tag,
      slot: raw.slot as string,
      socket,
      category,
      folder,
      mainAsset,
      assets,
      preset,
      raw,
    });
    report.added.push({ id, name: raw.display_name as string, library: tag, category });
  }

  for (const [folder, entry] of manifestEntries) {
    if (!listedFolders.has(folder) && !packFiles.some((f) => dirname(f.path) === folder)) {
      report.skipped.push({ item: entry.id ?? entry.folder ?? folder, reason: 'listed in manifest.json but the folder has no pack.json' });
    }
  }

  if (packFiles.length === 0) {
    report.notes.push('No pack.json files were found in this folder.');
  }
  return { packs, report };
}

/** Maps a pack category to the left library tab where it appears. */
export function libraryTabFor(pack: ImportedPack): string {
  const top = pack.category.split('/')[0];
  switch (top) {
    case 'bodies':
    case 'body':
      return 'Body';
    case 'morphs':
      return 'Head';
    case 'hair':
      return 'Hair';
    case 'facial_hair':
      return 'Facial Hair';
    case 'elements':
      return 'Elements';
    case 'outfits':
      return 'Outfit';
    case 'accessories':
    case 'parts':
      return 'Accessory';
    case 'materials':
      return 'Material';
    case 'motions':
      return 'Motion';
    case 'presets':
      return 'Actor';
    default:
      return 'Accessory';
  }
}

export function hairSlotForPack(pack: ImportedPack): 'front' | 'back' | 'sides' | 'extra' {
  const sub = pack.category.split('/')[1] ?? pack.slot.replace('hair_', '');
  if (sub.startsWith('front')) return 'front';
  if (sub.startsWith('side')) return 'sides';
  if (sub.startsWith('extra')) return 'extra';
  return 'back';
}
