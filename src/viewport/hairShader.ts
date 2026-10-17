import * as THREE from 'three';
import type { HairShader } from '../model/types';
import { DEFAULT_HAIR_SHADER } from '../model/hairShader';

export { DEFAULT_HAIR_SHADER };

/**
 * Anime hair shader (q24). One set of uniforms shared by every hair material, so a slider moves all hair at once
 * without rebuilding geometry (VRoid keeps its hair look per material; here it is per character).
 *
 * Inputs it relies on: strand geometry with uv.x around the strand (0..1) and uv.y from root (0) to tip (1), which is
 * what hair.ts builds. The same function is ported line for line to HLSL in shaders/hair/AnimeHair.hlsl.
 *
 * Parameters (names follow VRoid where it has one, MHS3 terms otherwise):
 *   shade / shadeMix      shadow colour of its own (MHS3 hair shadows are a hue shift, not a darker base)
 *   area / hardness       VRoid "Shading Area" and "Shading Hardness": where the shadow line sits and how hard it is
 *   rootDark              darker roots, fading out over the first quarter of each strand
 *   ringPos / ringWidth   the highlight band ("angel ring"): position along the strand (VRoid "Highlights Position")
 *   ringStrength / ringColor
 *   ringSpace             0 = band placed along each strand (uv), 1 = band placed on the head (elevation from the head
 *                         centre), so it reads as one continuous ring across all clumps like MHS3 / VRoid renders
 *   ringFollow            0 = band painted at ringPos, 1 = band follows the light like an anisotropic highlight
 *   ringJag / ringTeeth   jagged band edge (sawtooth along the strand width) and how many teeth per strand
 *   strandLines / strandCount   thin darker lines running down each strand (MHS3 painted hair lines)
 *   rim / rimPow          VRoid "Rim Light Intensity" and "Concentration"
 */

const col = (hex: string) => new THREE.Color(hex);

export const hairUniforms = {
  uHairShade: { value: col(DEFAULT_HAIR_SHADER.shade) },
  uHairShadeMix: { value: DEFAULT_HAIR_SHADER.shadeMix },
  uHairArea: { value: DEFAULT_HAIR_SHADER.area },
  uHairHard: { value: DEFAULT_HAIR_SHADER.hardness },
  uHairRootDark: { value: DEFAULT_HAIR_SHADER.rootDark },
  uRingPos: { value: DEFAULT_HAIR_SHADER.ringPos },
  uRingWidth: { value: DEFAULT_HAIR_SHADER.ringWidth },
  uRingStrength: { value: DEFAULT_HAIR_SHADER.ringStrength },
  uRingColor: { value: col(DEFAULT_HAIR_SHADER.ringColor) },
  uRingFollow: { value: DEFAULT_HAIR_SHADER.ringFollow },
  uRingSpace: { value: DEFAULT_HAIR_SHADER.ringSpace },
  uRingJag: { value: DEFAULT_HAIR_SHADER.ringJag },
  uRingTeeth: { value: DEFAULT_HAIR_SHADER.ringTeeth },
  uStrandLines: { value: DEFAULT_HAIR_SHADER.strandLines },
  uStrandCount: { value: DEFAULT_HAIR_SHADER.strandCount },
  uHairRim: { value: DEFAULT_HAIR_SHADER.rim },
  uHairRimPow: { value: DEFAULT_HAIR_SHADER.rimPow },
};

/** Copies a character's hair-shader settings into the shared uniforms (missing fields fall back to the defaults). */
export function applyHairShader(p: Partial<HairShader> | undefined): void {
  const s = { ...DEFAULT_HAIR_SHADER, ...(p ?? {}) };
  const u = hairUniforms;
  u.uHairShade.value.set(s.shade);
  u.uHairShadeMix.value = s.shadeMix;
  u.uHairArea.value = s.area;
  u.uHairHard.value = s.hardness;
  u.uHairRootDark.value = s.rootDark;
  u.uRingPos.value = s.ringPos;
  u.uRingWidth.value = s.ringWidth;
  u.uRingStrength.value = s.ringStrength;
  u.uRingColor.value.set(s.ringColor);
  u.uRingFollow.value = s.ringFollow;
  u.uRingSpace.value = s.ringSpace;
  u.uRingJag.value = s.ringJag;
  u.uRingTeeth.value = s.ringTeeth;
  u.uStrandLines.value = s.strandLines;
  u.uStrandCount.value = s.strandCount;
  u.uHairRim.value = s.rim;
  u.uHairRimPow.value = s.rimPow;
}

/** GLSL declarations and the shading function, spliced into the toon fragment shader. */
export const HAIR_GLSL = /* glsl */ `
uniform vec3 uHairShade;
uniform float uHairShadeMix;
uniform float uHairArea;
uniform float uHairHard;
uniform float uHairRootDark;
uniform float uRingPos;
uniform float uRingWidth;
uniform float uRingStrength;
uniform vec3 uRingColor;
uniform float uRingFollow;
uniform float uRingSpace;
uniform float uRingJag;
uniform float uRingTeeth;
uniform float uStrandLines;
uniform float uStrandCount;
uniform float uHairRim;
uniform float uHairRimPow;

float hairHash(float n) { return fract(sin(n * 127.1) * 43758.5453); }

// Strand direction (root to tip) in view space, from the screen derivatives of position and uv.
vec3 hairTangent(vec3 p, vec2 uv, vec3 N) {
  vec3 dpx = dFdx(p), dpy = dFdy(p);
  vec2 dux = dFdx(uv), duy = dFdy(uv);
  float det = dux.x * duy.y - dux.y * duy.x;
  vec3 T = (dpy * dux.x - dpx * duy.x) * sign(det);
  T -= N * dot(N, T);
  return length(T) > 1e-6 ? normalize(T) : vec3(0.0, -1.0, 0.0);
}

// Returns the shaded hair colour. base: strand colour (root..tip), shadowCol / litCol: the toon pass's colours for
// this fragment, ndl: N.L, P: view-space position, O: head-space position (hair is built around the head centre),
// strength: per-piece highlight amount (HairPiece.highlight).
vec3 animeHair(vec3 base, vec3 shadowCol, vec3 litCol, float ndl, vec3 N, vec3 V, vec3 L, vec3 P, vec3 O, vec2 uv, float strength) {
  float y = clamp(uv.y, 0.0, 1.0);
  float root = mix(1.0 - uHairRootDark, 1.0, smoothstep(0.0, 0.25, y));

  // VRoid-style shading: the area moves the line, the hardness sets its width.
  float w = mix(0.3, 0.004, clamp(uHairHard, 0.0, 1.0));
  float c = -uHairArea * 0.5;
  float lit = smoothstep(c - w, c + w, ndl);

  vec3 shade = mix(shadowCol, uHairShade * (0.6 + 0.4 * base / max(max(base.r, base.g), max(base.b, 0.001))), uHairShadeMix);
  vec3 colr = mix(shade, litCol, lit) * root;

  // Highlight band: painted at ringPos, optionally pulled toward an anisotropic (Kajiya-Kay) position.
  vec3 T = hairTangent(P, uv, N);
  vec3 H = normalize(L + V);
  float th = dot(T, H);                    // -1..1 along the strand
  float bandPos = mix(uRingPos, clamp(0.5 - th * 0.5, 0.0, 1.0), uRingFollow);
  float strand = floor(uv.x * max(uStrandCount, 1.0));
  // Strand space: coordinate along the strand, teeth across it. Head space: elevation from the head centre
  // (0 = crown, 0.5 = equator), teeth around the head.
  vec3 od = normalize(O + vec3(0.0, 1e-4, 0.0));
  float headT = 0.5 - 0.5 * od.y;
  float az = atan(od.x, od.z) / 6.2831853 + 0.5;
  float saw = mix(fract(uv.x * max(uRingTeeth, 1.0) * max(uStrandCount, 1.0) + hairHash(strand) * 0.7),
                  fract(az * max(uRingTeeth, 1.0) * 6.0), step(0.5, uRingSpace));
  float jag = (saw - 0.5) * uRingJag * uRingWidth * 2.0;
  float coord = mix(y, headT, uRingSpace);
  float d = abs(coord - bandPos - jag);
  float ring = 1.0 - smoothstep(uRingWidth * 0.6, uRingWidth, d);
  ring *= smoothstep(-0.2, 0.4, ndl);      // no ring deep in the shadow
  vec3 ringCol = mix(uRingColor, uRingColor * (base * 1.5 + 0.12), 0.55);   // tinted by the strand colour
  colr = mix(colr, ringCol, ring * uRingStrength * strength);

  // Thin darker lines down each strand.
  float sx = fract(uv.x * max(uStrandCount, 1.0) + hairHash(strand + 7.0) * 0.15 + sin(y * 9.0 + strand) * 0.03);
  float line = smoothstep(0.0, 0.05, abs(sx - 0.5) - 0.44);   // 1 in a thin line at each strand edge
  line *= smoothstep(0.08, 0.3, y);
  colr *= 1.0 - line * uStrandLines * 0.45;

  // Rim light (VRoid intensity / concentration).
  float ndv = max(dot(N, V), 0.0);
  float rim = pow(1.0 - ndv, max(uHairRimPow, 0.5)) * uHairRim;
  colr += rim * mix(vec3(1.0), base, 0.4) * (0.4 + 0.6 * lit);
  return colr;
}
`;
