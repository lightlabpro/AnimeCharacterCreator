import * as THREE from 'three';
import { resolveStyle, type RenderExtras, type RenderOverrides, type StyleSettings } from '../model/presets';
import type { StylePreset } from '../model/types';
import { hatchTexture } from './hatch';

const c = (hex: string) => new THREE.Color(hex);

/** Uniforms shared by every toon material so a style change reaches the whole picture at once. Directions are in view space. */
export const sharedUniforms = {
  uLightDir: { value: new THREE.Vector3(0.4, 0.6, 0.7).normalize() },
  uLightColor: { value: c('#fff6ea') },
  uBands: { value: 1 },
  uSoft: { value: 0.035 },
  uToony: { value: 0.6 },
  uShadeShift: { value: 0 },
  uPainted: { value: 0 },
  uRim: { value: 0.12 },
  uSaturation: { value: 1 },
  uBrightness: { value: 1 },
  uShadowTint: { value: new THREE.Vector3(0.74, 0.66, 0.86) },
  uShadow2Tint: { value: new THREE.Vector3(0.56, 0.48, 0.7) },
  uShadowGrade: { value: new THREE.Vector3(1, 1, 1) },
  uSpecBoost: { value: 1 },
  uEdgeHi: { value: 0.6 },
  uAmbient: { value: 0.12 },
  uAmbientDir: { value: new THREE.Vector3(0, 1, 0.25).normalize() },
  uAmbientColor: { value: c('#9ab4e0') },
  uFill: { value: 0.1 },
  uFillColor: { value: c('#b8c4ff') },
  uLight2Dir: { value: new THREE.Vector3(-0.6, 0.2, -0.5).normalize() },
  uLight2Color: { value: c('#8fb4ff') },
  uLight2Strength: { value: 0 },
  uFaceSmooth: { value: 0.75 },
  uHatch: { value: 0 },
  uHatchScale: { value: 1 },
  uHatchScreen: { value: 0 },
  uHatchTex: { value: null as THREE.Texture | null },
  uHalftone: { value: 0 },
  uSparkle: { value: 0.6 },
  uGobo: { value: 0 },
  uGlowEyes: { value: 0 },
  uTime: { value: 0 },
  uFakePos: { value: [new THREE.Vector3(), new THREE.Vector3()] },
  uFakeColor: { value: [c('#000000'), c('#000000')] },
  /** Radius, rate on lit color, rate on shadow color. Radius 0 turns the light off. */
  uFakeParams: { value: [new THREE.Vector3(), new THREE.Vector3()] },
};

let hatchReady = false;
let active: [StylePreset, RenderOverrides | undefined] | null = null;

/** Applies a style for one render (a thumbnail, say), then puts the previous one back. */
export function withStyle<T>(style: StylePreset, overrides: RenderOverrides | undefined, fn: (s: StyleSettings & RenderExtras) => T): T {
  const prev = active;
  const s = applyStyle(style, overrides);
  try {
    return fn(s);
  } finally {
    if (prev) applyStyle(prev[0], prev[1]);
  }
}

/** Pushes a style (with the person's overrides) into the shared uniforms. */
export function applyStyle(style: StylePreset, overrides?: RenderOverrides): StyleSettings & RenderExtras {
  active = [style, overrides];
  const s = resolveStyle(style, overrides);
  const u = sharedUniforms;
  if (!hatchReady) {
    u.uHatchTex.value = hatchTexture();
    hatchReady = true;
  }
  u.uBands.value = s.bands;
  u.uSoft.value = s.softness;
  u.uToony.value = s.toony;
  u.uShadeShift.value = s.shadeShift;
  u.uPainted.value = s.painted;
  u.uRim.value = s.rim;
  u.uSaturation.value = s.saturation;
  u.uBrightness.value = s.brightness;
  u.uShadowTint.value.set(...s.shadowTint);
  u.uShadow2Tint.value.set(...s.shadow2Tint);
  u.uShadowGrade.value.set(...s.shadowGrade);
  u.uSpecBoost.value = s.specBoost;
  u.uEdgeHi.value = s.edgeHighlight;
  u.uLightColor.value.set(s.lightColor);
  u.uAmbient.value = s.ambient;
  u.uAmbientColor.value.set(s.ambientColor);
  u.uFill.value = s.fill;
  u.uFillColor.value.set(s.fillColor);
  u.uLight2Dir.value.set(...s.light2.dir).normalize();
  u.uLight2Color.value.set(s.light2.color);
  u.uLight2Strength.value = s.light2.strength;
  u.uFaceSmooth.value = s.faceSmooth;
  u.uHatch.value = s.hatch;
  u.uHatchScale.value = s.hatchScale;
  u.uHatchScreen.value = s.hatchMode === 'screen' ? 1 : 0;
  u.uHalftone.value = s.halftone;
  u.uSparkle.value = s.sparkle;
  u.uGobo.value = s.gobo;
  u.uGlowEyes.value = s.glowEyes;
  return s;
}

/** Sets one of the two distance-based fake lights (world space). Radius 0 turns it off. */
export function setFakeLight(i: 0 | 1, pos: THREE.Vector3Like, color: THREE.ColorRepresentation, radius: number, rateLit = 0.3, rateShadow = 1) {
  sharedUniforms.uFakePos.value[i].set(pos.x, pos.y, pos.z);
  sharedUniforms.uFakeColor.value[i].set(color);
  sharedUniforms.uFakeParams.value[i].set(radius, rateLit, rateShadow);
}

export type ToonKind =
  | 'skin' | 'cloth' | 'leather' | 'metal' | 'hair' | 'scale' | 'fur' | 'emissive' | 'eyeWhite' | 'dark' | 'glass'
  | 'lens' | 'crystal' | 'velvet' | 'membrane';

export interface ToonOptions {
  color: THREE.ColorRepresentation;
  kind?: ToonKind;
  map?: THREE.Texture | null;
  /** Use the map's brightness as a gradient-map lookup under `color` instead of multiplying. */
  recolor?: boolean;
  /** Forced-shadow mask (glTF occlusion slot, red). Below 0.5 is forced shadow, below 0.2 the second shadow. */
  aoMap?: THREE.Texture | null;
  /** Control map (glTF metallic-roughness slot). Green sets highlight size, blue masks highlights. */
  ilmMap?: THREE.Texture | null;
  emissiveMap?: THREE.Texture | null;
  normalMap?: THREE.Texture | null;
  /** Normal maps only nudge the shadow boundary, so they stay weak. */
  normalScale?: number;
  sparkle?: number;
  /** Three colors for a view-angle gradient applied to the highlight only. */
  iridescent?: [THREE.ColorRepresentation, THREE.ColorRepresentation, THREE.ColorRepresentation];
  tip?: THREE.ColorRepresentation;
  highlight?: number;
  emissive?: THREE.ColorRepresentation;
  emissiveStrength?: number;
  opacity?: number;
  damageMap?: THREE.Texture | null;
  wrinkleMap?: THREE.Texture | null;
  side?: THREE.Side;
  wear?: number;
  face?: { map: THREE.Texture; rect: THREE.Vector4; front: number; headInv: THREE.Matrix4; radii?: THREE.Vector3 };
}

interface KindParams {
  spec: number;
  power: number;
  wrap: number;
  rim: number;
  /** Boundary softness multiplier. Only fur is soft, per Capcom's per-category rule. */
  soft: number;
  edge: number;
  /** Skin correction: lifts the threshold so moving lights never leave blotchy shadows. */
  lift: number;
  mode: number;
  sparkle: number;
}

const K = (p: Partial<KindParams>): KindParams => ({ spec: 0, power: 10, wrap: 0.2, rim: 0.8, soft: 1, edge: 0, lift: 0, mode: 0, sparkle: 0, ...p });

/** Fixed values per material category, so carapace always reads as carapace on armor and monsters alike. */
export const KIND_PARAMS: Record<ToonKind, KindParams> = {
  skin: K({ spec: 0.04, power: 24, wrap: 0.3, rim: 1, lift: 0.12 }),
  cloth: K({ power: 8, wrap: 0.2, rim: 0.7 }),
  leather: K({ spec: 0.28, power: 26, wrap: 0.15, rim: 0.8, edge: 0.35 }),
  metal: K({ spec: 0.95, power: 60, wrap: 0.05, rim: 1.1, soft: 0.6, edge: 1, sparkle: 0.15 }),
  hair: K({ power: 20, wrap: 0.25, rim: 0.9, edge: 0.15 }),
  scale: K({ spec: 0.35, power: 40, wrap: 0.15, rim: 1, soft: 0.8, edge: 0.6, sparkle: 0.12 }),
  fur: K({ power: 10, wrap: 0.35, rim: 1.2, soft: 6 }),
  emissive: K({ wrap: 1, rim: 0 }),
  eyeWhite: K({ wrap: 0.8, rim: 0 }),
  dark: K({ spec: 0.1, power: 20, wrap: 0.1, rim: 0.5 }),
  glass: K({ spec: 1, power: 90, wrap: 0.3, rim: 1.2, edge: 0.8 }),
  lens: K({ spec: 1, power: 90, wrap: 1, rim: 0.4, mode: 4 }),
  crystal: K({ spec: 1, power: 80, wrap: 0.2, rim: 1, soft: 0.5, edge: 1, mode: 1, sparkle: 1 }),
  velvet: K({ power: 8, wrap: 0.3, rim: 1.3, soft: 1.5, mode: 3 }),
  membrane: K({ spec: 0.2, power: 20, wrap: 0.45, rim: 1.2, soft: 2, mode: 2, sparkle: 0.2 }),
};

const vertex = /* glsl */ `
#include <common>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
uniform float uFaceSmooth;
varying vec3 vNormalV;
varying vec2 vUv2;
varying vec3 vViewPos;
varying vec3 vWorldPos;
varying vec3 vObjPos;
varying vec3 vObjN;
#ifdef USE_FACEPROJ
uniform mat4 uHeadInv;
uniform vec3 uFaceRadii;
varying vec3 vHeadPos;
#endif
void main() {
  #include <beginnormal_vertex>
  #include <morphinstance_vertex>
  #include <morphnormal_vertex>
  #include <skinbase_vertex>
  #include <skinnormal_vertex>
  #include <defaultnormal_vertex>
  #include <begin_vertex>
  #include <morphtarget_vertex>
  #include <skinning_vertex>
  #include <project_vertex>
  vNormalV = normalize(transformedNormal);
  vUv2 = uv;
  vViewPos = -mvPosition.xyz;
  vObjPos = transformed;
  vObjN = normalize(objectNormal);
  vWorldPos = (modelMatrix * vec4(transformed, 1.0)).xyz;
  #ifdef USE_FACEPROJ
  vHeadPos = (uHeadInv * vec4(vWorldPos, 1.0)).xyz;
  vec3 nh = normalize(vHeadPos / (uFaceRadii * uFaceRadii));
  vec3 nw = normalize(transpose(mat3(uHeadInv)) * nh);
  vec3 nv = normalize(mat3(viewMatrix) * nw);
  vNormalV = normalize(mix(vNormalV, nv, uFaceSmooth));
  #endif
}
`;

const fragment = /* glsl */ `
uniform vec3 uColor;
uniform vec3 uTip;
uniform float uHighlight;
uniform vec3 uEmissive;
uniform float uEmissiveStrength;
uniform float uOpacity;
uniform float uSpec;
uniform float uSpecPower;
uniform float uWrap;
uniform float uKindRim;
uniform float uKindSoft;
uniform float uKindEdge;
uniform float uKindLift;
uniform float uKindSparkle;
uniform int uMode;
uniform float uIsHair;
uniform float uIsTransparent;
uniform float uSelect;
uniform float uWear;
uniform vec3 uIri0;
uniform vec3 uIri1;
uniform vec3 uIri2;
uniform float uIriStrength;
uniform float uNormalScale;

uniform vec3 uLightDir;
uniform vec3 uLightColor;
uniform float uBands;
uniform float uSoft;
uniform float uToony;
uniform float uShadeShift;
uniform float uPainted;
uniform float uRim;
uniform float uSaturation;
uniform float uBrightness;
uniform vec3 uShadowTint;
uniform vec3 uShadow2Tint;
uniform vec3 uShadowGrade;
uniform float uSpecBoost;
uniform float uEdgeHi;
uniform float uAmbient;
uniform vec3 uAmbientDir;
uniform vec3 uAmbientColor;
uniform float uFill;
uniform vec3 uFillColor;
uniform vec3 uLight2Dir;
uniform vec3 uLight2Color;
uniform float uLight2Strength;
uniform float uHatch;
uniform float uHatchScale;
uniform float uHatchScreen;
uniform sampler2D uHatchTex;
uniform float uHalftone;
uniform float uSparkle;
uniform float uGobo;
uniform float uTime;
uniform vec3 uFakePos[2];
uniform vec3 uFakeColor[2];
uniform vec3 uFakeParams[2];
uniform float uDamage;
uniform vec4 uWrinkle;
uniform float uWrinkleNose;
#ifdef USE_TMAP
uniform sampler2D uMap;
#endif
#ifdef USE_AOMASK
uniform sampler2D uAoMap;
#endif
#ifdef USE_ILM
uniform sampler2D uIlmMap;
#endif
#ifdef USE_EMAP
uniform sampler2D uEmissiveMap;
#endif
#ifdef USE_NMAP
uniform sampler2D uNormalMap;
#endif
#ifdef USE_DAMAGE
uniform sampler2D uDamageMap;
#endif
#ifdef USE_WRINKLE
uniform sampler2D uWrinkleMap;
#endif
#ifdef USE_FACEPROJ
uniform sampler2D uFaceMap;
uniform vec4 uFaceRect;
uniform float uFaceFront;
varying vec3 vHeadPos;
#endif
varying vec3 vNormalV;
varying vec2 vUv2;
varying vec3 vViewPos;
varying vec3 vWorldPos;
varying vec3 vObjPos;
varying vec3 vObjN;

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }
float hash3(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
vec3 hash33(vec3 p) { return vec3(hash3(p), hash3(p + 17.1), hash3(p + 41.7)); }
float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x), mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), f.x), f.y);
}
float lum(vec3 c) { return dot(c, vec3(0.299, 0.587, 0.114)); }

float bandize(float l, float soft) {
  float q = l * uBands;
  float f = fract(q);
  float s = floor(q) + smoothstep(0.5 - soft, 0.5 + soft, f);
  return clamp(s / uBands, 0.0, 1.0);
}

vec3 deepTone(vec3 c) { return vec3(c.r * 0.42 + 0.03, c.g * 0.36 + 0.02, c.b * 0.5 + 0.08); }
vec3 liftTone(vec3 c) { return mix(c, vec3(1.0, 0.97, 0.9), 0.38); }
vec3 recolor(vec3 c, float g) {
  return g < 0.5 ? mix(deepTone(c), c, g * 2.0) : mix(c, liftTone(c), (g - 0.5) * 2.0);
}

mat3 cotangentFrame(vec3 N, vec3 p, vec2 uv) {
  vec3 dp1 = dFdx(p);
  vec3 dp2 = dFdy(p);
  vec2 duv1 = dFdx(uv);
  vec2 duv2 = dFdy(uv);
  vec3 dp2perp = cross(dp2, N);
  vec3 dp1perp = cross(N, dp1);
  vec3 T = dp2perp * duv1.x + dp1perp * duv2.x;
  vec3 B = dp2perp * duv1.y + dp1perp * duv2.y;
  float invmax = inversesqrt(max(max(dot(T, T), dot(B, B)), 1e-12));
  return mat3(T * invmax, B * invmax, N);
}

float hatchLevel(vec4 h, float tone) {
  float ink = h.r * smoothstep(0.12, 0.22, tone);
  ink = max(ink, h.g * smoothstep(0.32, 0.42, tone));
  ink = max(ink, h.b * smoothstep(0.52, 0.62, tone));
  ink = max(ink, h.a * smoothstep(0.72, 0.82, tone));
  return ink;
}

void main() {
  vec3 N = normalize(vNormalV);
  if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(vViewPos);
  vec3 L = normalize(uLightDir);

  vec3 base = uColor;
  if (uIsHair > 0.5) base = mix(uColor, uTip, smoothstep(0.0, 1.0, vUv2.y));
  float texLum = 0.5;
  #ifdef USE_TMAP
  vec4 tex = texture2D(uMap, vUv2);
  texLum = lum(tex.rgb);
  #ifdef USE_RECOLOR
  base = recolor(uColor, texLum);
  #else
  base *= tex.rgb;
  #endif
  #endif

  #ifdef USE_NMAP
  vec3 nm = texture2D(uNormalMap, vUv2).xyz * 2.0 - 1.0;
  nm.xy *= uNormalScale;
  N = normalize(cotangentFrame(N, -vViewPos, vUv2) * nm);
  #endif

  #ifdef USE_DAMAGE
  vec4 dmg = texture2D(uDamageMap, vUv2);
  if (uDamage > 0.001 && dmg.r < uDamage * 0.85) discard;
  base = mix(base, base * vec3(0.45, 0.38, 0.3), clamp(dmg.g * uDamage * 1.4, 0.0, 0.85));
  #endif

  vec2 wuv = vUv2;
  float faceMask = 1.0;
  #ifdef USE_FACEPROJ
  vec2 fuv = vec2((vHeadPos.x - uFaceRect.x) / uFaceRect.z * 0.5 + 0.5, (vHeadPos.y - uFaceRect.y) / uFaceRect.w * 0.5 + 0.5);
  float inside = step(0.0, fuv.x) * step(fuv.x, 1.0) * step(0.0, fuv.y) * step(fuv.y, 1.0);
  faceMask = smoothstep(uFaceFront - 0.01, uFaceFront + 0.02, vHeadPos.z) * inside;
  vec4 fc = texture2D(uFaceMap, fuv);
  base = mix(base, fc.rgb, fc.a * faceMask);
  wuv = fuv;
  #endif
  #ifdef USE_WRINKLE
  vec4 wr = texture2D(uWrinkleMap, wuv);
  float crease = dot(wr, uWrinkle) * faceMask;
  base *= 1.0 - clamp(crease, 0.0, 1.0) * 0.4;
  #endif

  if (uMode == 4) {
    float gy = clamp(vUv2.y, 0.0, 1.0);
    base = mix(base * 1.2 + 0.05, base * 0.55, gy);
  }

  // Key light: hard two-tone with a per-category boundary width.
  float soft = uSoft * uKindSoft * mix(2.0, 0.15, uToony);
  float ndl = dot(N, L);
  float lit0 = (ndl + uWrap) / (1.0 + uWrap) + uKindLift - uShadeShift * 0.5;
  if (uPainted > 0.0) lit0 += (texLum - 0.5) * uPainted * 0.35 + (vnoise(vUv2 * 38.0) - 0.5) * uPainted * 0.22;
  float shadow2 = 0.0;
  #ifdef USE_AOMASK
  float ao = texture2D(uAoMap, vUv2).r;
  lit0 = mix(-0.5, lit0, smoothstep(0.35, 0.55, ao));
  shadow2 = 1.0 - smoothstep(0.1, 0.25, ao);
  #endif
  float lit = bandize(clamp(lit0, 0.0, 1.0), soft);
  if (uGobo > 0.0) {
    float leaf = vnoise(vWorldPos.xz * 3.2 + vWorldPos.y * 1.7) * 0.65 + vnoise(vWorldPos.xy * 7.0) * 0.35;
    lit *= mix(1.0, smoothstep(0.5, 0.58, leaf), uGobo);
  }

  // Shadow color: tint, one-direction ambient and fill (both on shadows only), then the second shadow.
  vec3 shadowCol = base * uShadowTint;
  if (uMode == 3) shadowCol = pow(max(shadowCol, 0.0), vec3(1.18)) * 1.12;
  shadowCol += base * uAmbientColor * uAmbient * 0.6 * (0.5 + 0.5 * dot(N, normalize(uAmbientDir)));
  shadowCol += base * uFillColor * uFill * 0.6;
  // Added ambient and fill are bluish and grey out warm colors; shadows should stay rich.
  shadowCol = max(mix(vec3(lum(shadowCol)), shadowCol, 1.25), 0.0);
  vec3 shadow2Col = base * uShadow2Tint;
  shadowCol = mix(shadowCol, shadow2Col, shadow2) * uShadowGrade;
  vec3 litCol = base * uLightColor;
  vec3 col = mix(shadowCol, litCol, lit);

  if (uLight2Strength > 0.0) {
    float l2 = smoothstep(0.5 - soft, 0.5 + soft, (dot(N, normalize(uLight2Dir)) + uWrap) / (1.0 + uWrap));
    col += base * uLight2Color * uLight2Strength * l2 * (1.0 - 0.6 * lit);
  }

  for (int i = 0; i < 2; i++) {
    vec3 fp = uFakeParams[i];
    if (fp.x > 0.0) {
      float f = clamp(1.0 - distance(vWorldPos, uFakePos[i]) / fp.x, 0.0, 1.0);
      col += base * uFakeColor[i] * f * f * mix(fp.z, fp.y, lit);
    }
  }

  // Highlights come from the key light only, and only on its lit side.
  float specMask = 1.0;
  float power = uSpecPower;
  #ifdef USE_ILM
  vec4 ilm = texture2D(uIlmMap, vUv2);
  power *= mix(1.6, 0.35, ilm.g);
  specMask = ilm.b;
  #endif
  vec3 H = normalize(L + V);
  float hs = 0.05 * uKindSoft;
  float sp = pow(max(dot(N, H), 0.0), power);
  sp = smoothstep(0.5 - hs, 0.5 + hs, sp) * uSpec * uSpecBoost * specMask * lit;
  float ndv = max(dot(N, V), 0.0);
  vec3 hiCol = mix(vec3(1.0), base, 0.25) * uLightColor;
  if (uIriStrength > 0.0) {
    vec3 iri = ndv > 0.5 ? mix(uIri1, uIri0, (ndv - 0.5) * 2.0) : mix(uIri2, uIri1, ndv * 2.0);
    hiCol = mix(hiCol, iri, uIriStrength);
  }
  if (uWear > 0.001) {
    float chip = step(1.0 - uWear * 0.5, hash(floor(vUv2 * 48.0)));
    col = mix(col, vec3(0.62, 0.64, 0.66) * (0.6 + 0.4 * lit), chip * 0.8);
  }
  col += sp * hiCol;

  float edge = smoothstep(0.55, 0.8, 1.0 - ndv) * uKindEdge * uEdgeHi * lit * specMask;
  col += edge * mix(base, vec3(1.0), 0.5) * uLightColor * 0.45;

  if (uIsHair > 0.5) {
    float band = 0.42 + N.y * 0.08;
    float hb = 1.0 - smoothstep(0.0, 0.07, abs(vUv2.y - band));
    float seg = fract(vUv2.x * 7.0 + hash(vec2(floor(vUv2.x * 7.0), 3.0)) * 0.4);
    float slash = smoothstep(0.08, 0.16, seg) * (1.0 - smoothstep(0.5, 0.6, seg));
    col += uHighlight * hb * slash * mix(vec3(1.0), uTip, 0.3) * 0.5 * lit;
  }

  float rim = pow(1.0 - ndv, 3.0);
  rim = smoothstep(0.35, 0.55, rim) * uRim * uKindRim;
  col += rim * mix(vec3(1.0, 0.97, 0.92), base, 0.35) * (0.35 + 0.65 * lit) * 0.55;

  float alpha = uOpacity;
  float fres = pow(1.0 - ndv, 2.0);
  if (uMode == 1) {
    vec3 Nf = normalize(cross(dFdx(-vViewPos), dFdy(-vViewPos)));
    if (dot(Nf, V) < 0.0) Nf = -Nf;
    float facet = hash3(floor(Nf * 5.0));
    float inner = 0.3 + 0.7 * facet;
    col = mix(base * 0.32, base * 1.3, inner * (0.55 + 0.45 * lit));
    col += base * 0.25;
    col += vec3(1.0) * fres * 0.5;
    col += sp * hiCol;
    if (uIsTransparent > 0.5) alpha = mix(uOpacity, 1.0, fres);
  } else if (uMode == 2) {
    col = mix(col, liftTone(base), fres * 0.6);
    col += base * max(-ndl, 0.0) * 0.45;
    if (uIsTransparent > 0.5) alpha = mix(uOpacity, 1.0, fres);
  } else if (uMode == 3) {
    col += base * 0.35 * pow(1.0 - ndv, 2.5);
  } else if (uMode == 4) {
    col = mix(col, base, 0.7);
    float s = abs(fract(vUv2.x * 0.8 + vUv2.y * 0.8) - 0.62);
    col += vec3(0.9) * (1.0 - smoothstep(0.03, 0.05, s));
  }

  float sparkle = uSparkle * uKindSparkle;
  if (sparkle > 0.0) {
    float dens = 55.0;
    vec3 cell = floor(vObjPos * dens);
    vec3 r = hash33(cell);
    vec3 local = fract(vObjPos * dens) - (0.25 + 0.5 * r);
    float pt = 1.0 - smoothstep(0.0, 0.18, length(local));
    vec3 Nj = normalize(N + (r - 0.5) * 0.9);
    float glint = pow(max(dot(Nj, H), 0.0), 220.0) * step(0.9, r.x);
    col += vec3(glint * pt * 5.0 * sparkle) * mix(vec3(1.0), base, 0.3);
  }

  if (uHatch > 0.0) {
    float tone = clamp((1.0 - lit) * 0.75 + (1.0 - lum(col)) * 0.45 - 0.1, 0.0, 1.0);
    vec4 h;
    if (uHatchScreen > 0.5) {
      h = texture2D(uHatchTex, gl_FragCoord.xy / (256.0 * uHatchScale));
    } else {
      vec3 w = abs(normalize(vObjN));
      w = w / (w.x + w.y + w.z);
      vec3 p = vObjPos * 3.2 * uHatchScale;
      h = texture2D(uHatchTex, p.yz) * w.x + texture2D(uHatchTex, p.xz) * w.y + texture2D(uHatchTex, p.xy) * w.z;
    }
    float ink = hatchLevel(h, tone) * (1.0 - 0.85 * lit);
    col = mix(col, col * 0.12, clamp(ink * uHatch, 0.0, 1.0));
  }
  if (uHalftone > 0.0) {
    vec2 cellPx = gl_FragCoord.xy / 6.0;
    vec2 g = fract(mat2(0.707, -0.707, 0.707, 0.707) * cellPx) - 0.5;
    float tone = clamp(1.0 - lum(col) * 1.1, 0.0, 1.0) * lit;
    float dotm = 1.0 - smoothstep(tone * 0.5 - 0.04, tone * 0.5 + 0.04, length(g));
    col *= 1.0 - 0.35 * uHalftone * dotm;
  }

  vec3 emis = uEmissive * uEmissiveStrength;
  #ifdef USE_EMAP
  emis *= texture2D(uEmissiveMap, vUv2).rgb;
  #endif
  col += emis;

  float l = lum(col);
  col = mix(vec3(l), col, uSaturation) * uBrightness;
  col = mix(col, vec3(0.3, 0.78, 1.0), uSelect * 0.42);

  gl_FragColor = vec4(col, alpha);
  #include <colorspace_fragment>
}
`;

export class ToonMaterial extends THREE.ShaderMaterial {
  kind: ToonKind;
  constructor(opts: ToonOptions) {
    const kind = opts.kind ?? 'skin';
    const p = KIND_PARAMS[kind];
    const defines: Record<string, string> = {};
    if (opts.map) defines.USE_TMAP = '';
    if (opts.map && opts.recolor) defines.USE_RECOLOR = '';
    if (opts.aoMap) defines.USE_AOMASK = '';
    if (opts.ilmMap) defines.USE_ILM = '';
    if (opts.emissiveMap) defines.USE_EMAP = '';
    if (opts.normalMap) defines.USE_NMAP = '';
    if (opts.damageMap) defines.USE_DAMAGE = '';
    if (opts.wrinkleMap) defines.USE_WRINKLE = '';
    if (opts.face) defines.USE_FACEPROJ = '';
    const opacity = opts.opacity ?? 1;
    const iri = opts.iridescent?.map((x) => new THREE.Color(x)) ?? [new THREE.Color(), new THREE.Color(), new THREE.Color()];
    super({
      vertexShader: vertex,
      fragmentShader: fragment,
      defines,
      transparent: opacity < 1,
      depthWrite: opacity >= 1,
      side: opts.side ?? THREE.FrontSide,
      uniforms: {
        ...sharedUniforms,
        uColor: { value: new THREE.Color(opts.color) },
        uTip: { value: new THREE.Color(opts.tip ?? opts.color) },
        uHighlight: { value: opts.highlight ?? 0 },
        uEmissive: { value: new THREE.Color(opts.emissive ?? 0x000000) },
        uEmissiveStrength: { value: opts.emissiveStrength ?? (kind === 'emissive' ? 1 : 0) },
        uOpacity: { value: opacity },
        uSpec: { value: p.spec },
        uSpecPower: { value: p.power },
        uWrap: { value: p.wrap },
        uKindRim: { value: p.rim },
        uKindSoft: { value: p.soft },
        uKindEdge: { value: p.edge },
        uKindLift: { value: p.lift },
        uKindSparkle: { value: opts.sparkle ?? p.sparkle },
        uMode: { value: p.mode },
        uIsHair: { value: kind === 'hair' ? 1 : 0 },
        uIsTransparent: { value: opacity < 1 ? 1 : 0 },
        uSelect: { value: 0 },
        uWear: { value: opts.wear ?? 0 },
        uIri0: { value: iri[0] },
        uIri1: { value: iri[1] },
        uIri2: { value: iri[2] },
        uIriStrength: { value: opts.iridescent ? 0.85 : 0 },
        uNormalScale: { value: opts.normalScale ?? 0.35 },
        uDamage: { value: 0 },
        uWrinkle: { value: new THREE.Vector4() },
        uWrinkleNose: { value: 0 },
        uMap: { value: opts.map ?? null },
        uAoMap: { value: opts.aoMap ?? null },
        uIlmMap: { value: opts.ilmMap ?? null },
        uEmissiveMap: { value: opts.emissiveMap ?? null },
        uNormalMap: { value: opts.normalMap ?? null },
        uDamageMap: { value: opts.damageMap ?? null },
        uWrinkleMap: { value: opts.wrinkleMap ?? null },
        uFaceMap: { value: opts.face?.map ?? null },
        uFaceRect: { value: opts.face?.rect ?? new THREE.Vector4(0, 0, 1, 1) },
        uFaceFront: { value: opts.face?.front ?? 0 },
        uFaceRadii: { value: opts.face?.radii ?? new THREE.Vector3(1, 1, 1) },
        uHeadInv: { value: opts.face?.headInv ?? new THREE.Matrix4() },
      },
    });
    this.kind = kind;
  }

  set select(v: number) {
    this.uniforms.uSelect.value = v;
  }
}

export function toon(opts: ToonOptions): ToonMaterial {
  return new ToonMaterial(opts);
}
