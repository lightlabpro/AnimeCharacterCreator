import { useEffect, useRef, useState } from 'react';
import { BODY_POSES, CLIPS, CLIP_BY_ID } from '../model/performance';
import { useStore } from '../state/store';
import { Icon } from './icons';

export function PlayBar() {
  const perf = useStore((s) => s.perf);
  const st = useStore.getState;
  const clip = perf.clip;
  const [chosen, setChosen] = useState(CLIPS[0].id);
  const [time, setTime] = useState(0);
  const trackRef = useRef<HTMLDivElement>(null);
  const [scrubbing, setScrubbing] = useState(false);

  const selectedId = clip?.id ?? chosen;
  const def = CLIP_BY_ID[selectedId];
  const duration = def?.duration ?? 1;

  useEffect(() => {
    if (clip) setChosen(clip.id);
  }, [clip]);

  useEffect(() => {
    if (!clip) {
      setTime(0);
      return;
    }
    let raf = 0;
    const tick = () => {
      const d = CLIP_BY_ID[clip.id];
      if (d) {
        const t = (performance.now() / 1000 - clip.start) * clip.speed;
        setTime(clip.loop ? t % d.duration : Math.min(d.duration, t));
      }
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [clip]);

  const setSpeed = (speed: number) => {
    if (!clip) return;
    const now = performance.now() / 1000;
    const elapsed = (now - clip.start) * clip.speed;
    st().setPerf({ clip: { ...clip, speed, start: now - elapsed / speed } });
  };

  const seek = (clientX: number) => {
    const r = trackRef.current?.getBoundingClientRect();
    if (!r) return;
    const t = Math.max(0, Math.min(1, (clientX - r.left) / r.width)) * duration;
    const now = performance.now() / 1000;
    const cur = st().perf.clip ?? { id: selectedId, start: now, speed: 1, loop: CLIP_BY_ID[selectedId]?.loop ?? false };
    st().setPerf({ clip: { ...cur, id: selectedId, start: now - t / cur.speed } });
  };

  const fmt = (s: number) => s.toFixed(2);

  return (
    <div className="playbar">
      <div className="transport">
        <button className="play-btn" onClick={() => (clip ? st().stopClip() : st().playClip(chosen))} title={clip ? 'Stop (face clip)' : 'Play the chosen face clip'}>
          <Icon name={clip ? 'stop' : 'play'} size={14} stroke={2.2} />
        </button>
      </div>
      <select value={selectedId} onChange={(e) => {
        setChosen(e.target.value);
        if (clip) st().playClip(e.target.value, clip.loop);
      }} title="Face clip" className="clip-sel">
        {CLIPS.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
      </select>
      <button className={`icon-btn${clip?.loop ? ' on' : ''}`} disabled={!clip} onClick={() => clip && st().setPerf({ clip: { ...clip, loop: !clip.loop } })} title="Loop">
        <Icon name="loop" />
      </button>
      <select className="speed" value={clip?.speed ?? 1} disabled={!clip} onChange={(e) => setSpeed(Number(e.target.value))} title="Playback speed" style={{ width: 62 }}>
        {[0.25, 0.5, 1, 1.5, 2].map((s) => <option key={s} value={s}>{s}×</option>)}
      </select>

      <div className="timeline-wrap">
        <div
          ref={trackRef}
          className="timeline"
          title="Drag to scrub"
          onPointerDown={(e) => {
            (e.target as Element).setPointerCapture?.(e.pointerId);
            setScrubbing(true);
            seek(e.clientX);
          }}
          onPointerMove={(e) => scrubbing && seek(e.clientX)}
          onPointerUp={() => setScrubbing(false)}
          onPointerCancel={() => setScrubbing(false)}
        >
          <div className="track"><div className="fillbar" style={{ width: `${(time / duration) * 100}%` }} /></div>
          <div className="ticks" />
          <div className="head" style={{ left: `${(time / duration) * 100}%` }} />
        </div>
        <span className="time">{fmt(time)} / {fmt(duration)}s</span>
      </div>

      <div className="divider" />
      <div className="group" title="Body pose for checking fit">
        <span className="lbl"><Icon name="pose" size={15} /></span>
        <select value={perf.bodyPose} onChange={(e) => st().setPerf({ bodyPose: e.target.value as typeof perf.bodyPose })} className="pose-sel">
          {BODY_POSES.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
        </select>
      </div>
      <div className="divider" />
      <div className="group tight">
        <button className={`icon-btn${perf.autoBlink ? ' on' : ''}`} onClick={() => st().setPerf({ autoBlink: !perf.autoBlink })} title={`Auto blink: ${perf.autoBlink ? 'on' : 'off'}`}>
          <Icon name="blink" />
        </button>
        <button className={`icon-btn${perf.wrinklePreview ? ' on' : ''}`} onClick={() => st().setPerf({ wrinklePreview: !perf.wrinklePreview })} title={`Expression wrinkles in the viewport: ${perf.wrinklePreview ? 'on' : 'off'}`}>
          <Icon name="wrinkle" />
        </button>
        <button className="icon-btn opt" onClick={() => st().resetPerformance()} title="Reset performance: neutral face, centered gaze and head. Identity is untouched.">
          <Icon name="reset" />
        </button>
      </div>
    </div>
  );
}
