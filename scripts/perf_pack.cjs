/**
 * Slider-drag cost with a realistic pack: generates a heavy body (every ID-/PF- key the app drives, ~19k triangles),
 * imports and applies it, then changes a slider repeatedly and reports rebuild time, time until the pack is live again,
 * frames dropped, and JS heap growth (a leak check).
 *
 *   node scripts/perf_pack.cjs [--url http://localhost:5173] [--pack LIB_DIR] [--changes 20]
 * Headless software rendering is slow: read the numbers as relative, and compare before/after a change.
 */
const fs = require('fs'), os = require('os'), path = require('path');
const { spawnSync } = require('child_process');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]] : a), []));
const url = args.url || 'http://localhost:5173';
const changes = Number(args.changes || 20);
const playwright = process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright';
(async () => {
  let lib = args.pack;
  if (!lib && !args['no-pack']) {
    lib = fs.mkdtempSync(path.join(os.tmpdir(), 'perf-lib-'));
    const r = spawnSync('python3', [path.join(__dirname, '..', '.claude/skills/library-pack-check/scripts/make_test_pack.py'), path.join(lib, 'humanoid/bodies/adult/body_test'), '--all-keys'], { encoding: 'utf8' });
    if (r.status !== 0) { console.error(r.stderr); process.exit(1); }
  }
  const { chromium } = require(playwright);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--enable-precise-memory-info', '--js-flags=--expose-gc'] });
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  await page.goto(url + '?capture');
  await page.waitForFunction(() => window.creator && window.creator.store);
  if (lib) {
    const [chooser] = await Promise.all([page.waitForEvent('filechooser'), page.getByRole('button', { name: /import/i }).first().click()]);
    await chooser.setFiles(lib);
    await page.waitForFunction(() => window.creator.store.getState().packs.length > 0, null, { timeout: 30000 });
    await page.evaluate(() => { const st = window.creator.store.getState(); st.applyPack(st.packs[0]); });
    await page.waitForFunction(() => { const e = window.creator.engine(); return e && e.rig && e.rig.root.getObjectByName('PACK_body_test'); }, null, { timeout: 120000 });
  } else {
    await page.waitForFunction(() => { const e = window.creator.engine(); return e && e.rig; });
  }
  const res = await page.evaluate(async ([n, args_nopack]) => {
    const e = window.creator.engine(), st = window.creator.store;
    const orig = e.rebuild.bind(e); const rebuilds = [];
    e.rebuild = () => { const t = performance.now(); orig(); rebuilds.push(performance.now() - t); };
    const live = []; const frames = []; let last = performance.now(); let stop = false;
    const tick = (t) => { frames.push(t - last); last = t; if (!stop) requestAnimationFrame(tick); }; requestAnimationFrame(tick);
    const info = () => { const r = e.renderer.info; return { geometries: r.memory.geometries, textures: r.memory.textures, programs: r.programs ? r.programs.length : 0 }; };
    await new Promise((ok) => setTimeout(ok, 1500)); const gpu0 = info();
    if (window.gc) window.gc(); const heap0 = performance.memory ? performance.memory.usedJSHeapSize : 0;
    const series = [{ i: 0, ...gpu0 }];
    for (let i = 1; i <= n; i++) {
      const t0 = performance.now(); st.getState().setValue('face.round', (i * 7) % 100 + 1);
      await new Promise((ok) => { const poll = () => { const r = e.rig; const packed = args_nopack ? (r && r.identity.values['face.round'] === (i * 7) % 100 + 1 ? r.root : null) : r && r.root.getObjectByName('PACK_body_test'); const m = args_nopack ? (packed ? (i * 7 % 100 + 1) / 100 : null) : packed && (() => { let v = null; packed.traverse((o) => { if (o.isMesh && o.morphTargetDictionary && 'ID-FaceRound' in o.morphTargetDictionary) v = o.morphTargetInfluences[o.morphTargetDictionary['ID-FaceRound']]; }); return v; })(); if (m !== null && Math.abs(m - ((i * 7) % 100 + 1) / 100) < 0.01) ok(); else setTimeout(poll, 5); }; poll(); });
      live.push(performance.now() - t0);
      if (i % 25 === 0) series.push({ i, ...info() });
    }
    stop = true; if (window.gc) window.gc(); const heap1 = performance.memory ? performance.memory.usedJSHeapSize : 0;
    await new Promise((ok) => setTimeout(ok, 1500)); const gpu1 = info();
    const q = (a, p) => [...a].sort((x, y) => x - y)[Math.floor(a.length * p)];
    return { rebuildMs: { median: q(rebuilds, 0.5), max: Math.max(...rebuilds) }, liveMs: { median: q(live, 0.5), max: Math.max(...live) }, frames: frames.length, worstFrameMs: Math.max(...frames), heapGrowthMB: +((heap1 - heap0) / 1048576).toFixed(1), rebuilds: rebuilds.length, gpu: { before: gpu0, after: gpu1 }, series };
  }, [changes, !lib]);
  console.log(JSON.stringify(res, null, 1));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
