/**
 * Fits the ellipsoid head to the reference profile in knowledge/head-targets.json.
 * Run: npx vite-node scripts/fit_head.ts
 * Prints the fitted HEAD_TUNING to paste into src/model/headShape.ts, plus before and after errors.
 */
import { readFileSync } from 'node:fs';
import { HEAD_TUNING, headDims, headProfile, type HeadTuning } from '../src/model/headShape';

const target = JSON.parse(readFileSync(new URL('../knowledge/head-targets.json', import.meta.url), 'utf8'));
const none = () => 0;
const h = 0.234;

const W = (f: string) => target.front.width[f] as number;
const B = (f: string) => target.side.behind_nose[f] as number;
const widthRows: [string, number][] = [['0.1', 2], ['0.15', 2], ['0.2', 3], ['0.25', 3], ['0.3', 3], ['0.75', 2], ['0.8', 2], ['0.85', 2], ['0.9', 2], ['0.95', 1], ['0.97', 1]];
const nose: [string, number][] = [['0.1', 1], ['0.2', 2], ['0.3', 2], ['0.4', 1], ['0.8', 2], ['0.9', 2]];

function errors(t: HeadTuning) {
  const d = headDims(none, h, false, 0, t);
  const p = headProfile(d, h, false, none, t);
  let e = 0;
  for (const [f, w] of widthRows) e += w * (p.width[f] - W(f)) ** 2;
  for (const [f, w] of nose) e += w * (p.behindNose[f] - B(f)) ** 2;
  e += 3 * (p.skullDepth03 - target.side['skull_depth_at_0.3']) ** 2;
  return { e, p };
}

const KEYS = Object.keys(HEAD_TUNING) as (keyof HeadTuning)[];
const LO: Partial<HeadTuning> = { noseDown: 0 };
const HI: Partial<HeadTuning> = { noseDown: 0.05 };
let best = { ...HEAD_TUNING };
let bestE = errors(best).e;
const before = errors(HEAD_TUNING).p;
let seed = 7;
const rnd = () => ((seed = (seed * 1664525 + 1013904223) % 4294967296) / 4294967296);
for (let i = 0; i < 40000; i++) {
  const t = { ...best };
  const k = KEYS[Math.floor(rnd() * KEYS.length)];
  const lo = LO[k] ?? 0.55;
  const hi = HI[k] ?? 1.5;
  t[k] = Math.min(hi, Math.max(lo, t[k] + (rnd() - 0.5) * (i < 20000 ? 0.12 : 0.02)));
  const e = errors(t).e;
  if (e < bestE) {
    best = t;
    bestE = e;
  }
}
const after = errors(best).p;
const r = (x: number) => Math.round(x * 1000) / 1000;
console.log('fitted HEAD_TUNING =', JSON.stringify(Object.fromEntries(KEYS.map((k) => [k, r(best[k])]))));
for (const [name, p] of [['before', before], ['after', after]] as const) {
  console.log(name, JSON.stringify({ cranium: r(p.cranium), depth: r(p.skullDepth03), ratio: r(p.widthToDepth), jaw0_8: r(p.width['0.8']), chin0_9: r(p.width['0.9']), noseAheadOfForehead: r(p.behindNose['0.3']), noseAheadOfChin: r(p.behindNose['0.9']) }));
}
console.log('target', JSON.stringify({ cranium: target.derived.cranium_width_H, depth: target.derived.skull_depth_H, ratio: target.derived.width_to_depth_ratio, jaw0_8: W('0.8'), chin0_9: W('0.9'), noseAheadOfForehead: B('0.3'), noseAheadOfChin: B('0.9') }));
