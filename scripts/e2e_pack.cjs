/**
 * End-to-end check of the asset-library pipeline in the real app: import a pack through the Import button, apply it,
 * then confirm that a slider moves the pack's ID- shape key and a performance value drives its PF- key.
 *
 *   node scripts/e2e_pack.cjs [--url http://localhost:5173] [--pack DIR_WITH_LIBRARY_TREE] [--id body_test]
 *
 * Without --pack it generates a conforming test pack (make_test_pack.py). Exit 0 = every step passed, 1 = something failed.
 * Needs Playwright and a running dev server (npx vite --port 5173).
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]] : a), []));
const url = args.url || 'http://localhost:5173';
const packId = args.id || 'body_test';
const playwright = process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright';
const results = [];
const step = (name, ok, detail) => { results.push({ name, ok: !!ok, detail }); console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? '  ' + detail : ''}`); return !!ok; };

(async () => {
  let lib = args.pack;
  if (!lib) {
    lib = fs.mkdtempSync(path.join(os.tmpdir(), 'e2e-lib-'));
    const gen = path.join(__dirname, '..', '.claude/skills/library-pack-check/scripts/make_test_pack.py');
    const r = spawnSync('python3', [gen, path.join(lib, 'humanoid/bodies/adult', packId), '--id', packId], { encoding: 'utf8' });
    if (r.status !== 0) { console.error(r.stderr); process.exit(1); }
    const hat = spawnSync('python3', [gen, path.join(lib, 'humanoid/accessories/hat_test'), '--id', 'hat_test', '--kind', 'accessory', '--socket', 'SOC-HeadTop'], { encoding: 'utf8' });
    if (hat.status !== 0) { console.error(hat.stderr); process.exit(1); }
    fs.writeFileSync(path.join(lib, 'manifest.json'), JSON.stringify({ packs: [{ id: packId, library: 'humanoid', folder: `humanoid/bodies/adult/${packId}` }, { id: 'hat_test', library: 'humanoid', folder: 'humanoid/accessories/hat_test' }] }));
  }
  const { chromium } = require(playwright);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1400, height: 850 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url + '?capture');
  await page.waitForFunction(() => window.creator && window.creator.store, null, { timeout: 30000 });

  const [chooser] = await Promise.all([page.waitForEvent('filechooser', { timeout: 15000 }), page.getByRole('button', { name: /import/i }).first().click()]);
  await chooser.setFiles(lib);
  await page.waitForFunction(() => window.creator.store.getState().packs.length > 0, null, { timeout: 15000 }).catch(() => {});
  const imported = await page.evaluate(() => window.creator.store.getState().packs.map((p) => ({ id: p.id, slot: p.slot, library: p.library, category: p.category, main: p.mainAsset })));
  if (!step('import: the pack is read from the folder', imported.some((p) => p.id === packId), JSON.stringify(imported))) return finish(browser, errors);
  const report = await page.evaluate(() => { const r = window.creator.store.getState().report; return r ? { added: r.added.length, skipped: r.skipped.map((s) => s.reason) } : null; });
  step('import: nothing skipped', report && report.skipped.length === 0, JSON.stringify(report));

  await page.evaluate((id) => { const st = window.creator.store.getState(); st.applyPack(st.packs.find((p) => p.id === id)); }, packId);
  const attached = await page.waitForFunction((id) => { const e = window.creator.engine(); return !!(e && e.rig && e.rig.root.getObjectByName('PACK_' + id)); }, packId, { timeout: 30000 }).then(() => true, () => false);
  if (!step('apply: the pack mesh is attached to the rig', attached)) return finish(browser, errors);

  const keys = await page.evaluate((id) => {
    const root = window.creator.engine().rig.root.getObjectByName('PACK_' + id); const out = [];
    root.traverse((o) => { if (o.isMesh && o.morphTargetDictionary) out.push(Object.keys(o.morphTargetDictionary)); });
    return out.flat();
  }, packId);
  step('apply: shape keys arrive by name', keys.includes('ID-FaceRound') && keys.includes('PF-Blink'), `${keys.length} keys`);

  const read = (key) => page.evaluate(([id, k]) => {
    const root = window.creator.engine().rig.root.getObjectByName('PACK_' + id); let v = null;
    root.traverse((o) => { if (o.isMesh && o.morphTargetDictionary && k in o.morphTargetDictionary) v = o.morphTargetInfluences[o.morphTargetDictionary[k]]; });
    return v;
  }, [packId, key]);
  const before = await read('ID-FaceRound');
  await page.evaluate(() => window.creator.store.getState().setValue('face.round', 100));
  await page.waitForTimeout(1500);
  const after = await read('ID-FaceRound');
  step('slider: "Round face" = 100 drives ID-FaceRound to 1', before === 0 && Math.abs(after - 1) < 0.01, `before ${before}, after ${after}`);
  await page.evaluate(() => window.creator.store.getState().setValue('face.round', 0));
  await page.waitForTimeout(1500);
  step('slider: back to 0 returns the key to 0', Math.abs(await read('ID-FaceRound')) < 0.01);

  // Accessory packs must attach to the SOC- node inside the BODY PACK, not to the placeholder rig's socket.
  if (!args.pack) {
    await page.evaluate(() => { const st = window.creator.store.getState(); st.applyPack(st.packs.find((p) => p.id === 'hat_test')); });
    const hatThere = await page.waitForFunction(() => { const r = window.creator.engine().rig.root.getObjectByName('EQ_hat_test'); return !!(r && r.children.some((c) => c.children.length || c.isMesh || c.name)); }, null, { timeout: 30000 }).then(() => true, () => false);
    step('accessory: the hat pack loads', hatThere);
    await page.waitForTimeout(1500);
    const att = await page.evaluate((id) => {
      const root = window.creator.engine().rig.root; const hat = root.getObjectByName('EQ_hat_test'); const soc = root.getObjectByName('PACK_' + id).getObjectByName('SOC-HeadTop');
      const a = new (hat.position.constructor)(), b = new (hat.position.constructor)(); hat.getWorldPosition(a); soc.getWorldPosition(b);
      let p = hat.parent; let under = false; while (p) { if (p === soc) under = true; p = p.parent; }
      return { hat: a.toArray().map((x) => +x.toFixed(3)), socket: b.toArray().map((x) => +x.toFixed(3)), dist: +a.distanceTo(b).toFixed(3), under };
    }, packId);
    step("accessory: attaches to the body pack's SOC-HeadTop, not the placeholder's", att.dist < 0.02 && att.under, JSON.stringify(att));
  }

  await page.evaluate(() => window.creator.store.getState().setPerfKey('PF-Blink', 1));
  await page.waitForTimeout(2500);
  const blink = await read('PF-Blink');
  step('performance: PF-Blink = 1 drives the pack key', blink !== null && blink > 0.9, `value ${blink}`);
  // Poses: the pack's own POSE-<pose> clip is applied to its skeleton when that pose is picked.
  const armAngle = () => page.evaluate((id) => {
    const root = window.creator.engine().rig.root.getObjectByName('PACK_' + id); let arm = null;
    root.traverse((o) => { if (o.userData && o.userData.name === 'DEF-upperarm.L') arm = o; });   // three strips the dot from loaded names
    return arm ? +arm.quaternion.angleTo(new arm.quaternion.constructor()).toFixed(3) : null;
  }, packId);
  const settle = (what) => page.waitForFunction((id) => !!window.creator.engine().rig.root.getObjectByName('PACK_' + id) && window.creator.engine().rig.identity.body === id, packId, { timeout: 30000 }).catch(() => {});
  await page.evaluate(() => window.creator.store.getState().setPerf({ bodyPose: 'tpose' }));
  await settle(); await page.waitForTimeout(2500);
  const tpose = await armAngle();
  step('pose: picking T-pose applies the pack clip POSE-tpose (arm raised 90 degrees)', tpose !== null && Math.abs(tpose - Math.PI / 2) < 0.05, `arm angle ${tpose} rad`);
  await page.evaluate(() => window.creator.store.getState().setPerf({ bodyPose: 'apose' }));
  await settle(); await page.waitForTimeout(2500);
  const rest = await armAngle();
  step('pose: back to A-pose returns the skeleton to rest', rest !== null && rest < 0.02, `arm angle ${rest} rad`);
  // Limb length: the control reaches a bone whose authored name has a .L suffix (the loader renames it DEF-upperarmL).
  const armScale = () => page.evaluate((id) => {
    const root = window.creator.engine().rig.root.getObjectByName('PACK_' + id); let arm = null;
    root.traverse((o) => { if (o.userData && o.userData.name === 'DEF-upperarm.L') arm = o; });
    return arm ? +arm.scale.y.toFixed(3) : null;
  }, packId);
  await page.evaluate(() => window.creator.store.getState().setValue('upperArm.length', 100));
  await settle(); await page.waitForTimeout(2500);
  const longArm = await armScale();
  step('bones: "Upper arm length" = 100 scales DEF-upperarm.L even though the loader renames it', longArm !== null && longArm > 1.05, `scale.y ${longArm}`);
  await finish(browser, errors);
})().catch((e) => { console.error(e); process.exit(1); });

async function finish(browser, errors) {
  if (errors.length) console.log('page errors:', errors.slice(0, 3));
  await browser.close();
  const failed = results.filter((r) => !r.ok).length;
  console.log(failed ? `\nE2E FAILED: ${failed} step(s)` : '\nE2E OK');
  process.exit(failed ? 1 : 0);
}
