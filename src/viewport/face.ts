import * as THREE from 'three';
import { conformGrid, HeadSurface, type PartRegistry } from './parts';
import { sharedUniforms } from './toonMaterial';

const eyeVertex = /* glsl */ `
varying vec2 vUv2;
varying vec3 vN;
void main() {
  vUv2 = uv;
  vN = normalize(normalMatrix * normal);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}
`;

const eyeFragment = /* glsl */ `
uniform vec3 uIris;
uniform vec3 uIrisDark;
uniform vec3 uSclera;
uniform vec3 uSkin;
uniform vec3 uLash;
uniform vec3 uLidTint;
uniform float uLidTintA;
uniform vec2 uGaze;
uniform float uIrisSize;
uniform float uPupilSize;
uniform float uPupilStyle;
uniform float uCatch;
uniform float uUpper;
uniform float uLower;
uniform float uSqueeze;
uniform float uLashT;
uniform float uSide;
uniform float uSelect;
uniform float uGlow;
uniform vec3 uLightDir;
uniform float uSaturation;
uniform float uBrightness;
varying vec2 vUv2;
varying vec3 vN;

void main() {
  vec2 p = vUv2 * 2.0 - 1.0;
  float x = p.x;
  float ax = clamp(abs(x), 0.0, 1.0);
  float top = sqrt(max(1.0 - x * x, 0.0));
  float k = mix(-0.28, 0.5, uSqueeze);
  float closed = -0.18 + k * (1.0 - x * x);
  float yLid = mix(top, closed, clamp(uUpper, 0.0, 1.0));
  if (uUpper < 0.0) yLid = top;
  float yLow = mix(-top, closed - 0.015, clamp(uLower, 0.0, 1.0));
  float lashT = uLashT * (1.0 - 0.55 * ax * ax) * (1.0 - 0.35 * clamp(uUpper, 0.0, 1.0));
  float flick = smoothstep(0.55, 0.98, x * uSide) * uLashT * 1.6;

  float lighting = 0.9 + 0.1 * max(dot(normalize(vN), normalize(uLightDir)), 0.0);
  vec3 lid = mix(uSkin, uLidTint, uLidTintA) * lighting;
  vec3 col;
  if (p.y > yLid) {
    col = lid;
    if (p.y < yLid + lashT + flick * smoothstep(0.0, 0.25, p.y - yLid + 0.2)) col = uLash;
  } else if (p.y < yLow) {
    col = lid;
    if (p.y > yLow - 0.05 && x * uSide > 0.1) col = mix(lid, uLash, 0.6);
  } else {
    vec2 c = vec2(uGaze.x * 0.42, uGaze.y * 0.3 - 0.05);
    vec2 d = (p - c) / vec2(0.82, 1.0);
    float r = length(d) / uIrisSize;
    col = uSclera * lighting;
    float shade = smoothstep(yLid - 0.45, yLid, p.y);
    col *= 1.0 - 0.28 * shade;
    if (r < 1.0) {
      float grad = clamp((d.y / uIrisSize) * 0.5 + 0.5, 0.0, 1.0);
      vec3 iris = mix(uIris * 1.25, uIrisDark, grad);
      iris = mix(iris, uIrisDark * 0.6, smoothstep(0.82, 0.96, r));
      float ring = smoothstep(0.35, 0.6, r) * (1.0 - smoothstep(0.62, 0.8, r));
      iris += uIris * 0.25 * ring * (1.0 - grad);
      vec2 q = d / uIrisSize;
      float pupil;
      if (uPupilStyle < 0.5) pupil = length(q) / (uPupilSize * 0.5);
      else if (uPupilStyle < 1.5) pupil = length(q / vec2(0.28, 1.0)) / (uPupilSize * 0.95);
      else if (uPupilStyle < 2.5) pupil = length(q / vec2(1.0, 0.3)) / (uPupilSize * 0.95);
      else {
        float a = atan(q.y, q.x);
        pupil = length(q) / (uPupilSize * (0.35 + 0.35 * pow(abs(cos(2.0 * a)), 6.0)));
      }
      if (pupil < 1.0) iris = uIrisDark * 0.25;
      iris *= 1.0 - 0.3 * shade;
      col = iris + uIris * uGlow;
    }
    vec2 cl = (p - c - vec2(-0.32, 0.36) * uIrisSize) / vec2(0.2, 0.26) / uIrisSize;
    if (length(cl) < 1.0) col = mix(col, vec3(1.0), clamp(uCatch, 0.0, 1.0));
    if (p.y > yLid - 0.06) col = mix(col, uLash, 0.35);
  }
  float lum = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(vec3(lum), col, uSaturation) * uBrightness;
  col = mix(col, vec3(0.3, 0.78, 1.0), uSelect * 0.42);
  gl_FragColor = vec4(col, 1.0);
  #include <colorspace_fragment>
}
`;

export function eyeMaterial(side: 1 | -1): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader: eyeVertex,
    fragmentShader: eyeFragment,
    uniforms: {
      uIris: { value: new THREE.Color('#2fa47e') },
      uIrisDark: { value: new THREE.Color('#123a30') },
      uSclera: { value: new THREE.Color('#fbfbff') },
      uSkin: { value: new THREE.Color('#f6d2bc') },
      uLash: { value: new THREE.Color('#241a18') },
      uLidTint: { value: new THREE.Color('#a05a8a') },
      uLidTintA: { value: 0 },
      uGaze: { value: new THREE.Vector2() },
      uIrisSize: { value: 0.62 },
      uPupilSize: { value: 0.42 },
      uPupilStyle: { value: 0 },
      uCatch: { value: 0.95 },
      uUpper: { value: 0.1 },
      uLower: { value: 0 },
      uSqueeze: { value: 0 },
      uLashT: { value: 0.16 },
      uSide: { value: side },
      uSelect: { value: 0 },
      uGlow: { value: 0 },
      uLightDir: sharedUniforms.uLightDir,
      uSaturation: sharedUniforms.uSaturation,
      uBrightness: sharedUniforms.uBrightness,
    },
  });
}

const mouthFragment = /* glsl */ `
uniform float uHalfW;
uniform float uCornerL;
uniform float uCornerR;
uniform float uOpenUp;
uniform float uOpenDown;
uniform float uExp;
uniform float uShift;
uniform float uTeethUp;
uniform float uTeethDown;
uniform float uTongue;
uniform float uTongueFwd;
uniform float uLipUpper;
uniform float uLipLower;
uniform float uPress;
uniform float uBite;
uniform float uFangs;
uniform vec3 uLip;
uniform vec3 uLine;
uniform vec3 uCavity;
uniform vec3 uTeeth;
uniform vec3 uTongueCol;
uniform float uSelect;
uniform float uSaturation;
uniform float uBrightness;
varying vec2 vUv2;

void main() {
  vec2 p = vUv2 * 2.0 - 1.0;
  float t = (p.x - uShift) / uHalfW;
  float at = abs(t);
  float env = pow(max(1.0 - t * t, 0.0), uExp);
  float corner = t < 0.0 ? uCornerR : uCornerL;
  float mid = corner * t * t;
  float open = uOpenUp + uOpenDown;
  float upper = mid + uOpenUp * env;
  float lower = mid - uOpenDown * env;
  vec4 col = vec4(0.0);
  float lineW = (0.07 + 0.05 * uPress) * (1.0 - 0.6 * pow(at, 4.0));

  if (at <= 1.0 && open > 0.02 && p.y < upper && p.y > lower) {
    col = vec4(uCavity, 1.0);
    float th = min(0.34, open * 0.9) * uTeethUp;
    if (p.y > upper - th) col = vec4(uTeeth, 1.0);
    float tl = min(0.26, open * 0.6) * uTeethDown;
    if (p.y < lower + tl) col = vec4(uTeeth * 0.95, 1.0);
    if (uFangs > 0.01 && at > 0.42 && at < 0.62 && p.y > upper - th - uFangs * 0.3 * (1.0 - abs(at - 0.52) * 10.0)) col = vec4(uTeeth, 1.0);
    vec2 tq = vec2(t / 0.62, (p.y - (lower + open * (0.18 + 0.5 * uTongue))) / max(open * 0.45, 0.02));
    if (length(tq) < 1.0 && p.y < upper - th * 0.8) col = vec4(uTongueCol, 1.0);
    float edge = min(p.y - lower, upper - p.y);
    if (edge < 0.035) col = vec4(uLine, 1.0);
  } else if (at <= 1.08) {
    float d = abs(p.y - mid);
    if (open <= 0.02 && d < lineW * (at > 1.0 ? (1.08 - at) / 0.08 : 1.0)) col = vec4(uLine, 1.0);
    float lowerLip = lower - uLipLower * 0.28 * env;
    if (at < 1.0 && p.y < lower && p.y > lowerLip - 0.02) {
      float f = smoothstep(lowerLip - 0.02, lowerLip + 0.08, p.y);
      col = max(col, vec4(uLip, 0.55 * f * (1.0 - at * 0.7)));
      if (uBite > 0.01 && p.y > lower - 0.08 * uBite) col = vec4(uTeeth, 1.0);
    }
    float upperLip = upper + uLipUpper * 0.12 * env;
    if (at < 1.0 && p.y > upper && p.y < upperLip && col.a < 0.9) col = vec4(uLip * 0.85, 0.5);
  }
  if (uTongueFwd > 0.01 && at < 0.35 && p.y < mid + 0.02 && p.y > mid - 0.2 * uTongueFwd) col = vec4(uTongueCol, 1.0);
  if (col.a < 0.01) discard;
  vec3 c = col.rgb;
  float lum = dot(c, vec3(0.299, 0.587, 0.114));
  c = mix(vec3(lum), c, uSaturation) * uBrightness;
  c = mix(c, vec3(0.3, 0.78, 1.0), uSelect * 0.42);
  gl_FragColor = vec4(c, col.a);
  #include <colorspace_fragment>
}
`;

export function mouthMaterial(): THREE.ShaderMaterial {
  return new THREE.ShaderMaterial({
    vertexShader: eyeVertex,
    fragmentShader: mouthFragment,
    transparent: true,
    depthWrite: false,
    polygonOffset: true,
    polygonOffsetFactor: -2,
    uniforms: {
      uHalfW: { value: 0.7 },
      uCornerL: { value: 0 },
      uCornerR: { value: 0 },
      uOpenUp: { value: 0 },
      uOpenDown: { value: 0 },
      uExp: { value: 0.6 },
      uShift: { value: 0 },
      uTeethUp: { value: 1 },
      uTeethDown: { value: 0 },
      uTongue: { value: 0 },
      uTongueFwd: { value: 0 },
      uLipUpper: { value: 0.5 },
      uLipLower: { value: 0.6 },
      uPress: { value: 0 },
      uBite: { value: 0 },
      uFangs: { value: 0 },
      uLip: { value: new THREE.Color('#d98a86') },
      uLine: { value: new THREE.Color('#5a2a26') },
      uCavity: { value: new THREE.Color('#6a1e24') },
      uTeeth: { value: new THREE.Color('#fbf8f2') },
      uTongueCol: { value: new THREE.Color('#d8646a') },
      uSelect: { value: 0 },
      uSaturation: sharedUniforms.uSaturation,
      uBrightness: sharedUniforms.uBrightness,
    },
  });
}

type W = Record<string, number>;
const g = (w: W, k: string) => w[k] ?? 0;

export interface MouthSolve {
  halfW: number;
  cornerL: number;
  cornerR: number;
  openUp: number;
  openDown: number;
  exp: number;
  shift: number;
  teethUp: number;
  teethDown: number;
  tongue: number;
  tongueFwd: number;
  press: number;
  bite: number;
  jaw: number;
}

/** Turns jaw, viseme, and emotion weights into one continuous mouth shape. */
export function solveMouth(w: W, restCorner: number, widthBase: number): MouthSolve {
  const jaw = Math.min(1, g(w, 'PF-JawOpen') + 0.3 * g(w, 'PF-SmileOpenJaw') + 0.35 * g(w, 'PF-FrownOpen') + 0.3 * g(w, 'PF-Surprise') + 0.2 * g(w, 'PF-Cry'));
  const lipPart = 0.12 * g(w, 'PF-VisSmall') + 0.2 * g(w, 'PF-VisMid') + 0.06 * g(w, 'PF-VisEE') + 0.05 * g(w, 'PF-VisIH') + 0.1 * g(w, 'PF-VisSZ') + 0.12 * g(w, 'PF-Snarl') + 0.1 * g(w, 'PF-Grimace') + 0.05 * g(w, 'PF-VisL');
  const closeForce = Math.max(g(w, 'PF-VisMBP'), g(w, 'PF-Press') * 0.9, g(w, 'PF-VisFV') * 0.6);
  let open = Math.max(0, (jaw * 0.75 + lipPart) * (1 - closeForce * 0.85));
  const round = g(w, 'PF-VisOH') * 0.8 + g(w, 'PF-VisOO') + g(w, 'PF-Pout') * 0.7 + g(w, 'PF-Surprise') * 0.4;
  const wide = g(w, 'PF-VisEE') * 0.7 + g(w, 'PF-VisIH') * 0.45 + g(w, 'PF-VisWide') * 0.35 + g(w, 'PF-Grimace') * 0.7 + g(w, 'PF-SmileClosed') * 0.3 + g(w, 'PF-SmileOpenJaw') * 0.35 + g(w, 'PF-VisSZ') * 0.3;
  if (g(w, 'PF-VisOO') > 0) open = Math.max(open, 0.1 * g(w, 'PF-VisOO'));
  const halfW = Math.min(0.97, Math.max(0.2, widthBase * (1 + 0.32 * wide - 0.45 * round - 0.1 * g(w, 'PF-Press'))));
  const smile = g(w, 'PF-SmileClosed') * 0.9 + g(w, 'PF-SmileOpenJaw') * 0.8 + g(w, 'PF-VisEE') * 0.1;
  const frown = g(w, 'PF-Frown') * 0.8 + g(w, 'PF-FrownOpen') * 0.8 + g(w, 'PF-Cry') * 0.7 + g(w, 'PF-Disgust') * 0.4 + g(w, 'PF-Grimace') * 0.2;
  const cornerL = restCorner + 0.34 * (smile - frown) + 0.42 * g(w, 'PF-Smirk_L') + 0.1 * g(w, 'PF-Disgust');
  const cornerR = restCorner + 0.34 * (smile - frown) + 0.42 * g(w, 'PF-Smirk_R') - 0.08 * g(w, 'PF-Disgust');
  const shift = 0.22 * (g(w, 'PF-MouthSide_L') - g(w, 'PF-MouthSide_R')) + 0.08 * (g(w, 'PF-Smirk_L') - g(w, 'PF-Smirk_R'));
  const upShare = 0.35 + 0.25 * g(w, 'PF-Snarl') + 0.15 * g(w, 'PF-VisWide');
  const exp = Math.max(0.2, 0.55 + 0.5 * round - 0.3 * wide - 0.2 * g(w, 'PF-VisWide'));
  return {
    halfW,
    cornerL,
    cornerR,
    openUp: open * upShare,
    openDown: open * (1 - upShare),
    exp,
    shift,
    teethUp: Math.min(1, 0.35 + g(w, 'PF-VisEE') + g(w, 'PF-VisSZ') + g(w, 'PF-Grimace') + g(w, 'PF-Snarl') + g(w, 'PF-SmileOpenJaw') * 0.8 + g(w, 'PF-VisFV')),
    teethDown: Math.min(1, g(w, 'PF-Grimace') + g(w, 'PF-VisSZ') * 0.7 + g(w, 'PF-VisEE') * 0.5),
    tongue: Math.min(1, g(w, 'PF-TongueL') + g(w, 'PF-TongueRest') * 0.3),
    tongueFwd: g(w, 'PF-TongueTh'),
    press: Math.max(g(w, 'PF-Press'), g(w, 'PF-VisMBP') * 0.6),
    bite: Math.max(g(w, 'PF-LipBite'), g(w, 'PF-VisFV')),
    jaw,
  };
}

export function applyMouthUniforms(mat: THREE.ShaderMaterial, s: MouthSolve) {
  const u = mat.uniforms;
  u.uHalfW.value = s.halfW;
  u.uCornerL.value = s.cornerL;
  u.uCornerR.value = s.cornerR;
  u.uOpenUp.value = s.openUp;
  u.uOpenDown.value = s.openDown;
  u.uExp.value = s.exp;
  u.uShift.value = s.shift;
  u.uTeethUp.value = s.teethUp;
  u.uTeethDown.value = s.teethDown;
  u.uTongue.value = s.tongue;
  u.uTongueFwd.value = s.tongueFwd;
  u.uPress.value = s.press;
  u.uBite.value = s.bite;
}

export interface EyeSolve {
  upper: number;
  lower: number;
  squeeze: number;
}

/** Lid state for one side. Gaze down lowers the upper lid so the iris stays under it. */
export function solveEye(w: W, side: 'L' | 'R', hood: number, gazeY: number): EyeSolve {
  const blink = g(w, `PF-Blink_${side}`);
  const upper = 0.1 + hood * 0.18 + blink * 0.9 + g(w, `PF-LidUpperDown_${side}`) * 0.5 + g(w, `PF-Squint_${side}`) * 0.22 - g(w, `PF-EyeWide_${side}`) * 0.22 + Math.max(0, -gazeY) * 0.18 - Math.max(0, gazeY) * 0.06;
  const lower = g(w, `PF-Squint_${side}`) * 0.4 + g(w, `PF-LidLowerUp_${side}`) * 0.55 + blink * 0.12 + g(w, `PF-Squeeze_${side}`) * 0.2 + g(w, 'PF-SmileOpenJaw') * 0.12 - g(w, `PF-EyeWide_${side}`) * 0.05;
  const squeeze = Math.min(1, g(w, `PF-Squeeze_${side}`) * 1.2 + g(w, 'PF-SmileOpenJaw') * 0.45 * blink);
  return { upper: Math.min(1, upper), lower: Math.max(0, Math.min(1, lower)), squeeze };
}

export interface BrowShape {
  inner: [number, number];
  mid: [number, number];
  outer: [number, number];
}

/** Moves the three brow points from their identity placement by the performance keys. */
export function solveBrow(w: W, side: 'L' | 'R', rest: BrowShape, unit: number): BrowShape {
  const raise = g(w, `PF-BrowRaise_${side}`);
  const inUp = g(w, `PF-BrowInnerUp_${side}`);
  const outUp = g(w, `PF-BrowOuterUp_${side}`);
  const lower = g(w, `PF-BrowLower_${side}`);
  const furrow = g(w, `PF-BrowFurrow_${side}`);
  const sad = g(w, `PF-BrowSad_${side}`);
  const surprise = g(w, 'PF-Surprise') * 0.4;
  const dy = (raise + surprise) * 0.55 - lower * 0.45;
  return {
    inner: [rest.inner[0] - furrow * 0.25 * unit, rest.inner[1] + (dy + inUp * 0.6 + sad * 0.55 - furrow * 0.3) * unit],
    mid: [rest.mid[0], rest.mid[1] + (dy + inUp * 0.2 + outUp * 0.25 + sad * 0.05) * unit],
    outer: [rest.outer[0], rest.outer[1] + (dy * 0.8 + outUp * 0.55 - sad * 0.3 + furrow * 0.05) * unit],
  };
}

/** Rebuilds a brow ribbon on the head surface. The geometry keeps a fixed vertex count. */
export class BrowRibbon {
  geometry: THREE.BufferGeometry;
  mesh: THREE.Mesh;
  private samples = 14;
  constructor(private surface: HeadSurface, reg: PartRegistry, parent: THREE.Object3D, mat: THREE.Material, private thickness: number) {
    const n = this.samples;
    this.geometry = new THREE.BufferGeometry();
    this.geometry.setAttribute('position', new THREE.Float32BufferAttribute(new Float32Array((n + 1) * 2 * 3), 3));
    this.geometry.setAttribute('normal', new THREE.Float32BufferAttribute(new Float32Array((n + 1) * 2 * 3), 3));
    const uv: number[] = [];
    const idx: number[] = [];
    for (let i = 0; i <= n; i += 1) {
      uv.push(i / n, 0, i / n, 1);
      if (i < n) {
        const a = i * 2;
        idx.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
      }
    }
    this.geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    this.geometry.setIndex(idx);
    this.mesh = reg.add(parent, this.geometry, mat, { region: 'brows' });
  }

  update(shape: BrowShape) {
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(shape.inner[0], shape.inner[1], 0),
      new THREE.Vector3(shape.mid[0], shape.mid[1], 0),
      new THREE.Vector3(shape.outer[0], shape.outer[1], 0),
    ]);
    const pos = this.geometry.attributes.position as THREE.BufferAttribute;
    const nrm = this.geometry.attributes.normal as THREE.BufferAttribute;
    const p = new THREE.Vector3();
    const n = new THREE.Vector3();
    for (let i = 0; i <= this.samples; i += 1) {
      const t = i / this.samples;
      const c = curve.getPoint(t);
      const tan = curve.getTangent(t);
      const th = this.thickness * (1 - 0.65 * t) * (0.6 + 0.4 * Math.sin(Math.min(1, t * 3 + 0.3) * Math.PI * 0.5));
      const nx = -tan.y;
      const ny = tan.x;
      for (let s = 0; s < 2; s += 1) {
        const off = s === 0 ? -th * 0.5 : th * 0.5;
        this.surface.hit(c.x + nx * off, c.y + ny * off, p, n);
        p.addScaledVector(n, 0.0016);
        pos.setXYZ(i * 2 + s, p.x, p.y, p.z);
        nrm.setXYZ(i * 2 + s, n.x, n.y, n.z);
      }
    }
    pos.needsUpdate = true;
    nrm.needsUpdate = true;
    this.geometry.computeBoundingSphere();
  }
}

export function eyeGeometry(surface: HeadSurface, cx: number, cy: number, w: number, h: number, tilt: number, almond: number, side: 1 | -1) {
  return conformGrid(
    surface,
    new THREE.Vector2(cx, cy),
    w,
    h,
    20,
    14,
    0.0012,
    (u, v) => {
      const r = Math.max(Math.abs(u), Math.abs(v));
      if (r < 1e-6) return [0, 0];
      const a = Math.atan2(v, u);
      let x = Math.cos(a) * r;
      let y = Math.sin(a) * r;
      const topScale = 1 + almond * 0.1;
      const botScale = 0.82 - almond * 0.2;
      y *= y > 0 ? topScale : botScale;
      y *= 1 - almond * 0.35 * x * x;
      y += (x * side) * 0.08 * almond;
      return [x, y];
    },
    tilt * side,
  );
}

export function squareToDiscUv(geom: THREE.BufferGeometry) {
  const uv = geom.attributes.uv as THREE.BufferAttribute;
  for (let i = 0; i < uv.count; i += 1) {
    const u = uv.getX(i) * 2 - 1;
    const v = uv.getY(i) * 2 - 1;
    const r = Math.max(Math.abs(u), Math.abs(v));
    if (r < 1e-6) {
      uv.setXY(i, 0.5, 0.5);
      continue;
    }
    const a = Math.atan2(v, u);
    uv.setXY(i, 0.5 + Math.cos(a) * r * 0.5, 0.5 + Math.sin(a) * r * 0.5);
  }
  uv.needsUpdate = true;
}
