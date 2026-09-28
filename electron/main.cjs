const { app, BrowserWindow, dialog, ipcMain, protocol, net } = require('electron');
const path = require('node:path');
const fs = require('node:fs/promises');
const { pathToFileURL } = require('node:url');

protocol.registerSchemesAsPrivileged([
  { scheme: 'pack', privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } },
]);

const importedRoots = new Set();
const SCAN_LIMIT = 20000;
const JSON_NAMES = new Set(['manifest.json', 'pack.json']);
const ASSET_EXT = new Set(['.gltf', '.glb', '.bin', '.png', '.jpg', '.jpeg', '.webp', '.ktx2', '.json']);

function toPosix(p) {
  return p.split(path.sep).join('/');
}

function isInsideImportedRoot(target) {
  const resolved = path.resolve(target);
  for (const root of importedRoots) {
    const rel = path.relative(root, resolved);
    if (rel === '' || (!rel.startsWith('..') && !path.isAbsolute(rel))) return true;
  }
  return false;
}

async function scanFolder(folder) {
  const files = [];
  const assets = [];
  let visited = 0;
  async function walk(dir, depth) {
    if (depth > 12 || visited > SCAN_LIMIT) return;
    let entries;
    try {
      entries = await fs.readdir(dir, { withFileTypes: true });
    } catch {
      return;
    }
    for (const entry of entries) {
      visited += 1;
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        if (entry.name === 'node_modules' || entry.name.startsWith('.')) continue;
        await walk(full, depth + 1);
      } else if (JSON_NAMES.has(entry.name)) {
        const text = await fs.readFile(full, 'utf8').catch(() => '');
        files.push({ path: toPosix(full), text });
      } else if (ASSET_EXT.has(path.extname(entry.name).toLowerCase())) {
        const isPresetJson = path.extname(entry.name).toLowerCase() === '.json';
        const text = isPresetJson ? await fs.readFile(full, 'utf8').catch(() => '') : undefined;
        assets.push({ path: toPosix(full), text });
      }
    }
  }
  await walk(folder, 0);
  return { root: toPosix(folder), files, assets };
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 960,
    minWidth: 1180,
    minHeight: 720,
    backgroundColor: '#1b1e24',
    title: 'Anime Character Creator',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.setMenuBarVisibility(false);
  const devUrl = process.env.CREATOR_DEV_URL;
  if (devUrl) win.loadURL(devUrl);
  else win.loadFile(path.join(__dirname, '..', 'dist', 'index.html'));
}

app.whenReady().then(() => {
  protocol.handle('pack', (request) => {
    const url = new URL(request.url);
    const filePath = path.resolve(decodeURIComponent(url.pathname.replace(/^\/+/, '')));
    if (!isInsideImportedRoot(filePath)) {
      return new Response('Not inside an imported library folder', { status: 403 });
    }
    return net.fetch(pathToFileURL(filePath).toString());
  });

  ipcMain.handle('dialog:pickFolder', async (event, title) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    const result = await dialog.showOpenDialog(win, { title: title || 'Import Library', properties: ['openDirectory'] });
    if (result.canceled || result.filePaths.length === 0) return null;
    return toPosix(result.filePaths[0]);
  });

  ipcMain.handle('library:scan', async (_event, folder) => {
    importedRoots.add(path.resolve(folder));
    return scanFolder(folder);
  });

  ipcMain.handle('file:saveJson', async (event, defaultName, text) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    const result = await dialog.showSaveDialog(win, {
      defaultPath: defaultName,
      filters: [{ name: 'Character or wheel', extensions: ['json'] }],
    });
    if (result.canceled || !result.filePath) return null;
    await fs.writeFile(result.filePath, text, 'utf8');
    return toPosix(result.filePath);
  });

  ipcMain.handle('file:openJson', async (event) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    const result = await dialog.showOpenDialog(win, {
      properties: ['openFile'],
      filters: [{ name: 'Character or wheel', extensions: ['json'] }],
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    const text = await fs.readFile(result.filePaths[0], 'utf8');
    return { path: toPosix(result.filePaths[0]), text };
  });

  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
