import * as THREE from 'three';
import { STYLE_PRESETS, type StyleSettings } from '../model/presets';
import type { StylePreset } from '../model/types';

/** Uniforms shared by every toon material so a style change reaches the whole picture at once. */
export const sharedUniforms = {
  uLightDir: { value: new THREE.Vector3(0.4, 0.6, 0.7).normalize() },
  uBands: { value: 3 },
  uSoft: { value: 0.2 },
  uRim: { value: 0.4 },
  uSaturation: { value: 1 },
  uBrightness: { value: 1 },
  uShadowTint: { value: new THREE.Vector3(0.72, 0.66, 0.82) },
  uSpecBoost: { value: 1 },
  uAmbient: { value: 0.18 },
};

export function applyStyle(style: StylePreset): StyleSettings {
  const s = STYLE_PRESETS[style];
  sharedUniforms.uBands.value = s.bands;
  sharedUniforms.uSoft.value = s.softness;
  sharedUniforms.uRim.value = s.rim;
  sharedUniforms.uSaturation.value = s.saturation;
  sharedUniforms.uBrightness.value = s.brightness;
  sharedUniforms.uShadowTint.value.set(...s.shadowTint);
  sharedUniforms.uSpecBoost.value = s.specBoost;
  return s;
}

export type ToonKind = 'skin' | 'cloth' | 'leather' | 'metal' | 'hair' | 'scale' | 'fur' | 'emissive' | 'eyeWhite' | 'dark' | 'glass';

export interface ToonOptions {
  color: THREE.ColorRepresentation;
  kind?: ToonKind;
  map?: THREE.Texture | null;
  tip?: THREE.ColorRepresentation;
  highlight?: number;
  emissive?: THREE.ColorRepresentation;
  emissiveStrength?: number;
  opacity?: number;
  damageMap?: THREE.Texture | null;
  wrinkleMap?: THREE.Texture | null;
  side?: THREE.Side;
  wear?: number;
  face?: { map: THREE.Texture; rect: THREE.Vector4; front: number; headInv: THREE.Matrix4 };
}

const KIND_PARAMS: Record<ToonKind, { spec: number; power: number; wrap: number; rim: number }> = {
  skin: { spec: 0.05, power: 24, wrap: 0.35, rim: 1 },
  cloth: { spec: 0.0, power: 8, wrap: 0.2, rim: 0.7 },
  leather: { spec: 0.25, power: 30, wrap: 0.15, rim: 0.8 },
  metal: { spec: 0.9, power: 70, wrap: 0.05, rim: 1.1 },
  hair: { spec: 0.0, power: 20, wrap: 0.25, rim: 0.9 },
  scale: { spec: 0.35, power: 40, wrap: 0.15, rim: 1 },
  fur: { spec: 0.0, power: 10, wrap: 0.35, rim: 1.2 },
  emissive: { spec: 0.0, power: 10, wrap: 1, rim: 0 },
  eyeWhite: { spec: 0.0, power: 10, wrap: 0.8, rim: 0 },
  dark: { spec: 0.1, power: 20, wrap: 0.1, rim: 0.5 },
  glass: { spec: 1.0, power: 90, wrap: 0.3, rim: 1.2 },
};

const vertex = /* glsl */ `
#include <common>
#include <morphtarget_pars_vertex>
#include <skinning_pars_vertex>
varying vec3 vNormalV;
varying vec2 vUv2;
varying vec3 vViewPos;
#ifdef USE_FACEPROJ
uniform mat4 uHeadInv;
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
  #ifdef USE_FACEPROJ
  vHeadPos = (uHeadInv * modelMatrix * vec4(transformed, 1.0)).xyz;
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
uniform float uIsHair;
uniform float uSelect;
uniform float uWear;
uniform vec3 uLightDir;
uniform float uBands;
uniform float uSoft;
uniform float uRim;
uniform float uSaturation;
uniform float uBrightness;
uniform vec3 uShadowTint;
uniform float uSpecBoost;
uniform float uAmbient;
uniform float uDamage;
uniform vec4 uWrinkle;
uniform float uWrinkleNose;
#ifdef USE_TMAP
uniform sampler2D uMap;
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

float bandize(float l) {
  float q = l * uBands;
  float f = fract(q);
  float s = floor(q) + smoothstep(0.5 - uSoft, 0.5 + uSoft, f);
  return clamp(s / uBands, 0.0, 1.0);
}

float hash(vec2 p) { return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453); }

void main() {
  vec3 N = normalize(vNormalV);
  if (!gl_FrontFacing) N = -N;
  vec3 V = normalize(vViewPos);
  vec3 L = normalize(uLightDir);

  vec3 base = uColor;
  if (uIsHair > 0.5) base = mix(uColor, uTip, smoothstep(0.0, 1.0, vUv2.y));
  #ifdef USE_TMAP
  vec4 tex = texture2D(uMap, vUv2);
  base *= tex.rgb;
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

  float ndl = dot(N, L);
  float lit = (ndl + uWrap) / (1.0 + uWrap);
  lit = bandize(clamp(lit, 0.0, 1.0));
  lit = max(lit, uAmbient);
  vec3 shadowCol = base * uShadowTint;
  vec3 col = mix(shadowCol, base, lit);

  vec3 H = normalize(L + V);
  float sp = pow(max(dot(N, H), 0.0), uSpecPower);
  sp = smoothstep(0.45, 0.55, sp) * uSpec * uSpecBoost;
  if (uWear > 0.001) {
    float chip = step(1.0 - uWear * 0.5, hash(floor(vUv2 * 48.0)));
    col = mix(col, vec3(0.62, 0.64, 0.66) * (0.6 + 0.4 * lit), chip * 0.8);
  }
  col += vec3(sp) * mix(vec3(1.0), base, 0.25);

  if (uIsHair > 0.5) {
    float band = 0.42 + N.y * 0.08;
    float hb = 1.0 - smoothstep(0.0, 0.07, abs(vUv2.y - band));
    col += uHighlight * hb * mix(vec3(1.0), uTip, 0.4) * 0.35 * (0.4 + 0.6 * lit);
  }

  float rim = pow(1.0 - max(dot(N, V), 0.0), 3.0);
  rim = smoothstep(0.35, 0.55, rim) * uRim * uKindRim;
  col += rim * mix(vec3(1.0, 0.97, 0.92), base, 0.35) * (0.35 + 0.65 * lit) * 0.55;

  col += uEmissive * uEmissiveStrength;

  float lum = dot(col, vec3(0.299, 0.587, 0.114));
  col = mix(vec3(lum), col, uSaturation) * uBrightness;
  col = mix(col, vec3(0.3, 0.78, 1.0), uSelect * 0.42);

  gl_FragColor = vec4(col, uOpacity);
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
    if (opts.damageMap) defines.USE_DAMAGE = '';
    if (opts.wrinkleMap) defines.USE_WRINKLE = '';
    if (opts.face) defines.USE_FACEPROJ = '';
    super({
      vertexShader: vertex,
      fragmentShader: fragment,
      defines,
      transparent: (opts.opacity ?? 1) < 1,
      depthWrite: (opts.opacity ?? 1) >= 1,
      side: opts.side ?? THREE.FrontSide,
      uniforms: {
        ...sharedUniforms,
        uColor: { value: new THREE.Color(opts.color) },
        uTip: { value: new THREE.Color(opts.tip ?? opts.color) },
        uHighlight: { value: opts.highlight ?? 0 },
        uEmissive: { value: new THREE.Color(opts.emissive ?? 0x000000) },
        uEmissiveStrength: { value: opts.emissiveStrength ?? (kind === 'emissive' ? 1 : 0) },
        uOpacity: { value: opts.opacity ?? 1 },
        uSpec: { value: p.spec },
        uSpecPower: { value: p.power },
        uWrap: { value: p.wrap },
        uKindRim: { value: p.rim },
        uIsHair: { value: kind === 'hair' ? 1 : 0 },
        uSelect: { value: 0 },
        uWear: { value: opts.wear ?? 0 },
        uDamage: { value: 0 },
        uWrinkle: { value: new THREE.Vector4() },
        uWrinkleNose: { value: 0 },
        uMap: { value: opts.map ?? null },
        uDamageMap: { value: opts.damageMap ?? null },
        uWrinkleMap: { value: opts.wrinkleMap ?? null },
        uFaceMap: { value: opts.face?.map ?? null },
        uFaceRect: { value: opts.face?.rect ?? new THREE.Vector4(0, 0, 1, 1) },
        uFaceFront: { value: opts.face?.front ?? 0 },
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
