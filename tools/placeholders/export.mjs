// Exports the app's procedural placeholder bodies to JSON so the Python validators can measure them.
//   npm install --no-save playwright-core        (dev tool only; uses the Chromium that is already installed)
//   npx vite --port 5173 &                        (the dev server must be running)
//   node tools/placeholders/export.mjs <out_dir> [adult child robot beast ...] [--archetype tiger] [--chrome /path/to/chrome]
// Axes: three.js is Y up and faces +Z. The exporter converts to Blender's (x, -z, y) so forward is -Y, as in the library.
import { chromium } from 'playwright-core';
import fs from 'node:fs';

const args = process.argv.slice(2);
const outDir = args[0] || '/tmp';
const kinds = args.slice(1).filter((a, i, arr) => !a.startsWith('--') && !(arr[i - 1] || '').startsWith('--'));
const opt = (k) => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : undefined; };
const chrome = opt('--chrome') || process.env.CHROME || '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const archetype = opt('--archetype');
const tag = opt('--tag') || 'run';
const hairTuning = opt('--hair') ? JSON.parse(opt('--hair')) : null;

const browser = await chromium.launch({ executablePath: chrome, args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--no-sandbox'] });
const page = await browser.newPage();
page.on('pageerror', (e) => console.log('PAGE ERROR', e.message.slice(0, 300)));
await page.goto(process.env.APP_URL || 'http://localhost:5173/', { waitUntil: 'networkidle' });

for (const kind of kinds.length ? kinds : ['adult']) {
  const data = await page.evaluate(async ({ kind, archetype, hairTuning }) => {
    if (hairTuning) { const hm = await import('/src/viewport/hair.ts'); hm.setHairTuning(hairTuning); }
    const Vec = (await import('/src/viewport/parts.ts')).V().constructor;
    const THREE = { Vector3: Vec };
    const { createCtx, finishRig } = await import('/src/viewport/rig.ts');
    const { buildHumanoid } = await import('/src/viewport/humanoid.ts');
    const { buildRobot } = await import('/src/viewport/robot.ts');
    const { buildDragon } = await import('/src/viewport/dragon.ts');
    const { newCharacter } = await import('/src/model/character.ts');
    const charMod = await import('/src/model/character.ts');
    let id = newCharacter(kind);
    if (archetype) id = charMod.applyArchetype(id, archetype);
    const ctx = createCtx(id, new Map(), { name: 'A-pose' });
    let built;
    if (kind === 'robot') built = buildRobot(ctx); else if (kind === 'beast') built = buildDragon(ctx); else built = buildHumanoid(ctx);
    const root = built.root;
    root.updateMatrixWorld(true);
    const P = (o) => { const v = new THREE.Vector3(); o.getWorldPosition(v); return [v.x, -v.z, v.y]; };   // to Blender axes
    const parts = {};
    root.traverse((o) => {
      if (!o.isMesh) return;
      const name = o.name || '';
      const region = o.userData?.region || '';
      const g = o.geometry; const pos = g.attributes.position; if (!pos) return;
      const m = o.matrixWorld; const v = new THREE.Vector3(); const verts = [];
      for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i).applyMatrix4(m); verts.push([+v.x.toFixed(5), +(-v.z).toFixed(5), +v.y.toFixed(5)]); }
      const idx = g.index ? Array.from(g.index.array) : Array.from({ length: pos.count }, (_, i) => i);
      const faces = []; for (let i = 0; i + 2 < idx.length; i += 3) faces.push([idx[i], idx[i + 1], idx[i + 2]]);
      const key = name || `?${region}`;
      (parts[key] ||= []).push({ region, verts, faces });
    });
    const body = built.body;
    const joints = body && body.g ? {
      hips: P(body.g.pelvis), neck: P(body.g.neck), head: P(body.g.head),
      shoulder_L: P(body.g.sh[0]), shoulder_R: P(body.g.sh[1]), elbow_L: P(body.g.el[0]), elbow_R: P(body.g.el[1]),
      wrist_L: P(body.g.wr[0]), wrist_R: P(body.g.wr[1]), hip_L: P(body.g.hip[0]), hip_R: P(body.g.hip[1]),
      knee_L: P(body.g.knee[0]), knee_R: P(body.g.knee[1]), ankle_L: P(body.g.ankle[0]), ankle_R: P(body.g.ankle[1]),
    } : {};
    return { kind, archetype: archetype || id.archetype, units: body ? { u: body.u, h: body.h } : {}, joints, parts };
  }, { kind, archetype, hairTuning });
  const file = `${outDir}/placeholder-${kind}${archetype ? '-' + archetype : ''}-${tag}.json`;
  fs.writeFileSync(file, JSON.stringify(data));
  console.log('wrote', file, Object.keys(data.parts).length, 'named parts');
}
await browser.close();
