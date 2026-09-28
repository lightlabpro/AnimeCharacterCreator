import type { ReactNode } from 'react';

/** Original line icons drawn on a 24 unit grid. Stroke only, so they inherit the current text color. */
const P: Record<string, ReactNode> = {
  actor: <><circle cx="12" cy="7.5" r="3.5" /><path d="M5 20c.8-4 3.6-6 7-6s6.2 2 7 6" /></>,
  head: <><path d="M12 3.5c-3.9 0-6.5 2.8-6.5 6.6 0 2.7 1.2 4.6 2.6 5.9V19h7.8v-3c1.4-1.3 2.6-3.2 2.6-5.9 0-3.8-2.6-6.6-6.5-6.6Z" /><path d="M9.5 11h.01M14.5 11h.01" /><path d="M10.5 14.5c.9.6 2.1.6 3 0" /></>,
  body: <><circle cx="12" cy="4.5" r="2" /><path d="M8 8.5h8l-1 6h-6l-1-6Z" /><path d="M9.5 14.5 9 21M14.5 14.5 15 21M8 8.5 5.5 13M16 8.5l2.5 4.5" /></>,
  hair: <><path d="M5 14c0-6 3-9.5 7-9.5s7 3.5 7 9.5" /><path d="M5 14c1.5-1 2.5-3 3-5.5M19 14c-1.5-1-2.5-3-3-5.5M12 4.5c-.5 2.5-2 4.5-4 5.5M12 4.5c.5 2.5 2 4.5 4 5.5" /><path d="M5 14v5M19 14v5" /></>,
  facialHair: <><path d="M6 10c0 5 2.7 9.5 6 9.5s6-4.5 6-9.5" /><path d="M8 12.5c1.2-1 2.6-1.4 4-1.4s2.8.4 4 1.4" /><path d="M10.5 15.5h3" /></>,
  elements: <><path d="M7 4c1.5 2 1.8 4 1 6.5M17 4c-1.5 2-1.8 4-1 6.5" /><circle cx="12" cy="14" r="5" /><path d="M10 14h.01M14 14h.01" /></>,
  outfit: <><path d="M9 3.5 5 5.5 3 10l3 1.5V20.5h12V11.5l3-1.5-2-4.5-4-2c-.4 1.5-1.6 2.5-3 2.5S9.4 5 9 3.5Z" /></>,
  accessory: <><path d="M4 11c0-3.3 3.6-6 8-6s8 2.7 8 6" /><path d="M3 11h18v2H3z" /><path d="M8 13v3M16 13v3" /></>,
  material: <><circle cx="12" cy="12" r="8" /><path d="M12 4a8 8 0 0 0 0 16" /><path d="M8 8.5h.01M7 13h.01M10 16.5h.01" /></>,
  motion: <><circle cx="13" cy="4.5" r="2" /><path d="m10 21 2-6-2.5-2.5 1-4.5 3 2.5 3.5.5" /><path d="m9.5 8-3.5 1.5L5 13M12 15l3.5 2 1 4" /></>,
  expression: <><circle cx="12" cy="12" r="8.5" /><path d="M8.5 14c.9 1.6 2.1 2.4 3.5 2.4s2.6-.8 3.5-2.4" /><path d="M9 9.5h.01M15 9.5h.01" /></>,
  favorites: <><path d="m12 3.8 2.5 5.1 5.6.8-4 4 1 5.6L12 16.6l-5.1 2.7 1-5.6-4-4 5.6-.8L12 3.8Z" /></>,
  star: <><path d="m12 3.8 2.5 5.1 5.6.8-4 4 1 5.6L12 16.6l-5.1 2.7 1-5.6-4-4 5.6-.8L12 3.8Z" /></>,
  modify: <><path d="M4 7h10M18 7h2M4 17h4M12 17h8" /><circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /><path d="M4 12h6M14 12h6" /><circle cx="12" cy="12" r="2" /></>,
  mixer: <><circle cx="12" cy="12" r="8.5" /><path d="M12 3.5v8.5l6 6" /><circle cx="12" cy="12" r="1.8" /></>,
  appearance: <><path d="M4 8.5 12 4l8 4.5-8 4.5-8-4.5Z" /><path d="m4 12.5 8 4.5 8-4.5" /><path d="m4 16.5 8 4.5 8-4.5" /></>,
  face: <><path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" /><path d="M9 10h.01M15 10h.01M9.5 14.5c1.4 1 3.6 1 5 0" /></>,
  camFront: <><rect x="5" y="4" width="14" height="16" rx="2" /><circle cx="12" cy="10" r="2.5" /><path d="M8.5 17c.6-1.8 1.9-2.8 3.5-2.8s2.9 1 3.5 2.8" /></>,
  camSide: <><rect x="5" y="4" width="14" height="16" rx="2" /><path d="M11 7.5c1.9 0 3 1.2 3 2.8 0 1.2-.6 2-1 2.2l.6 1.5h-2.1" /><path d="M9.5 17c.3-1.4 1.1-2.6 2.5-3" /></>,
  camBack: <><rect x="5" y="4" width="14" height="16" rx="2" /><circle cx="12" cy="10" r="2.5" /><path d="M8.5 17c.6-1.8 1.9-2.8 3.5-2.8s2.9 1 3.5 2.8M9.8 8.8c1.3.6 3.1.6 4.4 0" /></>,
  camQuarter: <><path d="M12 3.5 19.5 8v8L12 20.5 4.5 16V8L12 3.5Z" /><path d="M12 12 19.5 8M12 12v8.5M12 12 4.5 8" /></>,
  camFace: <><path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16" /><circle cx="12" cy="11" r="3" /></>,
  camUpper: <><path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8" /><circle cx="12" cy="9" r="2.5" /><path d="M7 19c.7-3 2.6-4.8 5-4.8s4.3 1.8 5 4.8" /></>,
  frame: <><path d="M4 9V4h5M15 4h5v5M20 15v5h-5M9 20H4v-5" /><rect x="9" y="9" width="6" height="6" rx="1" /></>,
  turntable: <><ellipse cx="12" cy="16.5" rx="8" ry="3" /><path d="M12 13.5V5" /><path d="m9 7 3-2.5L15 7" /><path d="M18.5 12.5c1 .7 1.5 1.5 1.5 2.5" /></>,
  drag: <><path d="M9 11V5.5a1.5 1.5 0 0 1 3 0V10" /><path d="M12 10V8.5a1.5 1.5 0 0 1 3 0V11" /><path d="M15 11v-.5a1.5 1.5 0 0 1 3 0V14c0 3.6-2.4 6.5-6 6.5-2.6 0-4-1.3-5.3-3.2L4.6 14a1.5 1.5 0 0 1 2.4-1.8L9 14" /></>,
  camera: <><path d="M4 8.5A1.5 1.5 0 0 1 5.5 7h2l1.5-2.5h6L16.5 7h2A1.5 1.5 0 0 1 20 8.5v9a1.5 1.5 0 0 1-1.5 1.5h-13A1.5 1.5 0 0 1 4 17.5v-9Z" /><circle cx="12" cy="13" r="3.5" /></>,
  bookmark: <><path d="M7 4h10v16l-5-3.5L7 20V4Z" /></>,
  move: <><path d="M12 3v18M3 12h18" /><path d="m9 6 3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3" /></>,
  rotate: <><path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3" /><path d="M19.5 4v4h-4" /></>,
  scale: <><rect x="4" y="10" width="10" height="10" rx="1" /><path d="M13 4h7v7M20 4l-8 8" /></>,
  reset: <><path d="M4.5 12a7.5 7.5 0 1 0 2.2-5.3" /><path d="M4.5 4v4h4" /></>,
  undo: <><path d="M9 14 4.5 9.5 9 5" /><path d="M5 9.5h9a5.5 5.5 0 0 1 0 11h-3" /></>,
  redo: <><path d="m15 14 4.5-4.5L15 5" /><path d="M19 9.5h-9a5.5 5.5 0 0 0 0 11h3" /></>,
  import: <><path d="M12 4v11M7.5 10.5 12 15l4.5-4.5" /><path d="M4.5 15.5v3A1.5 1.5 0 0 0 6 20h12a1.5 1.5 0 0 0 1.5-1.5v-3" /></>,
  folder: <><path d="M3.5 7A1.5 1.5 0 0 1 5 5.5h4.2l2 2H19A1.5 1.5 0 0 1 20.5 9v8.5A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5V7Z" /></>,
  save: <><path d="M5 4h11l3 3v12a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4Z" /><path d="M8 4v5h7V4M8 20v-6h8v6" /></>,
  file: <><path d="M6 3.5h8l4 4V20a.5.5 0 0 1-.5.5h-11A.5.5 0 0 1 6 20V3.5Z" /><path d="M14 3.5v4h4" /></>,
  plus: <><path d="M12 5v14M5 12h14" /></>,
  search: <><circle cx="11" cy="11" r="6" /><path d="m19.5 19.5-4-4" /></>,
  eye: <><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" /><circle cx="12" cy="12" r="2.8" /></>,
  eyeOff: <><path d="M4 4l16 16" /><path d="M10 6c.6-.3 1.3-.5 2-.5 6 0 9.5 6.5 9.5 6.5a17 17 0 0 1-2.6 3.3M6.2 7.8A16 16 0 0 0 2.5 12S6 18.5 12 18.5c1.4 0 2.7-.4 3.8-.9" /></>,
  lock: <><rect x="5" y="10.5" width="14" height="9.5" rx="1.5" /><path d="M8 10.5V8a4 4 0 0 1 8 0v2.5" /></>,
  play: <><path d="M8 5.5v13l10.5-6.5L8 5.5Z" /></>,
  stop: <><rect x="6.5" y="6.5" width="11" height="11" rx="1.5" /></>,
  loop: <><path d="M17 3.5 20 6.5l-3 3" /><path d="M4 12v-1.5a4 4 0 0 1 4-4h12M7 20.5 4 17.5l3-3" /><path d="M20 12v1.5a4 4 0 0 1-4 4H4" /></>,
  chevronRight: <><path d="m9.5 6 6 6-6 6" /></>,
  chevronDown: <><path d="m6 9.5 6 6 6-6" /></>,
  chevronUp: <><path d="m6 14.5 6-6 6 6" /></>,
  close: <><path d="M6 6l12 12M18 6 6 18" /></>,
  more: <><path d="M6 12h.01M12 12h.01M18 12h.01" /></>,
  check: <><path d="m5 12.5 4.5 4.5L19 7.5" /></>,
  info: <><circle cx="12" cy="12" r="8.5" /><path d="M12 11v5M12 8h.01" /></>,
  warning: <><path d="M12 4 21 19.5H3L12 4Z" /><path d="M12 10v4.5M12 17h.01" /></>,
  error: <><circle cx="12" cy="12" r="8.5" /><path d="m9 9 6 6M15 9l-6 6" /></>,
  success: <><circle cx="12" cy="12" r="8.5" /><path d="m8 12.3 2.8 2.7L16 9.5" /></>,
  grid: <><rect x="4" y="4" width="6.5" height="6.5" rx="1" /><rect x="13.5" y="4" width="6.5" height="6.5" rx="1" /><rect x="4" y="13.5" width="6.5" height="6.5" rx="1" /><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="1" /></>,
  list: <><path d="M9 6.5h11M9 12h11M9 17.5h11" /><path d="M4.5 6.5h.01M4.5 12h.01M4.5 17.5h.01" /></>,
  refresh: <><path d="M19.5 9A7.5 7.5 0 0 0 5.6 7.5M4.5 15a7.5 7.5 0 0 0 13.9 1.5" /><path d="M19.5 4v5h-5M4.5 20v-5h5" /></>,
  image: <><rect x="4" y="5" width="16" height="14" rx="2" /><circle cx="9" cy="10" r="1.6" /><path d="m20 16-4.5-4.5L7 19" /></>,
  merge: <><path d="M7 4v4.5c0 2.5 5 3.5 5 6.5v5M17 4v4.5c0 2.5-5 3.5-5 6.5" /><path d="m9 17.5 3 3 3-3" /></>,
  trash: <><path d="M4.5 7h15M9.5 7V4.5h5V7" /><path d="M6.5 7l1 12.5a1 1 0 0 0 1 .9h7a1 1 0 0 0 1-.9l1-12.5" /><path d="M10 11v5.5M14 11v5.5" /></>,
  layers: <><path d="M4 8.5 12 4l8 4.5-8 4.5-8-4.5Z" /><path d="m4 12.5 8 4.5 8-4.5" /><path d="m4 16.5 8 4.5 8-4.5" /></>,
  dice: <><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M8.5 8.5h.01M15.5 8.5h.01M12 12h.01M8.5 15.5h.01M15.5 15.5h.01" /></>,
  child: <><circle cx="12" cy="8" r="3" /><path d="M7 20c.5-3.5 2.5-5.5 5-5.5s4.5 2 5 5.5" /></>,
  family: <><circle cx="8" cy="7.5" r="2.5" /><circle cx="16.5" cy="9.5" r="2" /><path d="M3.5 19c.5-3.4 2.2-5.5 4.5-5.5s4 2.1 4.5 5.5M13 19c.3-2.4 1.6-4 3.5-4s3.2 1.6 3.5 4" /></>,
  robot: <><rect x="5" y="7" width="14" height="11" rx="2.5" /><path d="M12 7V4M12 4h.01" /><path d="M9.5 12h.01M14.5 12h.01M9.5 15h5" /><path d="M5 11H3.5v3H5M19 11h1.5v3H19" /></>,
  dragon: <><path d="M3.5 17c2.5 0 4-1.5 5-4 1-2.5 2.5-4 5-4 1.5 0 2.5-.6 3.5-2l1.5 1.5L20.5 7c0 3-2 5-4 5.5l.5 3.5" /><path d="M8.5 13 5 10.5M11 9.5 9.5 5.5l3 2" /><path d="M8 17v2.5M13.5 16v3.5" /></>,
  help: <><circle cx="12" cy="12" r="8.5" /><path d="M9.8 9.5a2.3 2.3 0 1 1 3.3 2.1c-.7.3-1.1 1-1.1 1.7v.2M12 16.5h.01" /></>,
  keyboard: <><rect x="3" y="6.5" width="18" height="11" rx="2" /><path d="M7 10h.01M10 10h.01M13 10h.01M16 10h.01M7 13.5h.01M17 13.5h.01M10 13.5h4" /></>,
  sparkle: <><path d="M12 4v4M12 16v4M4 12h4M16 12h4" /><path d="m7 7 1.8 1.8M15.2 15.2 17 17M17 7l-1.8 1.8M8.8 15.2 7 17" /></>,
  palette: <><path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.2 0 1.8-.8 1.8-1.7 0-1.3-1.3-1.6-1.3-2.8 0-.9.7-1.5 1.7-1.5h2.3a4 4 0 0 0 4-4c0-3.9-3.8-7-8.5-7Z" /><path d="M7.5 11h.01M9.5 7.5h.01M14 7h.01M17 10h.01" /></>,
  sidebar: <><rect x="3.5" y="4.5" width="17" height="15" rx="2" /><path d="M9 4.5v15" /></>,
  sidebarRight: <><rect x="3.5" y="4.5" width="17" height="15" rx="2" /><path d="M15 4.5v15" /></>,
  physics: <><path d="M5 5c3 2 3 5 0 7s-3 5 0 7" /><path d="M12 5c3 2 3 5 0 7s-3 5 0 7" /><path d="M19 5c-1.5 1-2 2.5-1.5 4" /></>,
  pose: <><circle cx="12" cy="4.5" r="2" /><path d="M5 8.5 12 9l7-2.5M12 9v5l-3 6.5M12 14l3.5 6.5" /></>,
  sliders: <><path d="M4 7h10M18 7h2M4 17h4M12 17h8" /><circle cx="16" cy="7" r="2" /><circle cx="10" cy="17" r="2" /></>,
  wrinkle: <><path d="M5 9c2-1.5 4-1.5 7 0s5 1.5 7 0M5 13c2-1.5 4-1.5 7 0s5 1.5 7 0" /></>,
  blink: <><path d="M3 12c2.5 3 5.5 4.5 9 4.5s6.5-1.5 9-4.5" /><path d="M6 15.2 4.5 17.5M12 16.5V19M18 15.2l1.5 2.3" /></>,
  wide: <><path d="M3 12c2.5-3 5.5-4.5 9-4.5s6.5 1.5 9 4.5" /><path d="M6 8.8 4.5 6.5M12 7.5V5M18 8.8l1.5-2.3" /></>,
};

export type IconName = keyof typeof P;

export function Icon({ name, size = 16, stroke = 1.7, title }: { name: string; size?: number; stroke?: number; title?: string }) {
  const body = P[name];
  return (
    <svg className="ico" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden={title ? undefined : true} role={title ? 'img' : undefined}>
      {title && <title>{title}</title>}
      {body ?? P.more}
    </svg>
  );
}

export const CATEGORY_ICON: Record<string, string> = {
  Actor: 'actor', Head: 'head', Body: 'body', Hair: 'hair', 'Facial Hair': 'facialHair', Elements: 'elements', Outfit: 'outfit',
  Accessory: 'accessory', Material: 'material', Motion: 'motion', Expression: 'expression', Favorites: 'favorites',
};
