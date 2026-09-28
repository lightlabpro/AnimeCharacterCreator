import type { AppearanceLayer, LayerPage, MaterialZone } from './types';

export const MATERIAL_ZONES: { id: MaterialZone; label: string }[] = [
  { id: 'head', label: 'Head' },
  { id: 'body', label: 'Body' },
  { id: 'arms', label: 'Arms' },
  { id: 'legs', label: 'Legs' },
  { id: 'nails', label: 'Nails' },
];

export interface LayerCategory {
  id: string;
  label: string;
  page: LayerPage;
  zones: MaterialZone[];
  defaultColor: string;
  defaultMask: string;
  adultOnly?: boolean;
}

export const LAYER_CATEGORIES: LayerCategory[] = [
  { id: 'skinColor', label: 'Skin color', page: 'skin', zones: ['head', 'body', 'arms', 'legs'], defaultColor: '#e8b090', defaultMask: 'full' },
  { id: 'veins', label: 'Veins', page: 'skin', zones: ['arms', 'legs', 'body'], defaultColor: '#7a86b8', defaultMask: 'lower', adultOnly: true },
  { id: 'bodyHair', label: 'Body hair', page: 'skin', zones: ['body', 'arms', 'legs'], defaultColor: '#3a2a20', defaultMask: 'full', adultOnly: true },
  { id: 'dirt', label: 'Dirt', page: 'skin', zones: ['head', 'body', 'arms', 'legs'], defaultColor: '#5a4632', defaultMask: 'lower' },
  { id: 'scars', label: 'Scars', page: 'skin', zones: ['head', 'body', 'arms', 'legs'], defaultColor: '#c87a70', defaultMask: 'cheeks' },
  { id: 'markings', label: 'Markings', page: 'skin', zones: ['head', 'body', 'arms', 'legs'], defaultColor: '#c83a3a', defaultMask: 'cheeks' },
  { id: 'wrinkles', label: 'Wrinkle mask', page: 'skin', zones: ['head'], defaultColor: '#8a5a4a', defaultMask: 'eyes', adultOnly: true },
  { id: 'blush', label: 'Blush', page: 'makeup', zones: ['head'], defaultColor: '#f07a80', defaultMask: 'cheeks' },
  { id: 'lips', label: 'Lip color', page: 'makeup', zones: ['head'], defaultColor: '#d0506a', defaultMask: 'lips' },
  { id: 'eyeshadow', label: 'Eye shadow', page: 'makeup', zones: ['head'], defaultColor: '#a05a8a', defaultMask: 'eyes' },
  { id: 'eyeliner', label: 'Eye liner', page: 'makeup', zones: ['head'], defaultColor: '#241a22', defaultMask: 'eyes' },
  { id: 'facePaint', label: 'Face paint', page: 'makeup', zones: ['head'], defaultColor: '#3a6ad5', defaultMask: 'forehead' },
  { id: 'nails', label: 'Nail color', page: 'makeup', zones: ['nails'], defaultColor: '#d04a6a', defaultMask: 'full' },
];

export const CATEGORY_BY_ID: Record<string, LayerCategory> = Object.fromEntries(LAYER_CATEGORIES.map((c) => [c.id, c]));

export const MASKS: Record<MaterialZone, { id: string; label: string }[]> = {
  head: [
    { id: 'full', label: 'Whole head' }, { id: 'cheeks', label: 'Cheeks' }, { id: 'eyes', label: 'Around the eyes' },
    { id: 'lips', label: 'Lips' }, { id: 'forehead', label: 'Forehead' }, { id: 'nose', label: 'Nose' }, { id: 'jaw', label: 'Jaw' },
    { id: 'tzone', label: 'T-zone' }, { id: 'mark', label: 'Forehead mark' },
  ],
  body: [
    { id: 'full', label: 'Whole torso' }, { id: 'chest', label: 'Chest' }, { id: 'belly', label: 'Belly' }, { id: 'back', label: 'Back' },
    { id: 'upper', label: 'Upper half' }, { id: 'lower', label: 'Lower half' }, { id: 'stripes', label: 'Stripes' },
  ],
  arms: [
    { id: 'full', label: 'Whole arm' }, { id: 'upper', label: 'Upper arm' }, { id: 'lower', label: 'Forearm and hand' }, { id: 'stripes', label: 'Bands' },
  ],
  legs: [
    { id: 'full', label: 'Whole leg' }, { id: 'upper', label: 'Thigh' }, { id: 'lower', label: 'Shin and foot' }, { id: 'stripes', label: 'Bands' },
  ],
  nails: [{ id: 'full', label: 'All nails' }, { id: 'tips', label: 'Tips only' }],
};

let counter = 0;
export function layerUid(): string {
  counter += 1;
  return `L${Date.now().toString(36)}${counter.toString(36)}`;
}

export function newLayer(categoryId: string, zone: MaterialZone): AppearanceLayer {
  const cat = CATEGORY_BY_ID[categoryId];
  const masks = MASKS[zone];
  const mask = masks.some((m) => m.id === cat.defaultMask) ? cat.defaultMask : masks[0].id;
  return { uid: layerUid(), category: cat.id, name: cat.label, page: cat.page, color: cat.defaultColor, opacity: 0.6, mask, hidden: false };
}

export function emptyAppearance(): Record<MaterialZone, AppearanceLayer[]> {
  return { head: [], body: [], arms: [], legs: [], nails: [] };
}

/** Merges the layer at index into the one below it. The result keeps both layers as children of one entry. */
export function mergeDown(layers: AppearanceLayer[], index: number): AppearanceLayer[] {
  if (index <= 0 || index >= layers.length) return layers;
  const lower = layers[index - 1];
  const upper = layers[index];
  const merged: AppearanceLayer = {
    uid: layerUid(),
    category: 'merged',
    name: `${lower.name} + ${upper.name}`,
    page: lower.page,
    color: lower.color,
    opacity: 1,
    mask: 'full',
    hidden: false,
    children: [...flattenChildren(lower), ...flattenChildren(upper)],
  };
  const out = layers.slice();
  out.splice(index - 1, 2, merged);
  return out;
}

export function flatten(layers: AppearanceLayer[]): AppearanceLayer[] {
  const visible = layers.filter((l) => !l.hidden);
  if (visible.length <= 1) return visible;
  return [
    {
      uid: layerUid(),
      category: 'merged',
      name: 'Flattened',
      page: 'skin',
      color: '#ffffff',
      opacity: 1,
      mask: 'full',
      hidden: false,
      children: visible.flatMap(flattenChildren),
    },
  ];
}

function flattenChildren(layer: AppearanceLayer): AppearanceLayer[] {
  if (layer.hidden) return [];
  if (!layer.children) return [layer];
  return layer.children.map((c) => ({ ...c, opacity: c.opacity * layer.opacity }));
}

/** Leaf layers in draw order, with merged group opacity applied. */
export function leafLayers(layers: AppearanceLayer[]): AppearanceLayer[] {
  return layers.flatMap(flattenChildren);
}
