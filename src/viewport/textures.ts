import * as THREE from 'three';
import { leafLayers } from '../model/appearance';
import type { AppearanceLayer } from '../model/types';
import { seeded } from './parts';

const texCache = new Map<string, THREE.Texture>();
const MAX_CACHE = 160;

function remember(key: string, make: () => THREE.Texture): THREE.Texture {
  const hit = texCache.get(key);
  if (hit) return hit;
  const t = make();
  t.userData.cached = true;
  texCache.set(key, t);
  if (texCache.size > MAX_CACHE) {
    const first = texCache.keys().next().value as string;
    texCache.get(first)?.dispose();
    texCache.delete(first);
  }
  return t;
}

function canvas(w: number, h: number): [HTMLCanvasElement, CanvasRenderingContext2D] {
  const c = document.createElement('canvas');
  c.width = w;
  c.height = h;
  return [c, c.getContext('2d')!];
}

function toTexture(c: HTMLCanvasElement, srgb = true): THREE.CanvasTexture {
  const t = new THREE.CanvasTexture(c);
  if (srgb) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.wrapS = THREE.RepeatWrapping;
  return t;
}

function rgba(hex: string, a: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${Math.max(0, Math.min(1, a))})`;
}

export interface SurfaceParams {
  base: string;
  primary: string;
  secondary: string;
  belly: string;
  pattern: string;
  surface: string;
  coverage: number;
  bellyWidth: number;
  veins: number;
  hair: number;
  hairColor: string;
  layers: AppearanceLayer[];
  zone: string;
  seed: number;
}

function paintPattern(ctx: CanvasRenderingContext2D, W: number, H: number, p: SurfaceParams, rand: () => number) {
  const col = p.secondary;
  const a = p.coverage;
  if (p.pattern === 'stripes') {
    const n = 7;
    for (let i = 0; i < n; i += 1) {
      const y = ((i + 0.5) / n) * H;
      ctx.fillStyle = rgba(col, 0.9 * a);
      ctx.beginPath();
      const segs = 24;
      for (let s = 0; s <= segs; s += 1) {
        const x = (s / segs) * W;
        const wob = Math.sin(s * 0.9 + i * 2.1) * H * 0.02;
        const th = H * 0.022 * (0.6 + 0.8 * Math.abs(Math.sin(s * 0.45 + i)));
        if (s === 0) ctx.moveTo(x, y + wob - th);
        else ctx.lineTo(x, y + wob - th);
      }
      for (let s = segs; s >= 0; s -= 1) {
        const x = (s / segs) * W;
        const wob = Math.sin(s * 0.9 + i * 2.1) * H * 0.02;
        const th = H * 0.022 * (0.6 + 0.8 * Math.abs(Math.sin(s * 0.45 + i)));
        ctx.lineTo(x, y + wob + th);
      }
      ctx.fill();
    }
  } else if (p.pattern === 'spots') {
    for (let i = 0; i < 26; i += 1) {
      const x = rand() * W;
      const y = rand() * H;
      const r = (0.025 + rand() * 0.04) * W;
      ctx.fillStyle = rgba(col, 0.85 * a);
      ctx.beginPath();
      ctx.ellipse(x, y, r, r * (0.7 + rand() * 0.5), rand() * 3, 0, Math.PI * 2);
      ctx.fill();
    }
  } else if (p.pattern === 'plates' || p.surface === 'scales' || p.surface === 'hide' || p.surface === 'feathers') {
    const cols = p.surface === 'hide' ? 6 : 10;
    const rows = p.surface === 'hide' ? 5 : 9;
    const cw = W / cols;
    const rh = H / rows;
    ctx.lineWidth = p.surface === 'hide' ? 2.2 : 1.6;
    for (let r = 0; r < rows; r += 1) {
      for (let c = 0; c <= cols; c += 1) {
        const x = c * cw + (r % 2 ? cw / 2 : 0);
        const y = r * rh;
        ctx.strokeStyle = rgba('#000000', 0.18 * a);
        ctx.fillStyle = p.pattern === 'plates' ? rgba(col, 0.28 * a) : rgba('#ffffff', 0.05 * a);
        ctx.beginPath();
        if (p.surface === 'feathers') {
          ctx.ellipse(x, y + rh * 0.8, cw * 0.55, rh * 0.8, 0, 0, Math.PI);
        } else {
          const rr = Math.min(cw, rh) * 0.25;
          ctx.roundRect(x - cw * 0.46, y + rh * 0.06, cw * 0.92, rh * 0.88, rr);
        }
        ctx.fill();
        ctx.stroke();
      }
    }
  }
}

function paintBelly(ctx: CanvasRenderingContext2D, W: number, H: number, p: SurfaceParams) {
  if (p.bellyWidth <= 0 || p.surface === 'skin') return;
  const bw = W * p.bellyWidth;
  for (const x0 of [0, W]) {
    const g = ctx.createLinearGradient(x0 - bw, 0, x0 + bw, 0);
    g.addColorStop(0, rgba(p.belly, 0));
    g.addColorStop(0.35, rgba(p.belly, 0.95 * p.coverage));
    g.addColorStop(0.65, rgba(p.belly, 0.95 * p.coverage));
    g.addColorStop(1, rgba(p.belly, 0));
    ctx.fillStyle = g;
    ctx.fillRect(x0 - bw, 0, bw * 2, H);
  }
}

function maskRect(mask: string, W: number, H: number): [number, number, number, number] {
  switch (mask) {
    case 'upper': return [0, 0, W, H * 0.5];
    case 'lower': return [0, H * 0.5, W, H * 0.5];
    case 'chest': return [W * 0.8, H * 0.05, W * 0.4, H * 0.4];
    case 'belly': return [W * 0.82, H * 0.45, W * 0.36, H * 0.5];
    case 'back': return [W * 0.3, 0, W * 0.4, H];
    case 'tips': return [0, 0, W, H * 0.35];
    default: return [0, 0, W, H];
  }
}

function paintBodyLayer(ctx: CanvasRenderingContext2D, W: number, H: number, l: AppearanceLayer, rand: () => number) {
  const [x, y, w, h] = maskRect(l.mask, W, H);
  const rects: [number, number, number, number][] = [[x, y, w, h]];
  if (x + w > W) rects.push([x - W, y, w, h]);
  for (const [rx, ry, rw, rh] of rects) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(rx, ry, rw, rh);
    ctx.clip();
    if (l.mask === 'stripes') {
      for (let i = 0; i < 6; i += 1) {
        ctx.fillStyle = rgba(l.color, l.opacity);
        ctx.fillRect(0, (i / 6) * H + H * 0.03, W, H * 0.035);
      }
    } else if (l.category === 'dirt') {
      for (let i = 0; i < 90; i += 1) {
        const px = rx + rand() * rw;
        const py = ry + rh * Math.pow(rand(), 0.6);
        ctx.fillStyle = rgba(l.color, l.opacity * (0.25 + rand() * 0.5));
        ctx.beginPath();
        ctx.ellipse(px, py, 4 + rand() * 14, 3 + rand() * 9, rand() * 3, 0, Math.PI * 2);
        ctx.fill();
      }
    } else if (l.category === 'scars') {
      ctx.strokeStyle = rgba(l.color, l.opacity);
      ctx.lineWidth = 2.5;
      for (let i = 0; i < 3; i += 1) {
        ctx.beginPath();
        const sx = rx + rand() * rw;
        const sy = ry + rand() * rh;
        ctx.moveTo(sx, sy);
        ctx.lineTo(sx + (rand() - 0.5) * rw * 0.3, sy + rand() * rh * 0.3);
        ctx.stroke();
      }
    } else if (l.category === 'markings') {
      ctx.fillStyle = rgba(l.color, l.opacity);
      for (let i = 0; i < 4; i += 1) {
        const yy = ry + (i + 0.5) * (rh / 4);
        ctx.beginPath();
        ctx.moveTo(rx, yy);
        ctx.lineTo(rx + rw * 0.5, yy - rh * 0.05);
        ctx.lineTo(rx + rw, yy);
        ctx.lineTo(rx + rw * 0.5, yy + rh * 0.04);
        ctx.fill();
      }
    } else if (l.category === 'veins') {
      paintVeins(ctx, rx, ry, rw, rh, l.color, l.opacity, rand);
    } else if (l.category === 'bodyHair') {
      paintHairStrokes(ctx, rx, ry, rw, rh, l.color, l.opacity, rand);
    } else {
      ctx.fillStyle = rgba(l.color, l.opacity);
      ctx.fillRect(rx, ry, rw, rh);
    }
    ctx.restore();
  }
}

function paintVeins(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, color: string, a: number, rand: () => number) {
  ctx.strokeStyle = rgba(color, a);
  ctx.lineWidth = 1.4;
  for (let i = 0; i < 9; i += 1) {
    let px = x + rand() * w;
    let py = y + rand() * h * 0.3;
    ctx.beginPath();
    ctx.moveTo(px, py);
    for (let s = 0; s < 6; s += 1) {
      px += (rand() - 0.5) * 12;
      py += h * 0.1;
      ctx.lineTo(px, py);
    }
    ctx.stroke();
  }
}

function paintHairStrokes(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, color: string, a: number, rand: () => number) {
  ctx.strokeStyle = rgba(color, a * 0.8);
  ctx.lineWidth = 1;
  const n = Math.round(260 * a);
  for (let i = 0; i < n; i += 1) {
    const px = x + rand() * w;
    const py = y + rand() * h;
    ctx.beginPath();
    ctx.moveTo(px, py);
    ctx.lineTo(px + (rand() - 0.5) * 3, py + 3 + rand() * 4);
    ctx.stroke();
  }
}

export function surfaceTexture(p: SurfaceParams): THREE.Texture {
  const key = `surf:${JSON.stringify(p)}`;
  return remember(key, () => {
    const W = 256;
    const H = 256;
    const [c, ctx] = canvas(W, H);
    const rand = seeded(p.seed);
    const fur = p.surface !== 'skin';
    ctx.fillStyle = fur ? mixColor(p.base, p.primary, p.coverage) : p.base;
    ctx.fillRect(0, 0, W, H);
    if (fur && p.coverage > 0) {
      paintPattern(ctx, W, H, p, rand);
      paintBelly(ctx, W, H, p);
    }
    if (p.veins > 0) paintVeins(ctx, 0, H * 0.45, W, H * 0.55, '#7a86b8', p.veins * 0.55, rand);
    if (p.hair > 0) paintHairStrokes(ctx, 0, 0, W, H, p.hairColor, p.hair * 0.6, rand);
    for (const l of leafLayers(p.layers)) paintBodyLayer(ctx, W, H, l, rand);
    return toTexture(c);
  });
}

export interface FaceLayout {
  cx: number;
  cy: number;
  hx: number;
  hy: number;
  eyes: { x: number; y: number; w: number; h: number };
  mouth: { x: number; y: number; w: number };
  cheeks: { x: number; y: number; r: number };
  nose: { x: number; y: number };
  browY: number;
  foreheadY: number;
  jawY: number;
}

export interface FaceParams {
  layout: FaceLayout;
  blush: number;
  blushColor: string;
  crease: number;
  creaseColor: string;
  surface: string;
  coverage: number;
  pattern: string;
  secondary: string;
  belly: string;
  muzzle: boolean;
  stubble: number;
  stubbleColor: string;
  layers: AppearanceLayer[];
  seed: number;
}

function faceMapper(l: FaceLayout, S: number) {
  return {
    x: (x: number) => ((x - l.cx) / l.hx * 0.5 + 0.5) * S,
    y: (y: number) => (0.5 - (y - l.cy) / l.hy * 0.5) * S,
    s: (d: number) => (d / l.hx) * 0.5 * S,
    sy: (d: number) => (d / l.hy) * 0.5 * S,
  };
}

function softEllipse(ctx: CanvasRenderingContext2D, x: number, y: number, rx: number, ry: number, color: string, a: number) {
  ctx.save();
  ctx.translate(x, y);
  ctx.scale(1, ry / rx);
  const g = ctx.createRadialGradient(0, 0, 0, 0, 0, rx);
  g.addColorStop(0, rgba(color, a));
  g.addColorStop(0.55, rgba(color, a * 0.6));
  g.addColorStop(1, rgba(color, 0));
  ctx.fillStyle = g;
  ctx.beginPath();
  ctx.arc(0, 0, rx, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function faceMaskShapes(mask: string, l: FaceLayout, m: ReturnType<typeof faceMapper>): { x: number; y: number; rx: number; ry: number }[] {
  const e = l.eyes;
  switch (mask) {
    case 'cheeks':
      return [-1, 1].map((s) => ({ x: m.x(s * l.cheeks.x), y: m.y(l.cheeks.y), rx: m.s(l.cheeks.r), ry: m.sy(l.cheeks.r * 0.7) }));
    case 'eyes':
      return [-1, 1].map((s) => ({ x: m.x(s * e.x), y: m.y(e.y + e.h * 0.35), rx: m.s(e.w * 1.5), ry: m.sy(e.h * 1.2) }));
    case 'lips':
      return [{ x: m.x(0), y: m.y(l.mouth.y), rx: m.s(l.mouth.w * 0.8), ry: m.sy(l.mouth.w * 0.4) }];
    case 'forehead':
      return [{ x: m.x(0), y: m.y(l.foreheadY), rx: m.s(l.hx * 0.6), ry: m.sy(l.hy * 0.2) }];
    case 'nose':
      return [{ x: m.x(0), y: m.y(l.nose.y), rx: m.s(e.w * 0.6), ry: m.sy(e.h * 0.9) }];
    case 'jaw':
      return [{ x: m.x(0), y: m.y(l.jawY), rx: m.s(l.hx * 0.75), ry: m.sy(l.hy * 0.25) }];
    case 'tzone':
      return [
        { x: m.x(0), y: m.y(l.foreheadY), rx: m.s(l.hx * 0.5), ry: m.sy(l.hy * 0.14) },
        { x: m.x(0), y: m.y((l.browY + l.nose.y) / 2), rx: m.s(e.w * 0.45), ry: m.sy(Math.abs(l.browY - l.nose.y) * 0.8) },
      ];
    case 'mark':
      return [{ x: m.x(0), y: m.y(l.browY + e.h * 1.3), rx: m.s(e.w * 0.18), ry: m.sy(e.w * 0.28) }];
    default:
      return [{ x: m.x(0), y: m.y(l.cy), rx: m.s(l.hx), ry: m.sy(l.hy) }];
  }
}

function paintFaceLayer(ctx: CanvasRenderingContext2D, l: AppearanceLayer, lay: FaceLayout, m: ReturnType<typeof faceMapper>, rand: () => number) {
  const shapes = faceMaskShapes(l.mask, lay, m);
  const a = l.opacity;
  for (const s of shapes) {
    switch (l.category) {
      case 'eyeliner': {
        ctx.strokeStyle = rgba(l.color, a);
        ctx.lineWidth = Math.max(2, s.ry * 0.12);
        ctx.beginPath();
        ctx.ellipse(s.x, s.y + s.ry * 0.35, s.rx * 0.62, s.ry * 0.6, 0, Math.PI * 1.05, Math.PI * 1.95);
        ctx.stroke();
        break;
      }
      case 'markings':
      case 'facePaint': {
        ctx.fillStyle = rgba(l.color, a);
        if (l.mask === 'mark') {
          ctx.beginPath();
          ctx.moveTo(s.x, s.y - s.ry);
          ctx.lineTo(s.x + s.rx, s.y);
          ctx.lineTo(s.x, s.y + s.ry);
          ctx.lineTo(s.x - s.rx, s.y);
          ctx.fill();
        } else {
          for (let i = 0; i < 3; i += 1) {
            const yy = s.y - s.ry * 0.5 + i * s.ry * 0.45;
            ctx.beginPath();
            ctx.moveTo(s.x - s.rx * 0.9, yy);
            ctx.quadraticCurveTo(s.x, yy - s.ry * 0.25, s.x + s.rx * 0.9, yy);
            ctx.lineTo(s.x + s.rx * 0.9, yy + s.ry * 0.12);
            ctx.quadraticCurveTo(s.x, yy - s.ry * 0.1, s.x - s.rx * 0.9, yy + s.ry * 0.12);
            ctx.fill();
          }
        }
        break;
      }
      case 'scars': {
        ctx.strokeStyle = rgba(l.color, a);
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.moveTo(s.x - s.rx * 0.5, s.y - s.ry * 0.6);
        ctx.lineTo(s.x + s.rx * 0.3, s.y + s.ry * 0.5);
        ctx.stroke();
        ctx.lineWidth = 1.5;
        for (let i = 0; i < 4; i += 1) {
          const t = i / 3;
          const px = s.x - s.rx * 0.5 + t * s.rx * 0.8;
          const py = s.y - s.ry * 0.6 + t * s.ry * 1.1;
          ctx.beginPath();
          ctx.moveTo(px - 4, py + 3);
          ctx.lineTo(px + 4, py - 3);
          ctx.stroke();
        }
        break;
      }
      case 'dirt': {
        for (let i = 0; i < 30; i += 1) {
          softEllipse(ctx, s.x + (rand() - 0.5) * s.rx * 1.6, s.y + (rand() - 0.5) * s.ry * 1.6, 6 + rand() * 16, 5 + rand() * 12, l.color, a * 0.5);
        }
        break;
      }
      case 'wrinkles': {
        ctx.strokeStyle = rgba(l.color, a * 0.7);
        ctx.lineWidth = 1.6;
        for (let i = 0; i < 3; i += 1) {
          ctx.beginPath();
          ctx.arc(s.x, s.y + i * 5, s.rx * (0.5 + i * 0.15), Math.PI * 1.15, Math.PI * 1.85);
          ctx.stroke();
        }
        break;
      }
      default:
        softEllipse(ctx, s.x, s.y, s.rx, s.ry, l.color, a);
    }
  }
}

export function faceTexture(p: FaceParams): THREE.Texture {
  const key = `face:${JSON.stringify(p)}`;
  return remember(key, () => {
    const S = 512;
    const [c, ctx] = canvas(S, S);
    const L = p.layout;
    const m = faceMapper(L, S);
    const rand = seeded(p.seed);
    const fur = p.surface !== 'skin' && p.coverage > 0;
    if (fur) {
      if (p.pattern === 'stripes') {
        ctx.fillStyle = rgba(p.secondary, 0.85 * p.coverage);
        for (const s of [-1, 1]) {
          for (let i = 0; i < 3; i += 1) {
            const y = m.y(L.cheeks.y - i * L.eyes.h * 0.55);
            const x0 = m.x(s * L.hx * 0.98);
            const x1 = m.x(s * (L.cheeks.x + L.eyes.w * 0.4 - i * L.eyes.w * 0.15));
            ctx.beginPath();
            ctx.moveTo(x0, y - 8);
            ctx.lineTo(x1, y);
            ctx.lineTo(x0, y + 8);
            ctx.fill();
          }
        }
        for (let i = 0; i < 3; i += 1) {
          const x = m.x((i - 1) * L.eyes.w * 0.6);
          ctx.beginPath();
          ctx.moveTo(x - 6, m.y(L.foreheadY + L.hy * 0.25));
          ctx.lineTo(x, m.y(L.browY + L.eyes.h * 0.7));
          ctx.lineTo(x + 6, m.y(L.foreheadY + L.hy * 0.25));
          ctx.fill();
        }
      } else if (p.pattern === 'spots') {
        for (let i = 0; i < 12; i += 1) {
          const s = rand() < 0.5 ? -1 : 1;
          softEllipse(ctx, m.x(s * (L.hx * (0.4 + rand() * 0.5))), m.y(L.cy + (rand() - 0.3) * L.hy), 8 + rand() * 10, 7 + rand() * 8, p.secondary, 0.8 * p.coverage);
        }
      }
      const gy0 = m.y(L.nose.y);
      const g = ctx.createLinearGradient(0, gy0, 0, S);
      g.addColorStop(0, rgba(p.belly, 0));
      g.addColorStop(0.25, rgba(p.belly, 0.9 * p.coverage));
      g.addColorStop(1, rgba(p.belly, 0.95 * p.coverage));
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.ellipse(m.x(0), m.y(L.mouth.y), m.s(L.mouth.w * 1.9), m.sy(Math.abs(L.nose.y - L.jawY) * 1.1), 0, 0, Math.PI * 2);
      ctx.fill();
    }
    if (p.blush > 0) {
      for (const s of [-1, 1]) softEllipse(ctx, m.x(s * L.cheeks.x), m.y(L.cheeks.y), m.s(L.cheeks.r), m.sy(L.cheeks.r * 0.62), p.blushColor, p.blush * 0.6);
      if (p.blush > 0.35) {
        ctx.strokeStyle = rgba('#e0606a', (p.blush - 0.35) * 0.7);
        ctx.lineWidth = 2;
        for (const s of [-1, 1]) {
          for (let i = 0; i < 3; i += 1) {
            const x = m.x(s * L.cheeks.x) + (i - 1) * 8;
            const y = m.y(L.cheeks.y);
            ctx.beginPath();
            ctx.moveTo(x + 3, y - 5);
            ctx.lineTo(x - 3, y + 5);
            ctx.stroke();
          }
        }
      }
    }
    if (p.crease > 0) {
      ctx.strokeStyle = rgba(p.creaseColor, p.crease * 0.55);
      ctx.lineWidth = 2;
      for (const s of [-1, 1]) {
        const x = m.x(s * L.eyes.x);
        const y = m.y(L.eyes.y + L.eyes.h * 1.05);
        ctx.beginPath();
        ctx.ellipse(x, y + m.sy(L.eyes.h) * 0.4, m.s(L.eyes.w) * 0.95, m.sy(L.eyes.h) * 0.55, 0, Math.PI * 1.1, Math.PI * 1.9);
        ctx.stroke();
      }
    }
    if (p.stubble > 0) {
      const y0 = m.y(L.mouth.y + L.eyes.h * 0.8);
      for (let i = 0; i < 1400 * p.stubble; i += 1) {
        const x = m.x((rand() * 2 - 1) * L.hx * 0.85);
        const y = y0 + rand() * (S - y0);
        const dx = (x - m.x(0)) / m.s(L.hx * 0.85);
        const dy = (y - m.y(L.mouth.y)) / m.sy(L.mouth.w * 0.3);
        if (dx * dx + dy * dy < 1) continue;
        ctx.fillStyle = rgba(p.stubbleColor, 0.35 + rand() * 0.3);
        ctx.fillRect(x, y, 1.6, 1.6);
      }
    }
    for (const l of leafLayers(p.layers)) {
      if (l.category === 'lips') continue;
      paintFaceLayer(ctx, l, L, m, rand);
    }
    return toTexture(c);
  });
}

/** Four crease channels in face space: forehead, brow and nose, eye corners, mouth folds. */
export function wrinkleTexture(layout: FaceLayout): THREE.Texture {
  const key = `wr:${JSON.stringify(layout)}`;
  return remember(key, () => {
    const S = 256;
    const data = new Uint8Array(S * S * 4);
    const L = layout;
    const line = (d: number, w: number) => Math.max(0, 1 - Math.abs(d) / w);
    for (let py = 0; py < S; py += 1) {
      for (let px = 0; px < S; px += 1) {
        const x = L.cx + ((px + 0.5) / S * 2 - 1) * L.hx;
        const y = L.cy + ((py + 0.5) / S * 2 - 1) * L.hy;
        const ax = Math.abs(x);
        let f = 0;
        const fy = L.browY + L.eyes.h * 1.4;
        if (ax < L.hx * 0.55 && y > fy && y < fy + L.hy * 0.35) {
          for (let i = 0; i < 3; i += 1) {
            const yy = fy + L.hy * (0.06 + i * 0.08) - (x * x) / L.hx * 0.4;
            f = Math.max(f, line(y - yy, L.hy * 0.012));
          }
          f *= 1 - ax / (L.hx * 0.55);
        }
        let b = 0;
        if (ax < L.eyes.w * 0.6 && y > L.browY - L.eyes.h * 0.5 && y < L.browY + L.eyes.h * 1.2) {
          b = Math.max(line(ax - L.eyes.w * 0.18, L.hx * 0.012), line(ax - L.eyes.w * 0.34, L.hx * 0.01) * 0.7);
        }
        if (ax < L.eyes.w * 0.55 && y > L.nose.y && y < L.eyes.y - L.eyes.h * 0.4) {
          for (let i = 0; i < 3; i += 1) b = Math.max(b, line(y - (L.nose.y + (L.eyes.y - L.nose.y) * (0.35 + i * 0.18)), L.hy * 0.01) * 0.8);
        }
        let e = 0;
        const ox = ax - (L.eyes.x + L.eyes.w * 1.15);
        if (ox > 0 && ox < L.eyes.w * 0.55) {
          const dy = y - L.eyes.y;
          for (let i = -1; i <= 1; i += 1) e = Math.max(e, line(dy - i * L.eyes.h * 0.3 - ox * i * 0.4, L.hy * 0.01) * (1 - ox / (L.eyes.w * 0.55)));
        }
        let mo = 0;
        const mx = L.mouth.w * 0.55;
        if (y < L.nose.y && y > L.mouth.y - L.mouth.w * 0.45) {
          const t = (L.nose.y - y) / (L.nose.y - L.mouth.y + L.mouth.w * 0.45);
          const curve = mx + L.mouth.w * 0.35 * Math.sin(t * Math.PI * 0.9);
          mo = line(ax - curve, L.hx * 0.014);
        }
        const i4 = ((S - 1 - py) * S + px) * 4;
        data[i4] = Math.round(f * 255);
        data[i4 + 1] = Math.round(b * 255);
        data[i4 + 2] = Math.round(e * 255);
        data[i4 + 3] = Math.round(mo * 255);
      }
    }
    const t = new THREE.DataTexture(data, S, S, THREE.RGBAFormat);
    t.magFilter = THREE.LinearFilter;
    t.minFilter = THREE.LinearFilter;
    t.needsUpdate = true;
    return t;
  });
}

/** R: survival threshold for holes and fray (low values tear first). G: dirt. */
export function damageTexture(seed: number, torn: boolean): THREE.Texture {
  const key = `dmg:${seed}:${torn}`;
  return remember(key, () => {
    const S = 128;
    const data = new Uint8Array(S * S * 4);
    const rand = seeded(seed);
    const holes: [number, number, number][] = [];
    for (let i = 0; i < 9; i += 1) holes.push([rand(), rand() * 0.8, 0.04 + rand() * 0.08]);
    const jag: number[] = [];
    for (let i = 0; i < S; i += 1) jag.push(rand());
    for (let y = 0; y < S; y += 1) {
      for (let x = 0; x < S; x += 1) {
        const u = x / S;
        const v = y / S;
        let r = 0.35 + v * 0.65;
        for (const [hx, hy, hr] of holes) {
          const d = Math.hypot(u - hx, (v - hy) * 1.3) / hr;
          if (d < 1) r = Math.min(r, 0.1 + d * 0.6 + hy * 0.2);
        }
        const edge = 0.04 + jag[x] * 0.1 + (torn ? 0.06 : 0);
        if (v < edge) r = Math.min(r, (v / edge) * 0.7);
        if (torn) r *= 0.8;
        const dirt = Math.max(0, 1 - v * 1.6) * (0.6 + rand() * 0.4);
        const i4 = (y * S + x) * 4;
        data[i4] = Math.round(Math.min(1, r) * 255);
        data[i4 + 1] = Math.round(dirt * 255);
        data[i4 + 2] = 0;
        data[i4 + 3] = 255;
      }
    }
    const t = new THREE.DataTexture(data, S, S, THREE.RGBAFormat);
    t.magFilter = THREE.LinearFilter;
    t.minFilter = THREE.LinearFilter;
    t.needsUpdate = true;
    return t;
  });
}

export function mixColor(a: string, b: string, t: number): string {
  const ca = new THREE.Color(a);
  const cb = new THREE.Color(b);
  return `#${ca.lerp(cb, Math.max(0, Math.min(1, t))).getHexString()}`;
}

export function releaseTextureCache() {
  for (const t of texCache.values()) t.dispose();
  texCache.clear();
}
