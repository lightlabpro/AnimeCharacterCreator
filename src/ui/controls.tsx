import { useRef, useState, type ReactNode } from 'react';
import { CONTROL_BY_ID, controlRange } from '../model/controls';
import { useStore } from '../state/store';
import { Icon } from './icons';

function fill(min: number, max: number, v: number): React.CSSProperties {
  const zero = min < 0 ? ((0 - min) / (max - min)) * 100 : 0;
  const at = ((v - min) / (max - min)) * 100;
  return { ['--a' as string]: `${Math.min(zero, at)}%`, ['--b' as string]: `${Math.max(zero, at)}%` };
}

function NumberField({ value, min, max, onCommit }: { value: number; min: number; max: number; onCommit: (v: number) => void }) {
  const [text, setText] = useState<string | null>(null);
  return (
    <input
      className="num-in"
      type="number"
      value={text ?? String(value)}
      min={min}
      max={max}
      onFocus={(e) => {
        setText(String(value));
        e.target.select();
      }}
      onChange={(e) => setText(e.target.value)}
      onBlur={() => {
        if (text !== null && text.trim() !== '' && !Number.isNaN(Number(text))) onCommit(Number(text));
        setText(null);
      }}
      onKeyDown={(e) => {
        if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
        if (e.key === 'Escape') {
          setText(null);
          (e.target as HTMLInputElement).blur();
        }
      }}
    />
  );
}

/** Identity slider for one control. Live drag is one undo step. Double-click resets to zero. */
export function ControlSlider({ id, showHint = false }: { id: string; showHint?: boolean }) {
  const ctl = CONTROL_BY_ID[id];
  const kind = useStore((s) => s.identity.bodyKind);
  const value = useStore((s) => s.identity.values[id] ?? 0);
  const fav = useStore((s) => s.favorites.includes(id));
  const locked = useStore((s) => s.ui.locked.includes(id));
  const dragging = useRef(false);
  if (!ctl) return null;
  const [lo, hi] = controlRange(ctl, kind);
  const st = useStore.getState;
  const onHover = (on: boolean) => {
    if (!dragging.current) st().setUI({ highlight: on ? [ctl.region] : null });
  };
  return (
    <div className={`slider${value !== 0 ? ' changed' : ''}`} onPointerEnter={() => onHover(true)} onPointerLeave={() => onHover(false)} title={ctl.hint}>
      <button className={`star${fav ? ' on' : ''}`} onClick={() => st().toggleFavorite(id)} title={fav ? 'Remove from favorites' : 'Add to favorites'}>
        <Icon name="star" size={12} stroke={fav ? 2.4 : 1.8} />
      </button>
      <div className="s-main" onDoubleClick={() => st().resetValue(id)}>
        <span className="s-label">
          {ctl.label}
          <span className="grow" />
          {value !== 0 && (
            <button className="s-btn" title="Reset to zero" onClick={() => st().resetValue(id)}>
              <Icon name="reset" size={11} stroke={2} />
            </button>
          )}
          <button
            className={`s-btn${locked ? ' on' : ''}`}
            title={locked ? 'Locked: Randomize leaves this slider alone. Click to unlock.' : 'Lock this slider so Randomize leaves it alone'}
            onClick={() => {
              const cur = st().ui.locked;
              st().setUI({ locked: locked ? cur.filter((x) => x !== id) : [...cur, id] });
            }}
          >
            <Icon name="lock" size={11} stroke={2} />
          </button>
        </span>
        <div className={`rng-wrap${lo < 0 ? ' bi' : ''}`}>
          <input
            className="rng"
            type="range"
            min={lo}
            max={hi}
            step={1}
            value={value}
            style={fill(lo, hi, value)}
            onPointerDown={() => {
              dragging.current = true;
              st().beginEdit();
            }}
            onPointerUp={() => {
              dragging.current = false;
              st().endEdit();
            }}
            onKeyDown={(e) => {
              if (e.shiftKey && (e.key === 'ArrowLeft' || e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
                e.preventDefault();
                const dir = e.key === 'ArrowLeft' || e.key === 'ArrowDown' ? -1 : 1;
                st().setValue(id, value + dir * 10);
              }
            }}
            onChange={(e) => {
              const v = Number(e.target.value);
              if (dragging.current) st().setValueLive(id, v);
              else st().setValue(id, v);
            }}
          />
        </div>
        {showHint && <span className="s-hint">{ctl.hint}</span>}
      </div>
      <NumberField value={value} min={lo} max={hi} onCommit={(v) => st().setValue(id, v)} />
    </div>
  );
}

/** Generic slider for performance, physics, layers, and colors. onLive fires while dragging, onCommit once at the end. */
export function ValueSlider(props: {
  label: string;
  value: number;
  min?: number;
  max?: number;
  step?: number;
  format?: (v: number) => string;
  onLive?: (v: number) => void;
  onCommit?: (v: number) => void;
  onBegin?: () => void;
  onReset?: () => void;
  disabled?: boolean;
}) {
  const { label, value, min = 0, max = 1, step = 0.01, format = (v) => v.toFixed(2), onLive, onCommit, onBegin, onReset, disabled } = props;
  const dragging = useRef(false);
  return (
    <div className="vslider" onDoubleClick={onReset} title={onReset ? 'Double-click to reset' : undefined}>
      <div className="vl" title={label}>{label}</div>
      <div className={`rng-wrap${min < 0 ? ' bi' : ''}`}>
        <input
          className="rng"
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          disabled={disabled}
          style={fill(min, max, value)}
          onPointerDown={() => {
            dragging.current = true;
            onBegin?.();
          }}
          onPointerUp={(e) => {
            dragging.current = false;
            onCommit?.(Number((e.target as HTMLInputElement).value));
          }}
          onChange={(e) => {
            const v = Number(e.target.value);
            if (dragging.current) (onLive ?? onCommit)?.(v);
            else (onCommit ?? onLive)?.(v);
          }}
        />
      </div>
      <span className="vv">{format(value)}</span>
    </div>
  );
}

export function Section({ title, count, children, defaultOpen = true, right }: { title: ReactNode; count?: ReactNode; children: ReactNode; defaultOpen?: boolean; right?: ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`section${open ? ' open' : ''}`}>
      <div className="sec-head" onClick={() => setOpen(!open)}>
        <span className="caret"><Icon name="chevronRight" size={13} stroke={2} /></span>
        <span>{title}</span>
        <span className="grow" />
        {count !== undefined && count !== null && count !== '' && <span className="pill">{count}</span>}
        {right && <span className="act" onClick={(e) => e.stopPropagation()}>{right}</span>}
      </div>
      {open && <div className="sec-body">{children}</div>}
    </div>
  );
}

export function Seg<T extends string>({ value, options, onChange, full = false }: { value: T; options: { id: T; label: string; disabled?: boolean; title?: string }[]; onChange: (v: T) => void; full?: boolean }) {
  return (
    <div className={`seg${full ? ' full' : ''}`}>
      {options.map((o) => (
        <button key={o.id} className={o.id === value ? 'on' : ''} disabled={o.disabled} title={o.title} onClick={() => onChange(o.id)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

const HEX = /^#[0-9a-fA-F]{6}$/;

export function ColorRow({ label, value, onChange, onLive, onBegin, onEnd }: { label: string; value: string; onChange: (v: string) => void; onLive?: (v: string) => void; onBegin?: () => void; onEnd?: () => void }) {
  const [text, setText] = useState<string | null>(null);
  const live = useRef(false);
  const shown = HEX.test(value) ? value : '#000000';
  return (
    <div className="color-row">
      <label>{label}</label>
      <div className="color-ctl">
        <span className="sw" style={{ background: shown }}>
          <input
            type="color"
            value={shown}
            title="Pick a color"
            onFocus={() => {
              if (onLive && !live.current) {
                live.current = true;
                onBegin?.();
              }
            }}
            onInput={(e) => (onLive ?? onChange)((e.target as HTMLInputElement).value)}
            onChange={(e) => (onLive ?? onChange)(e.target.value)}
            onBlur={() => {
              if (live.current) {
                live.current = false;
                onEnd?.();
              }
            }}
          />
        </span>
        <input
          type="text"
          value={text ?? value.toUpperCase()}
          spellCheck={false}
          onChange={(e) => setText(e.target.value)}
          onBlur={() => {
            const t = text?.trim();
            const hex = t && !t.startsWith('#') ? `#${t}` : t;
            if (hex && HEX.test(hex)) onChange(hex.toLowerCase());
            setText(null);
          }}
          onKeyDown={(e) => {
            if (e.key === 'Enter') (e.target as HTMLInputElement).blur();
          }}
        />
      </div>
    </div>
  );
}

export function Toggle({ label, checked, onChange, title }: { label: string; checked: boolean; onChange: (v: boolean) => void; title?: string }) {
  return (
    <label className="switch" title={title}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span className="track" />
      {label}
    </label>
  );
}

export function Note({ children, warn = false }: { children: ReactNode; warn?: boolean }) {
  return (
    <div className={`note${warn ? ' warn' : ''}`}>
      <Icon name={warn ? 'warning' : 'info'} size={14} />
      <div>{children}</div>
    </div>
  );
}
