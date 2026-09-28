import type { ScanResult } from './importer';

interface CreatorHost {
  pickFolder(title?: string): Promise<string | null>;
  scanLibrary(folder: string): Promise<ScanResult>;
  saveJson(defaultName: string, text: string): Promise<string | null>;
  openJson(): Promise<{ path: string; text: string } | null>;
}

declare global {
  interface Window {
    creatorHost?: CreatorHost;
  }
}

export const host: CreatorHost | undefined = typeof window !== 'undefined' ? window.creatorHost : undefined;
export const isDesktop = !!host;

/** Browser-only fallback: object URLs for files picked through a folder input, keyed by relative path. */
const browserUrls = new Map<string, string>();

export function assetUrl(path: string): string {
  if (isDesktop) return `pack://local/${encodeURI(path.replace(/^\/+/, ''))}`;
  return browserUrls.get(path) ?? path;
}

export function resolveRelative(fromFile: string, rel: string): string {
  const parts = fromFile.split('/');
  parts.pop();
  for (const seg of rel.split('/')) {
    if (seg === '..') parts.pop();
    else if (seg !== '.') parts.push(seg);
  }
  return parts.join('/');
}

function pickBrowserFolder(): Promise<FileList | null> {
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    (input as HTMLInputElement & { webkitdirectory: boolean }).webkitdirectory = true;
    input.multiple = true;
    input.onchange = () => resolve(input.files);
    input.oncancel = () => resolve(null);
    input.click();
  });
}

export async function chooseAndScanLibrary(): Promise<ScanResult | null> {
  if (host) {
    const folder = await host.pickFolder('Import Library: choose the library root or one category folder');
    if (!folder) return null;
    return host.scanLibrary(folder);
  }
  const files = await pickBrowserFolder();
  if (!files || files.length === 0) return null;
  const list = Array.from(files);
  const first = (list[0] as File & { webkitRelativePath: string }).webkitRelativePath;
  const root = first.split('/')[0];
  const scan: ScanResult = { root, files: [], assets: [], relativeOnly: true };
  for (const f of list) {
    const rel = (f as File & { webkitRelativePath: string }).webkitRelativePath;
    const name = rel.split('/').pop() ?? '';
    if (name === 'manifest.json' || name === 'pack.json') {
      scan.files.push({ path: rel, text: await f.text() });
    } else if (/\.(gltf|glb|bin|png|jpe?g|webp|json)$/i.test(name)) {
      browserUrls.set(rel, URL.createObjectURL(f));
      scan.assets.push({ path: rel, text: /\.json$/i.test(name) ? await f.text() : undefined });
    }
  }
  return scan;
}

export async function saveTextFile(defaultName: string, text: string): Promise<string | null> {
  if (host) return host.saveJson(defaultName, text);
  const blob = new Blob([text], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = defaultName;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  return defaultName;
}

export async function openTextFile(): Promise<{ path: string; text: string } | null> {
  if (host) return host.openJson();
  return new Promise((resolve) => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json,application/json';
    input.onchange = async () => {
      const f = input.files?.[0];
      resolve(f ? { path: f.name, text: await f.text() } : null);
    };
    input.oncancel = () => resolve(null);
    input.click();
  });
}
