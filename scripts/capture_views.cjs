/**
 * Captures clean, transparent, fixed-view renders of the creator's current character for the render validator.
 *
 *   node scripts/capture_views.cjs --out work/app --url http://localhost:5173 [--views front,side,back,face] [--size 768]
 *        [--identity character.json] [--bald]
 *
 * Needs Playwright (use the preinstalled one) and the dev server, or any build opened with ?capture.
 * Then: python3 .claude/skills/render-validator/scripts/validate.py measure work/x --view front=work/app/front.png ...
 */
const fs = require('fs');
const path = require('path');
const args = Object.fromEntries(process.argv.slice(2).reduce((a, x, i, all) => (x.startsWith('--') ? [...a, [x.slice(2), all[i + 1] && !all[i + 1].startsWith('--') ? all[i + 1] : true]] : a), []));
const out = args.out || 'work/app';
const url = args.url || 'http://localhost:5173';
const size = Number(args.size || 768);
const views = args.views ? String(args.views).split(',') : undefined;
const playwright = process.env.PLAYWRIGHT_PATH || '/opt/node-tools/node_modules/playwright';

(async () => {
  const { chromium } = require(playwright);
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || '/opt/pw-browsers/chromium', args: ['--use-gl=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
  const errors = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto(url + (url.includes('?') ? '&' : '?') + 'capture');
  await page.waitForFunction(() => window.creator && window.creator.store, null, { timeout: 30000 });
  if (args.identity) {
    const identity = JSON.parse(fs.readFileSync(args.identity, 'utf8')).identity ?? JSON.parse(fs.readFileSync(args.identity, 'utf8'));
    await page.evaluate((id) => window.creator.store.getState().loadIdentity(id), identity);
  }
  if (args.bald) {
    await page.evaluate(() => {
      const st = window.creator.store.getState();
      st.commit((id) => { for (const k of ['front', 'back', 'sides']) id.hair[k] = { ...id.hair[k], id: 'none' }; id.hair.extras = []; });
    });
  }
  const shots = await page.evaluate(async ([v, s]) => window.creator.captureViews({ views: v, size: s }), [views, size]);
  fs.mkdirSync(out, { recursive: true });
  for (const [view, dataUrl] of Object.entries(shots)) {
    const file = path.join(out, `${view}.png`);
    fs.writeFileSync(file, Buffer.from(dataUrl.split(',')[1], 'base64'));
    console.log('wrote', file);
  }
  if (errors.length) console.error('page errors:', errors.slice(0, 3));
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
