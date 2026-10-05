import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { newCharacter, randomizeIdentity } from '../src/model/character';
import { useStore } from '../src/state/store';

describe('morph glide', () => {
  let now = 0;
  let queue: ((t: number) => void)[] = [];
  const runFrames = (ms: number) => {
    const end = now + ms;
    while (now < end && queue.length) {
      now += 16;
      const q = queue;
      queue = [];
      q.forEach((f) => f(now));
    }
  };

  beforeEach(() => {
    now = 0;
    queue = [];
    vi.stubGlobal('requestAnimationFrame', (f: (t: number) => void) => void queue.push(f));
    vi.spyOn(performance, 'now').mockImplementation(() => now);
    useStore.getState().newCharacter('adult');
    useStore.setState({ past: [], future: [] });
  });
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('undo blends the value through the middle and lands exactly on the target', () => {
    const st = useStore.getState();
    st.setValue('face.round', 80);
    expect(useStore.getState().identity.values['face.round']).toBe(80);
    useStore.getState().undo();
    runFrames(100);
    const mid = useStore.getState().identity.values['face.round'] ?? 0;
    expect(mid).toBeGreaterThan(0);
    expect(mid).toBeLessThan(80);
    runFrames(400);
    expect(useStore.getState().identity.values['face.round'] ?? 0).toBe(0);
  });

  it('an edit during a glide settles on the target first, so history stays exact', () => {
    useStore.getState().setValue('face.round', 80);
    useStore.getState().undo();
    runFrames(50);
    useStore.getState().setValue('face.long', 30);
    const s = useStore.getState();
    expect(s.identity.values['face.round'] ?? 0).toBe(0);
    expect(s.identity.values['face.long']).toBe(30);
    expect(Number.isInteger(s.past[s.past.length - 1].values['face.round'] ?? 0)).toBe(true);
  });

  it('randomize leaves locked sliders alone', () => {
    useStore.getState().setUI({ locked: ['face.round'] });
    useStore.getState().setValue('face.round', 40);
    for (let i = 0; i < 10; i++) useStore.getState().randomize();
    runFrames(600);
    expect(useStore.getState().identity.values['face.round']).toBe(40);
  });
});

describe('randomizeIdentity locks', () => {
  it('skips locked controls and honours the variation amount', () => {
    const base = newCharacter('adult');
    base.values['eye.size'] = 33;
    const calm = randomizeIdentity(base, undefined, 0.1, () => 0.9, ['eye.size']);
    expect(calm.values['eye.size']).toBe(33);
    const wild = randomizeIdentity(base, ['nose.size'], 1, () => 0.99);
    const mild = randomizeIdentity(base, ['nose.size'], 0.1, () => 0.99);
    expect(Math.abs(wild.values['nose.size'] ?? 0)).toBeGreaterThan(Math.abs(mild.values['nose.size'] ?? 0));
  });
});
