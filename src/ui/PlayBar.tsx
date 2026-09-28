import { useEffect, useState } from 'react';
import { BODY_POSES, CLIPS, CLIP_BY_ID } from '../model/performance';
import { useStore } from '../state/store';
import { Toggle } from './controls';

export function PlayBar() {
  const perf = useStore((s) => s.perf);
  const st = useStore.getState;
  const clip = perf.clip;
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!clip) {
      setProgress(0);
      return;
    }
    let raf = 0;
    const tick = () => {
      const def = CLIP_BY_ID[clip.id];
      if (def) {
        const t = (performance.now() / 1000 - clip.start) * clip.speed;
        setProgress(clip.loop ? (t % def.duration) / def.duration : Math.min(1, t / def.duration));
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

  return (
    <div className="playbar">
      <div className="row">
        <span className="label">Clip</span>
        {CLIPS.map((c) => (
          <button key={c.id} className={`chip${clip?.id === c.id ? ' on' : ''}`} onClick={() => (clip?.id === c.id ? st().stopClip() : st().playClip(c.id))}>{c.label}</button>
        ))}
        <button className="btn small" disabled={!clip} onClick={() => st().stopClip()} title="Stop">■ Stop</button>
        <Toggle label="Loop" checked={clip?.loop ?? false} onChange={(v) => clip && st().setPerf({ clip: { ...clip, loop: v } })} />
        <select className="inp" value={clip?.speed ?? 1} disabled={!clip} onChange={(e) => setSpeed(Number(e.target.value))} title="Speed">
          {[0.25, 0.5, 1, 1.5, 2].map((s) => <option key={s} value={s}>{s}×</option>)}
        </select>
        <span className="grow" />
        <Toggle label="Auto blink" checked={perf.autoBlink} onChange={(v) => st().setPerf({ autoBlink: v })} />
        <Toggle label="Wrinkles" checked={perf.wrinklePreview} onChange={(v) => st().setPerf({ wrinklePreview: v })} title="Show expression wrinkles in the viewport" />
        <button className="btn small" onClick={() => st().resetPerformance()} title="Neutral face, centered gaze and head. Identity is untouched.">Reset performance</button>
      </div>
      <div className="timeline" title={clip ? `${CLIP_BY_ID[clip.id]?.label} ${Math.round(progress * 100)}%` : 'No clip playing'}>
        <div style={{ width: `${progress * 100}%` }} />
      </div>
      <div className="row">
        <span className="label">Pose</span>
        {BODY_POSES.map((p) => (
          <button key={p.id} className={`chip${perf.bodyPose === p.id ? ' on' : ''}`} onClick={() => st().setPerf({ bodyPose: p.id })}>{p.label}</button>
        ))}
      </div>
    </div>
  );
}
