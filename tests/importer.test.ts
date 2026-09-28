import { describe, expect, it } from 'vitest';
import { hairSlotForPack, importLibrary, libraryTabFor, locateInTree, type ScanResult } from '../src/library/importer';

const pack = (id: string, library: string, slot: string, extra: Record<string, unknown> = {}) =>
  JSON.stringify({ id, display_name: id.replace(/_/g, ' '), library, slot, ...extra });

describe('importer', () => {
  it('reads a library root with all three trees', () => {
    const root = 'C:/lib';
    const scan: ScanResult = {
      root,
      files: [
        { path: `${root}/humanoid/hair/front/bangs_a/pack.json`, text: pack('bangs_a', 'humanoid', 'hair_front', { socket: 'SOC-HairFront' }) },
        { path: `${root}/robot/parts/fin/pack.json`, text: pack('fin', 'robot', 'antenna', { socket: 'SOC-Antenna' }) },
        { path: `${root}/full_beast/accessories/collar/pack.json`, text: pack('collar', 'full_beast', 'collar', { socket: 'SOC-Neck' }) },
      ],
      assets: [{ path: `${root}/humanoid/hair/front/bangs_a/bangs_a.glb` }],
    };
    const { packs, report } = importLibrary(scan);
    expect(report.kind).toBe('root');
    expect(packs.map((p) => p.id).sort()).toEqual(['bangs_a', 'collar', 'fin']);
    const bangs = packs.find((p) => p.id === 'bangs_a')!;
    expect(bangs.category).toBe('hair/front');
    expect(bangs.mainAsset).toMatch(/bangs_a\.glb$/);
    expect(libraryTabFor(bangs)).toBe('Hair');
    expect(hairSlotForPack(bangs)).toBe('front');
    expect(report.skipped).toEqual([]);
  });

  it('reads a single category folder inside a tree', () => {
    const root = 'C:/lib/humanoid/outfits';
    const scan: ScanResult = {
      root,
      files: [{ path: `${root}/scout/pack.json`, text: pack('scout', 'humanoid', 'outfit') }],
      assets: [{ path: `${root}/scout/scout.glb` }],
    };
    const { packs, report } = importLibrary(scan);
    expect(report.kind).toBe('category');
    expect(packs).toHaveLength(1);
    expect(packs[0].category).toBe('outfits');
    expect(libraryTabFor(packs[0])).toBe('Outfit');
  });

  it('skips a pack whose library tag does not match its tree', () => {
    const root = 'C:/lib';
    const scan: ScanResult = {
      root,
      files: [
        { path: `${root}/humanoid/accessories/visor/pack.json`, text: pack('visor', 'robot', 'head') },
        { path: `${root}/robot/parts/arm/pack.json`, text: pack('arm', 'robot', 'arm') },
      ],
      assets: [],
    };
    const { packs, report } = importLibrary(scan);
    expect(packs.map((p) => p.id)).toEqual(['arm']);
    expect(report.skipped).toHaveLength(1);
    expect(report.skipped[0].reason).toMatch(/robot.*humanoid tree/);
  });

  it('skips packs with missing fields, bad JSON, bad tags, and duplicate ids', () => {
    const root = 'C:/lib/humanoid/accessories';
    const scan: ScanResult = {
      root,
      files: [
        { path: `${root}/a/pack.json`, text: JSON.stringify({ id: 'a', library: 'humanoid' }) },
        { path: `${root}/b/pack.json`, text: '{ nope' },
        { path: `${root}/c/pack.json`, text: pack('c', 'alien', 'hat') },
        { path: `${root}/d/pack.json`, text: pack('dup', 'humanoid', 'hat') },
        { path: `${root}/e/pack.json`, text: pack('dup', 'humanoid', 'hat') },
      ],
      assets: [],
    };
    const { packs, report } = importLibrary(scan);
    expect(packs.map((p) => p.id)).toEqual(['dup']);
    const reasons = report.skipped.map((s) => s.reason).join('\n');
    expect(reasons).toMatch(/missing display_name, slot/);
    expect(reasons).toMatch(/not valid JSON/);
    expect(reasons).toMatch(/"alien"/);
    expect(reasons).toMatch(/already uses the id "dup"/);
  });

  it('checks manifest entries against pack files', () => {
    const root = 'C:/lib';
    const manifest = {
      packs: [
        { id: 'tail_a', library: 'humanoid', folder: 'humanoid/elements/tail/tail_a' },
        { id: 'plate', library: 'humanoid', folder: 'robot/parts/plate' },
        { id: 'ghost', library: 'humanoid', folder: 'humanoid/accessories/ghost' },
      ],
    };
    const scan: ScanResult = {
      root,
      files: [
        { path: `${root}/manifest.json`, text: JSON.stringify(manifest) },
        { path: `${root}/humanoid/elements/tail/tail_a/pack.json`, text: pack('tail_a', 'humanoid', 'element_tail', { socket: 'SOC-Tail' }) },
        { path: `${root}/robot/parts/plate/pack.json`, text: pack('plate', 'robot', 'chest') },
      ],
      assets: [],
    };
    const { packs, report } = importLibrary(scan);
    expect(packs.map((p) => p.id)).toEqual(['tail_a']);
    const reasons = report.skipped.map((s) => `${s.item}: ${s.reason}`).join('\n');
    expect(reasons).toMatch(/manifest.json lists it as humanoid but pack.json says robot/);
    expect(reasons).toMatch(/ghost: listed in manifest.json but the folder has no pack.json/);
  });

  it('marks re-imported ids as replaced', () => {
    const root = 'C:/lib/robot/parts';
    const scan: ScanResult = { root, files: [{ path: `${root}/fin/pack.json`, text: pack('fin', 'robot', 'antenna') }], assets: [] };
    const { report } = importLibrary(scan, new Set(['fin']));
    expect(report.replaced).toEqual(['fin']);
  });

  it('uses the pack tag when the tree above a browser-picked folder is unknown', () => {
    const scan: ScanResult = {
      root: 'hair',
      relativeOnly: true,
      files: [{ path: 'hair/pony/pack.json', text: pack('pony', 'humanoid', 'hair_extra') }],
      assets: [],
    };
    const { packs } = importLibrary(scan);
    expect(packs[0].category).toBe('hair/extras');
    expect(hairSlotForPack(packs[0])).toBe('extra');
  });

  it('locates folders in the tree', () => {
    expect(locateInTree('D:\\art\\library\\full_beast\\elements\\horns')).toEqual({ tree: 'full_beast', category: 'elements/horns' });
    expect(locateInTree('D:/art/other')).toEqual({ tree: null, category: '' });
  });
});
