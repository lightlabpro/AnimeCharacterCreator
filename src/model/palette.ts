import { parseHex } from './character';

/**
 * Gradient-map recoloring, after Capcom's NPC method: the painted brightness picks a spot on a
 * three-stop gradient built from the chosen color, instead of multiplying brightness by the color.
 * Dark paint lands on a hue-shifted deep tone and bright paint on a lifted tone, so recolors stay vivid.
 * The toon shader runs the same math per pixel (see recolor() in toonMaterial.ts).
 */
export type RGB = [number, number, number];

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const toUnit = (hex: string): RGB => parseHex(hex).map((v) => v / 255) as RGB;
const toHex = (c: RGB) => `#${c.map((v) => Math.round(clamp01(v) * 255).toString(16).padStart(2, '0')).join('')}`;
const lerp = (a: RGB, b: RGB, t: number): RGB => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

/** Deep end of the gradient: darker, pushed toward blue violet, a little more saturated. */
export function deepTone(c: RGB): RGB {
  return [c[0] * 0.42 + 0.03, c[1] * 0.36 + 0.02, c[2] * 0.5 + 0.08];
}

/** Light end of the gradient: toward a warm off-white. */
export function liftTone(c: RGB): RGB {
  return lerp(c, [1, 0.97, 0.9], 0.38);
}

/** Color for painted brightness `g` (0 to 1) under a chosen color. 0.5 returns the color itself. */
export function recolor(color: RGB, g: number): RGB {
  const t = clamp01(g);
  return t < 0.5 ? lerp(deepTone(color), color, t * 2) : lerp(color, liftTone(color), (t - 0.5) * 2);
}

export function recolorHex(color: string, g: number): string {
  return toHex(recolor(toUnit(color), g));
}

export type Element = 'none' | 'fire' | 'water' | 'thunder' | 'ice' | 'dragon';

/**
 * Element palettes for library variants: a target color and how far toward it every hue moves.
 * A variant keeps its value pattern and only its hue and tint follow the element.
 */
export const ELEMENT_PALETTES: Record<Element, { label: string; target: string; rate: number }> = {
  none: { label: 'None', target: '#ffffff', rate: 0 },
  fire: { label: 'Fire', target: '#e8502a', rate: 0.55 },
  water: { label: 'Water', target: '#2a8ad8', rate: 0.55 },
  thunder: { label: 'Thunder', target: '#f0c828', rate: 0.5 },
  ice: { label: 'Ice', target: '#9ad8f0', rate: 0.5 },
  dragon: { label: 'Dragon', target: '#8a2ab0', rate: 0.5 },
};

function rgbToHsl([r, g, b]: RGB): RGB {
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min;
  const s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  let h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h /= 6;
  return [h, s, l];
}

function hslToRgb([h, s, l]: RGB): RGB {
  if (s === 0) return [l, l, l];
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const f = (t: number) => {
    let x = t;
    if (x < 0) x += 1;
    if (x > 1) x -= 1;
    if (x < 1 / 6) return p + (q - p) * 6 * x;
    if (x < 1 / 2) return q;
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
    return p;
  };
  return [f(h + 1 / 3), f(h), f(h - 1 / 3)];
}

/** Moves a color's hue toward the element's target by the element's rate, along the shorter way round. */
export function elementVariant(color: string, element: Element): string {
  const pal = ELEMENT_PALETTES[element];
  if (!pal || pal.rate <= 0) return color;
  const [h, s, l] = rgbToHsl(toUnit(color));
  const [th, ts] = rgbToHsl(toUnit(pal.target));
  let dh = th - h;
  if (dh > 0.5) dh -= 1;
  if (dh < -0.5) dh += 1;
  const nh = (h + dh * pal.rate + 1) % 1;
  const ns = s + (ts - s) * pal.rate * 0.5;
  return toHex(hslToRgb([nh, clamp01(ns), l]));
}
