import * as THREE from 'three';

const SIZE = 256;

function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/**
 * Tonal art map (Praun 2001) packed into one RGBA texture. Each channel is one tone level and holds every
 * stroke of the lighter levels plus its own, so strokes stay put as the tone darkens.
 * R: sparse diagonal strokes. G: denser diagonal. B: adds the cross direction. A: dense crosshatch.
 * White is ink, black is paper. The texture tiles.
 */
export function hatchTexture(): THREE.Texture {
  if (typeof document === 'undefined') return new THREE.DataTexture(new Uint8Array(4), 1, 1);
  const levels: { angle: number; count: number }[][] = [
    [{ angle: 0.62, count: 26 }],
    [{ angle: 0.62, count: 52 }],
    [{ angle: 0.62, count: 64 }, { angle: -0.62, count: 30 }],
    [{ angle: 0.62, count: 80 }, { angle: -0.62, count: 64 }, { angle: 1.4, count: 30 }],
  ];
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = SIZE;
  const g = canvas.getContext('2d')!;
  const out = new Uint8Array(SIZE * SIZE * 4);
  const rand = rng(7);
  const strokes: { a: number; x: number; y: number; len: number; w: number }[] = [];
  levels.forEach((level, li) => {
    for (const set of level) {
      const have = strokes.filter((s) => Math.abs(s.a - set.angle) < 1e-3).length;
      for (let i = have; i < set.count; i += 1) {
        strokes.push({ a: set.angle, x: rand() * SIZE, y: rand() * SIZE, len: 40 + rand() * 60, w: 1 + rand() * 1.2 });
      }
    }
    g.fillStyle = '#000';
    g.fillRect(0, 0, SIZE, SIZE);
    g.strokeStyle = '#fff';
    g.lineCap = 'round';
    for (const s of strokes) {
      const dx = Math.cos(s.a) * s.len * 0.5;
      const dy = Math.sin(s.a) * s.len * 0.5;
      g.lineWidth = s.w;
      for (const ox of [-SIZE, 0, SIZE]) {
        for (const oy of [-SIZE, 0, SIZE]) {
          g.beginPath();
          g.moveTo(s.x + ox - dx, s.y + oy - dy);
          g.lineTo(s.x + ox + dx, s.y + oy + dy);
          g.stroke();
        }
      }
    }
    const px = g.getImageData(0, 0, SIZE, SIZE).data;
    for (let i = 0; i < SIZE * SIZE; i += 1) out[i * 4 + li] = px[i * 4];
  });
  const tex = new THREE.DataTexture(out, SIZE, SIZE, THREE.RGBAFormat);
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.magFilter = THREE.LinearFilter;
  tex.minFilter = THREE.LinearMipmapLinearFilter;
  tex.generateMipmaps = true;
  tex.needsUpdate = true;
  return tex;
}

/**
 * Adds an `outlineNormal` attribute: the average normal of every vertex at the same position.
 * Split vertices at UV seams and hard edges then push out together, so the inverted hull never cracks.
 */
export function ensureOutlineNormals(geom: THREE.BufferGeometry) {
  if (geom.attributes.outlineNormal) return;
  const pos = geom.attributes.position as THREE.BufferAttribute | undefined;
  const nrm = geom.attributes.normal as THREE.BufferAttribute | undefined;
  if (!pos || !nrm) return;
  const n = pos.count;
  const sums = new Map<string, [number, number, number]>();
  const keys: string[] = new Array(n);
  const q = 1e4;
  for (let i = 0; i < n; i += 1) {
    const k = `${Math.round(pos.getX(i) * q)},${Math.round(pos.getY(i) * q)},${Math.round(pos.getZ(i) * q)}`;
    keys[i] = k;
    const s = sums.get(k);
    if (s) {
      s[0] += nrm.getX(i);
      s[1] += nrm.getY(i);
      s[2] += nrm.getZ(i);
    } else sums.set(k, [nrm.getX(i), nrm.getY(i), nrm.getZ(i)]);
  }
  const out = new Float32Array(n * 3);
  for (let i = 0; i < n; i += 1) {
    const s = sums.get(keys[i])!;
    const len = Math.hypot(s[0], s[1], s[2]) || 1;
    out[i * 3] = s[0] / len;
    out[i * 3 + 1] = s[1] / len;
    out[i * 3 + 2] = s[2] / len;
  }
  geom.setAttribute('outlineNormal', new THREE.BufferAttribute(out, 3));
}
