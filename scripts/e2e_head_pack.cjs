/**
 * End-to-end check of a head-only pack (blender/newhead/export_head_pack.py) in the real app: import, apply as the body,
 * confirm every face element arrives as its own mesh, that identity sliders and performance keys move the right
 * element, and capture face renders with captureViews (neutral and a few expressions).
 *
 *   node scripts/e2e_head_pack.cjs --pack DIR_WITH_LIBRARY_TREE [--id head_mhs3_n56] [--out work/head_app] [--url http://localhost:5173]
 *
 * Needs Playwright and a running dev server (npx vite --port 5173). Exit 0 = every step passed.
 */
const fs = require('fs');
const path = require('path');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]] : a), []));
const url = args.url || 'http://localhost:5173';
const packId = args.id || 'head_mhs3_n56';
const out = args.out || 'work/head_app';
const playwright = process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright';
const ELEMENTS = ['CHR_Head', 'CHR_Ears', 'CHR_EyeWhite_L', 'CHR_EyeWhite_R', 'CHR_Iris_L', 'CHR_Iris_R', 'CHR_LidLine_L', 'CHR_LidLine_R',
  'CHR_Brow_L', 'CHR_Brow_R', 'CHR_NoseShade', 'CHR_MouthLine', 'CHR_MouthInside', 'CHR_TeethUpper', 'CHR_Tongue', 'CHR_LipShadow'];
const results = [];
const step = (name, ok, detail) => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); return !!ok; };

(async () => {
  const { chromium } = require(playwright);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 850 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url + '?capture');
  await page.waitForFunction(() => window.creator && window.creator.store, null, { timeout: 30000 });
  await page.waitForTimeout(3000);   // the toolbar binds its handlers after the store appears
  const [chooser] = await Promise.all([page.waitForEvent('filechooser', { timeout: 30000 }), page.getByRole('button', { name: /import/i }).first().click()]);
  await chooser.setFiles(args.pack);
  await page.waitForFunction(() => window.creator.store.getState().packs.length > 0, null, { timeout: 15000 }).catch(() => {});
  const ok = await page.evaluate((id) => window.creator.store.getState().packs.some((p) => p.id === id), packId);
  if (!step('import: the head pack is read', ok)) return finish(browser, errors);
  await page.evaluate((id) => { const st = window.creator.store.getState(); st.applyPack(st.packs.find((p) => p.id === id)); }, packId);
  const attached = await page.waitForFunction((id) => { const e = window.creator.engine(); return !!(e && e.rig && e.rig.root.getObjectByName('PACK_' + id)); }, packId, { timeout: 30000 }).then(() => true, () => false);
  if (!step('apply: the head is attached as the body (procedural body hidden)', attached)) return finish(browser, errors);
  const meshes = await page.evaluate((id) => {
    const root = window.creator.engine().rig.root.getObjectByName('PACK_' + id); const out = {};
    root.traverse((o) => { if (o.isMesh) out[(o.userData && o.userData.name) || o.name] = o.morphTargetDictionary ? Object.keys(o.morphTargetDictionary).length : 0; });
    return out;
  }, packId);
  const names = Object.keys(meshes);
  const missing = ELEMENTS.filter((e) => !names.some((n) => n === e || n.startsWith(e + '_')));
  step('elements: every face element is its own mesh', missing.length === 0, `${names.length} meshes${missing.length ? '; missing ' + missing.join(', ') : ''}`);
  const read = (mesh, key) => page.evaluate(([id, m, k]) => {
    const root = window.creator.engine().rig.root.getObjectByName('PACK_' + id); let v = null;
    root.traverse((o) => { const n = (o.userData && o.userData.name) || o.name; if (o.isMesh && n === m && o.morphTargetDictionary && k in o.morphTargetDictionary) v = o.morphTargetInfluences[o.morphTargetDictionary[k]]; });
    return v;
  }, [packId, mesh, key]);
  for (const [ctl, key, mesh] of [['eye.size', 'ID-EyeSize', 'CHR_EyeWhite_L'], ['mouth.width', 'ID-MouthWidth', 'CHR_MouthLine'], ['jaw.width', 'ID-JawWidth', 'CHR_Head'], ['ear.size', 'ID-EarSize', 'CHR_Ears']]) {
    await page.evaluate((c) => window.creator.store.getState().setValue(c, 100), ctl);
    await page.waitForTimeout(1200);
    const v = await read(mesh, key);
    step(`slider: ${ctl} = 100 drives ${key} on ${mesh}`, v !== null && Math.abs(v - 1) < 0.01, `value ${v}`);
    await page.evaluate((c) => window.creator.store.getState().setValue(c, 0), ctl);
  }
  await page.evaluate(() => window.creator.store.getState().setPerf({ autoBlink: false }));   // the auto blink owns PF-Blink_*
  for (const [key, mesh] of [['PF-Blink_L', 'CHR_LidLine_L'], ['PF-SmileOpenJaw', 'CHR_MouthInside'], ['PF-VisAA', 'CHR_TeethUpper'], ['PF-JawOpen', 'CHR_Head'], ['PF-BrowInnerUp_L', 'CHR_Brow_L']]) {
    await page.evaluate((k) => window.creator.store.getState().setPerfKey(k, 1), key);
    await page.waitForTimeout(1500);
    const v = await read(mesh, key);
    step(`performance: ${key} = 1 drives ${mesh}`, v !== null && v > 0.9, `value ${v}`);
    await page.evaluate((k) => window.creator.store.getState().setPerfKey(k, 0), key);
  }
  await page.waitForTimeout(1000);
  fs.mkdirSync(out, { recursive: true });
  const shots = {
    neutral: {},
    smile_open: { 'PF-SmileOpenJaw': 1, 'PF-JawOpen': 0.35 },
    talk_aa: { 'PF-VisAA': 0.8 },
    blink: { 'PF-Blink_L': 1, 'PF-Blink_R': 1 },
  };
  for (const [nm, keys] of Object.entries(shots)) {
    const imgs = await page.evaluate(async (k) => {
      const st = window.creator.store.getState();
      for (const [key, v] of Object.entries(k)) st.setPerfKey(key, v);
      await new Promise((r) => setTimeout(r, 1200));
      const r = await window.creator.captureViews({ views: ['face', 'face_three_quarter'], size: 768, perf: { manual: k } });
      for (const key of Object.keys(k)) st.setPerfKey(key, 0);
      return r;
    }, keys).catch((e) => ({ error: String(e) }));
    if (imgs.error) { step(`capture: ${nm}`, false, imgs.error); continue; }
    for (const [view, dataUrl] of Object.entries(imgs)) fs.writeFileSync(path.join(out, `${nm}_${view}.png`), Buffer.from(dataUrl.split(',')[1], 'base64'));
    step(`capture: ${nm}`, Object.keys(imgs).length > 0, Object.keys(imgs).join(','));
  }
  await page.screenshot({ path: path.join(out, 'app_ui.png') });
  await finish(browser, errors);
})().catch((e) => { console.error(e); process.exit(1); });

async function finish(browser, errors) {
  if (errors.length) console.log('page errors:', errors.slice(0, 3));
  await browser.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(failed ? `\nE2E FAILED: ${failed} step(s)` : '\nE2E OK');
  process.exit(failed ? 1 : 0);
}
