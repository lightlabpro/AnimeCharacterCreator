import * as THREE from 'three';
import type { RenderExtras, StyleSettings } from '../model/presets';
import { ensureOutlineNormals } from './hatch';
import { sharedUniforms, ToonMaterial } from './toonMaterial';

const quadVertex = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`;

/** Inverted hull: back faces pushed out along the smoothed normal by a fixed number of pixels. */
const hullVertex = /* glsl */ `
#include <common>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
attribute vec3 outlineNormal;
uniform float uHullWidth;
uniform vec2 uRes;
void main() {
  vec3 objectNormal = outlineNormal;
  #include <morphinstance_vertex>
  #include <morphnormal_vertex>
  #include <skinbase_vertex>
  #include <skinnormal_vertex>
  #include <begin_vertex>
  #include <morphtarget_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
  // Slightly behind the surface, so open sheets such as capes and cards hide their own hull.
  gl_Position = projectionMatrix * vec4(mvPosition.xyz * 1.004, 1.0);
  vec3 nv = normalize(normalMatrix * objectNormal);
  vec2 dir = (projectionMatrix * vec4(nv, 0.0)).xy;
  float len = length(dir);
  if (len > 1e-5) gl_Position.xy += dir / len * uHullWidth * 2.0 / uRes * gl_Position.w;
}
`;

/** Black with zero alpha marks a line pixel. The composite pass colors it by the nearest surface. */
const hullFragment = /* glsl */ `void main() { gl_FragColor = vec4(0.0); }`;

const prefilterFragment = /* glsl */ `
uniform sampler2D tColor;
uniform float uDiffusion;
uniform float uBloom;
varying vec2 vUv;
void main() {
  vec4 c = texture2D(tColor, vUv);
  float m = max(c.r, max(c.g, c.b));
  vec3 keep = vec3(c.r >= m - 1e-4 ? c.r : c.r * 0.2, c.g >= m - 1e-4 ? c.g : c.g * 0.2, c.b >= m - 1e-4 ? c.b : c.b * 0.2);
  vec3 diff = keep * smoothstep(0.8, 1.2, m) * uDiffusion;
  vec3 bl = max(c.rgb - 1.0, 0.0) * uBloom;
  gl_FragColor = vec4(diff + bl, 1.0);
}
`;

const blurFragment = /* glsl */ `
uniform sampler2D tSrc;
uniform vec2 uDir;
varying vec2 vUv;
void main() {
  vec3 c = texture2D(tSrc, vUv).rgb * 0.227027;
  c += (texture2D(tSrc, vUv + uDir).rgb + texture2D(tSrc, vUv - uDir).rgb) * 0.1945946;
  c += (texture2D(tSrc, vUv + uDir * 2.0).rgb + texture2D(tSrc, vUv - uDir * 2.0).rgb) * 0.1216216;
  c += (texture2D(tSrc, vUv + uDir * 3.0).rgb + texture2D(tSrc, vUv - uDir * 3.0).rgb) * 0.054054;
  c += (texture2D(tSrc, vUv + uDir * 4.0).rgb + texture2D(tSrc, vUv - uDir * 4.0).rgb) * 0.016216;
  gl_FragColor = vec4(c, 1.0);
}
`;

const compositeFragment = /* glsl */ `
uniform sampler2D tColor;
uniform sampler2D tDepth;
uniform sampler2D tNormal;
uniform sampler2D tGlow;
uniform vec2 uTexel;
uniform vec2 uRes;
uniform float uNear;
uniform float uFar;
uniform float uWidth;
uniform float uDark;
uniform float uLineMix;
uniform float uHull;
uniform float uCreases;
uniform float uSens;
uniform float uJitter;
uniform float uInk;
uniform vec2 uLightScreen;
uniform vec3 uLightColor;
uniform vec3 uFillColor;
uniform float uRimLit;
uniform float uRimShadow;
uniform float uRimWidth;
uniform float uKuwa;
uniform float uGlowOn;
uniform float uFlare;
uniform float uPara;
uniform float uFog;
uniform float uVignette;
uniform float uGrain;
uniform float uParticles;
uniform float uDof;
uniform float uFocus;
uniform vec3 uSplitShadow;
uniform vec3 uSplitHi;
uniform float uSplit;
uniform vec3 uBgTop;
uniform vec3 uBgBottom;
uniform float uTransparent;
uniform float uTime;
varying vec2 vUv;

float lin(float d) {
  float z = d * 2.0 - 1.0;
  return 2.0 * uNear * uFar / (uFar + uNear - z * (uFar - uNear));
}
float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
float lum(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

void sector(vec2 uv, vec2 dir, float r, inout vec3 bestMean, inout float bestVar) {
  vec3 m = vec3(0.0);
  vec3 s = vec3(0.0);
  for (int j = 0; j <= 2; j++) {
    for (int i = 0; i <= 2; i++) {
      vec3 c = texture2D(tColor, uv + vec2(float(i), float(j)) * dir * (r * 0.5) * uTexel).rgb;
      m += c;
      s += c * c;
    }
  }
  m /= 9.0;
  vec3 v = s / 9.0 - m * m;
  float vs = v.r + v.g + v.b;
  if (vs < bestVar) {
    bestVar = vs;
    bestMean = m;
  }
}

void main() {
  vec4 c0 = texture2D(tColor, vUv);
  float d0 = texture2D(tDepth, vUv).r;
  float z0 = lin(d0);

  if (uKuwa > 0.0 && c0.a > 0.99) {
    vec3 bm = c0.rgb;
    float bv = 1e9;
    sector(vUv, vec2(-1.0, -1.0), uKuwa, bm, bv);
    sector(vUv, vec2(1.0, -1.0), uKuwa, bm, bv);
    sector(vUv, vec2(-1.0, 1.0), uKuwa, bm, bv);
    sector(vUv, vec2(1.0, 1.0), uKuwa, bm, bv);
    c0.rgb = bm;
  }

  if (uDof > 0.0) {
    float coc = clamp(abs(z0 - uFocus) / max(uFocus, 0.1), 0.0, 1.0) * uDof * 8.0;
    if (coc > 0.5) {
      vec4 acc = c0;
      for (int i = 0; i < 12; i++) {
        float a = float(i) * 2.39996;
        float rr = sqrt(float(i) + 0.5) / sqrt(12.0);
        acc += texture2D(tColor, vUv + vec2(cos(a), sin(a)) * rr * coc * uTexel);
      }
      c0 = acc / 13.0;
    }
  }

  // Lines: ink layer offset, then a stepped wobble for sketchy looks.
  vec2 luv = vUv + uInk * uTexel * vec2(0.7, -0.7);
  if (uJitter > 0.0) {
    float t = floor(uTime * 6.0);
    vec2 q = luv * uRes / 30.0;
    luv += (vec2(vnoise(q + t * 7.1), vnoise(q + 13.3 + t * 3.7)) - 0.5) * 2.0 * uJitter * uTexel;
  }
  float dl = texture2D(tDepth, luv).r;
  float zl = lin(dl);
  float best = dl;
  vec2 bestUv = luv;
  float edge = 0.0;
  vec2 offs[8];
  offs[0] = vec2(1.0, 0.0); offs[1] = vec2(-1.0, 0.0); offs[2] = vec2(0.0, 1.0); offs[3] = vec2(0.0, -1.0);
  offs[4] = vec2(0.7, 0.7); offs[5] = vec2(-0.7, 0.7); offs[6] = vec2(0.7, -0.7); offs[7] = vec2(-0.7, -0.7);
  float thr = 0.03 / max(uSens, 0.05);
  for (int i = 0; i < 8; i++) {
    vec2 uv = luv + offs[i] * uTexel * uWidth;
    float d = texture2D(tDepth, uv).r;
    float z = lin(d);
    float diff = abs(z - zl) / max(min(z, zl), 1e-3);
    edge = max(edge, smoothstep(thr, thr * 2.6, diff));
    if (d < best) { best = d; bestUv = uv; }
  }
  if (best >= 1.0) edge = 0.0;
  vec3 srcCol = texture2D(tColor, bestUv).rgb;

  if (uCreases > 0.0) {
    vec4 n0 = texture2D(tNormal, luv);
    if (n0.a > 0.5) {
      vec3 a0 = n0.xyz * 2.0 - 1.0;
      for (int i = 0; i < 4; i++) {
        vec4 ni = texture2D(tNormal, luv + offs[i] * uTexel * max(uWidth, 1.0));
        if (ni.a > 0.5) edge = max(edge, smoothstep(0.35, 0.6, (1.0 - dot(a0, ni.xyz * 2.0 - 1.0)) * uCreases * uSens));
      }
    }
  }

  vec4 cl = texture2D(tColor, luv);
  if (uHull > 0.0 && dl < 1.0 && cl.a < 0.02) {
    edge = 1.0;
    bool found = false;
    for (int r = 1; r <= 4; r++) {
      for (int i = 0; i < 8; i++) {
        if (found) break;
        vec4 s = texture2D(tColor, luv + offs[i] * uTexel * float(r) * max(uHull * 0.5, 1.0));
        if (s.a > 0.5) { srcCol = s.rgb; found = true; }
      }
    }
  }
  vec3 lineCol = mix(vec3(0.06, 0.05, 0.07), srcCol * uDark, uLineMix);

  float a = c0.a;
  vec3 surf = uTransparent > 0.5 ? (a > 0.001 ? c0.rgb / a : vec3(0.0)) : c0.rgb;

  // Screen-space rim of constant width, on the side facing the light and, weaker, the side away from it.
  if (a > 0.5 && d0 < 1.0 && (uRimLit > 0.0 || uRimShadow > 0.0)) {
    vec2 off = uLightScreen * uRimWidth * uTexel;
    float dL = texture2D(tDepth, vUv + off).r;
    float dS = texture2D(tDepth, vUv - off).r;
    float rimL = smoothstep(0.03, 0.08, (lin(dL) - z0) / z0);
    float rimS = smoothstep(0.03, 0.08, (lin(dS) - z0) / z0);
    surf += rimL * uRimLit * (surf * 0.5 + uLightColor * 0.35) * (uTransparent > 0.5 ? 1.0 : a);
    surf += rimS * uRimShadow * uFillColor * 0.4 * (uTransparent > 0.5 ? 1.0 : a);
  }

  vec3 bg = mix(uBgBottom, uBgTop, smoothstep(0.0, 1.0, vUv.y));
  bg *= 1.0 - 0.25 * length(vUv - vec2(0.5, 0.55));
  if (uFog > 0.0 && d0 < 1.0) {
    float f = uFog * smoothstep(1.5, 9.0, z0);
    vec3 fogCol = mix(uBgBottom, uBgTop, 0.65) * (uTransparent > 0.5 ? 1.0 : a);
    surf = mix(surf, fogCol, f);
  }

  vec3 col = uTransparent > 0.5 ? surf : bg * (1.0 - a) + surf;
  float alpha = uTransparent > 0.5 ? a : 1.0;
  col = mix(col, lineCol, edge);
  alpha = max(alpha, edge);

  if (uGlowOn > 0.0) {
    vec3 gl = texture2D(tGlow, vUv).rgb;
    col += gl;
    alpha = max(alpha, clamp(lum(gl) * 2.0, 0.0, 1.0));
  }

  if (uTransparent < 0.5) {
    vec2 cc = vUv - 0.5;
    float rr = length(cc * vec2(uRes.x / uRes.y, 1.0));
    col += uFlare * vec3(1.0, 0.86, 0.66) * smoothstep(0.35, 1.0, rr) * 0.5;
    col *= 1.0 - uPara * smoothstep(0.55, 1.0, vUv.y) * 0.55;
    float l = lum(col);
    col += (mix(uSplitShadow, uSplitHi, smoothstep(0.15, 0.85, l)) - 0.5) * uSplit;
    col *= 1.0 - uVignette * smoothstep(0.3, 1.0, rr);
    if (uParticles > 0.0) {
      for (int k = 0; k < 2; k++) {
        float sc = k == 0 ? 16.0 : 30.0;
        vec2 p = vUv * vec2(uRes.x / uRes.y, 1.0) * sc;
        p.y -= uTime * (0.2 + 0.25 * float(k));
        p.x += sin(uTime * 0.3 + float(k) * 2.0) * 0.4;
        vec2 cell = floor(p);
        vec2 f = fract(p) - 0.5;
        float h = hash(cell + float(k) * 19.0);
        if (h > 0.84) {
          vec2 o = (vec2(hash(cell + 3.1), hash(cell + 7.7)) - 0.5) * 0.6;
          float tw = 0.5 + 0.5 * sin(uTime * 2.0 + h * 40.0);
          col += mix(vec3(0.6, 0.85, 1.0), vec3(1.0, 0.9, 0.6), hash(cell + 1.3)) * (1.0 - smoothstep(0.0, 0.08, length(f - o))) * tw * uParticles;
        }
      }
    }
  }
  if (uGrain > 0.0) col += (hash(vUv * uRes + fract(uTime) * 91.0) - 0.5) * uGrain * alpha;

  gl_FragColor = vec4(col, alpha);
  #include <colorspace_fragment>
}
`;

export interface PostFrame {
  time: number;
  /** Distance from the camera to what it looks at, for depth of field. */
  focus: number;
  /** Edge sensitivity, 1 for humanoids. The dragon uses less so it does not drown in lines. */
  sensitivity: number;
}

/**
 * The shared render path for the viewport and thumbnails: scene color and depth, an inverted-hull pass,
 * a normal pass for creases, a half-resolution glow, then one composite with lines, rim, and grading.
 */
export class PostPipeline {
  private rtScene: THREE.WebGLRenderTarget;
  private rtNormal: THREE.WebGLRenderTarget;
  private rtGlowA: THREE.WebGLRenderTarget;
  private rtGlowB: THREE.WebGLRenderTarget;
  private hullMat: THREE.ShaderMaterial;
  private normalMat = new THREE.MeshNormalMaterial();
  private prefilter: THREE.ShaderMaterial;
  private blur: THREE.ShaderMaterial;
  private composite: THREE.ShaderMaterial;
  private quad: THREE.Mesh;
  private quadScene = new THREE.Scene();
  private quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  private style: (StyleSettings & RenderExtras) | null = null;
  private pixelRatio = 1;
  private hidden: THREE.Object3D[] = [];

  constructor(private renderer: THREE.WebGLRenderer, private transparent: boolean) {
    const rtOpts = { type: THREE.HalfFloatType, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter };
    this.rtScene = new THREE.WebGLRenderTarget(4, 4, { ...rtOpts, depthTexture: new THREE.DepthTexture(4, 4) });
    this.rtScene.depthTexture!.type = THREE.UnsignedIntType;
    this.rtNormal = new THREE.WebGLRenderTarget(4, 4, { type: THREE.HalfFloatType });
    this.rtGlowA = new THREE.WebGLRenderTarget(2, 2, rtOpts);
    this.rtGlowB = new THREE.WebGLRenderTarget(2, 2, rtOpts);
    this.hullMat = new THREE.ShaderMaterial({
      vertexShader: hullVertex,
      fragmentShader: hullFragment,
      side: THREE.BackSide,
      blending: THREE.NoBlending,
      uniforms: { uHullWidth: { value: 1 }, uRes: { value: new THREE.Vector2(4, 4) } },
    });
    const quadMat = (fragmentShader: string, uniforms: Record<string, THREE.IUniform>) =>
      new THREE.ShaderMaterial({ vertexShader: quadVertex, fragmentShader, uniforms, depthTest: false, depthWrite: false });
    this.prefilter = quadMat(prefilterFragment, { tColor: { value: this.rtScene.texture }, uDiffusion: { value: 0 }, uBloom: { value: 0 } });
    this.blur = quadMat(blurFragment, { tSrc: { value: null }, uDir: { value: new THREE.Vector2() } });
    this.composite = quadMat(compositeFragment, {
      tColor: { value: this.rtScene.texture },
      tDepth: { value: this.rtScene.depthTexture },
      tNormal: { value: this.rtNormal.texture },
      tGlow: { value: this.rtGlowA.texture },
      uTexel: { value: new THREE.Vector2(1 / 4, 1 / 4) },
      uRes: { value: new THREE.Vector2(4, 4) },
      uNear: { value: 0.05 },
      uFar: { value: 60 },
      uWidth: { value: 1 },
      uDark: { value: 0.4 },
      uLineMix: { value: 1 },
      uHull: { value: 0 },
      uCreases: { value: 0 },
      uSens: { value: 1 },
      uJitter: { value: 0 },
      uInk: { value: 0 },
      uLightScreen: { value: new THREE.Vector2(0.5, 0.8) },
      uLightColor: sharedUniforms.uLightColor,
      uFillColor: sharedUniforms.uFillColor,
      uRimLit: { value: 0 },
      uRimShadow: { value: 0 },
      uRimWidth: { value: 2 },
      uKuwa: { value: 0 },
      uGlowOn: { value: 0 },
      uFlare: { value: 0 },
      uPara: { value: 0 },
      uFog: { value: 0 },
      uVignette: { value: 0 },
      uGrain: { value: 0 },
      uParticles: { value: 0 },
      uDof: { value: 0 },
      uFocus: { value: 4 },
      uSplitShadow: { value: new THREE.Color() },
      uSplitHi: { value: new THREE.Color() },
      uSplit: { value: 0 },
      uBgTop: { value: new THREE.Color('#58708c') },
      uBgBottom: { value: new THREE.Color('#1d2330') },
      uTransparent: { value: transparent ? 1 : 0 },
      uTime: { value: 0 },
    });
    this.composite.blending = THREE.NoBlending;
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), this.composite);
    this.quad.frustumCulled = false;
    this.quadScene.add(this.quad);
  }

  /** Size in device pixels. */
  setSize(w: number, h: number, pixelRatio = 1) {
    this.pixelRatio = pixelRatio;
    this.rtScene.setSize(w, h);
    this.rtNormal.setSize(w, h);
    const hw = Math.max(1, Math.floor(w / 2));
    const hh = Math.max(1, Math.floor(h / 2));
    this.rtGlowA.setSize(hw, hh);
    this.rtGlowB.setSize(hw, hh);
    const u = this.composite.uniforms;
    u.uTexel.value.set(1 / w, 1 / h);
    u.uRes.value.set(w, h);
    this.hullMat.uniforms.uRes.value.set(w, h);
    if (this.style) this.setStyle(this.style);
  }

  setStyle(s: StyleSettings & RenderExtras) {
    this.style = s;
    const pr = this.pixelRatio;
    const u = this.composite.uniforms;
    u.uWidth.value = s.outline * pr;
    u.uDark.value = s.outlineDark;
    u.uLineMix.value = s.lineColorMix;
    u.uHull.value = s.hull * pr;
    u.uCreases.value = s.creases;
    u.uJitter.value = s.lineJitter * pr;
    u.uInk.value = s.inkOffset * pr;
    u.uRimLit.value = s.screenRim.lit;
    u.uRimShadow.value = s.screenRim.shadow;
    u.uRimWidth.value = s.screenRim.width * pr;
    u.uKuwa.value = this.transparent ? 0 : s.kuwahara * pr;
    u.uGlowOn.value = s.diffusion + s.bloom > 0 ? 1 : 0;
    u.uFlare.value = s.flare;
    u.uPara.value = s.para;
    u.uFog.value = s.fog;
    u.uVignette.value = s.vignette;
    u.uGrain.value = this.transparent ? 0 : s.grain;
    u.uParticles.value = s.particles;
    u.uDof.value = this.transparent ? 0 : s.dof;
    u.uSplitShadow.value.set(s.splitTone.shadow);
    u.uSplitHi.value.set(s.splitTone.highlight);
    u.uSplit.value = s.splitTone.amount;
    u.uBgTop.value.set(s.background[0]);
    u.uBgBottom.value.set(s.background[1]);
    this.hullMat.uniforms.uHullWidth.value = s.hull * pr;
    this.prefilter.uniforms.uDiffusion.value = s.diffusion;
    this.prefilter.uniforms.uBloom.value = s.bloom;
  }

  /** Hides everything a pass should skip and returns them for restore. */
  private hideFor(scene: THREE.Scene, keep: (m: THREE.Mesh) => boolean) {
    this.hidden.length = 0;
    scene.traverse((o) => {
      const m = o as THREE.Mesh;
      if (!m.isMesh || !m.visible) return;
      if (keep(m)) return;
      m.visible = false;
      this.hidden.push(m);
    });
  }

  private restore() {
    for (const o of this.hidden) o.visible = true;
    this.hidden.length = 0;
  }

  render(scene: THREE.Scene, camera: THREE.PerspectiveCamera, frame: PostFrame, target: THREE.WebGLRenderTarget | null = null) {
    const s = this.style;
    if (!s) return;
    const r = this.renderer;
    const auto = r.autoClear;
    sharedUniforms.uTime.value = frame.time;
    const u = this.composite.uniforms;
    u.uNear.value = camera.near;
    u.uFar.value = camera.far;
    u.uTime.value = frame.time;
    u.uFocus.value = frame.focus;
    u.uSens.value = frame.sensitivity;
    const ld = sharedUniforms.uLightDir.value;
    u.uLightScreen.value.set(ld.x, ld.y).normalize();

    r.setRenderTarget(this.rtScene);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(scene, camera);

    if (s.hull > 0) {
      this.hideFor(scene, (m) => {
        const mat = m.material as THREE.Material;
        const ok = mat instanceof ToonMaterial && !mat.transparent && !m.userData.noHull;
        if (ok) ensureOutlineNormals(m.geometry);
        return ok;
      });
      r.autoClear = false;
      scene.overrideMaterial = this.hullMat;
      r.render(scene, camera);
      scene.overrideMaterial = null;
      r.autoClear = auto;
      this.restore();
    }

    if (s.creases > 0) {
      this.hideFor(scene, (m) => {
        const mat = m.material as THREE.Material;
        return !mat.transparent && !m.userData.outlineShell;
      });
      r.setRenderTarget(this.rtNormal);
      r.setClearColor(0x000000, 0);
      r.clear();
      scene.overrideMaterial = this.normalMat;
      r.render(scene, camera);
      scene.overrideMaterial = null;
      this.restore();
    }

    if (s.diffusion + s.bloom > 0) {
      const w = this.rtGlowA.width;
      const h = this.rtGlowA.height;
      this.quad.material = this.prefilter;
      r.setRenderTarget(this.rtGlowA);
      r.render(this.quadScene, this.quadCam);
      this.quad.material = this.blur;
      for (const spread of [1, 2.2]) {
        this.blur.uniforms.tSrc.value = this.rtGlowA.texture;
        this.blur.uniforms.uDir.value.set(spread / w, 0);
        r.setRenderTarget(this.rtGlowB);
        r.render(this.quadScene, this.quadCam);
        this.blur.uniforms.tSrc.value = this.rtGlowB.texture;
        this.blur.uniforms.uDir.value.set(0, spread / h);
        r.setRenderTarget(this.rtGlowA);
        r.render(this.quadScene, this.quadCam);
      }
    }

    this.quad.material = this.composite;
    r.setRenderTarget(target);
    r.setClearColor(0x000000, 0);
    r.clear();
    r.render(this.quadScene, this.quadCam);
  }

  dispose() {
    this.rtScene.dispose();
    this.rtNormal.dispose();
    this.rtGlowA.dispose();
    this.rtGlowB.dispose();
    this.hullMat.dispose();
    this.normalMat.dispose();
    this.prefilter.dispose();
    this.blur.dispose();
    this.composite.dispose();
    this.quad.geometry.dispose();
  }
}
