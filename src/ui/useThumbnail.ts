import { useEffect, useMemo, useRef, useState } from 'react';
import { useStore } from '../state/store';
import { cachedThumbnail, onThumbnailsCleared, requestThumbnail, type ThumbJob } from '../viewport/thumbnails';

/** Renders a thumbnail once the element scrolls into view. Returns the element ref and the image URL: null while pending, empty if the render failed. */
export function useThumbnail<T extends Element>(key: string | null, make: (() => ThumbJob) | undefined) {
  const ref = useRef<T>(null);
  const packs = useStore((s) => s.packs);
  const packMap = useMemo(() => new Map(packs.map((p) => [p.id, p])), [packs]);
  const [url, setUrl] = useState<string | null>(() => (key ? cachedThumbnail(key) ?? null : null));
  const [epoch, setEpoch] = useState(0);
  const makeRef = useRef(make);
  makeRef.current = make;

  useEffect(() => onThumbnailsCleared(() => setEpoch((e) => e + 1)), []);

  useEffect(() => {
    if (!key || !makeRef.current) {
      setUrl(null);
      return;
    }
    const hit = cachedThumbnail(key);
    if (hit) {
      setUrl(hit);
      return;
    }
    setUrl(null);
    const el = ref.current;
    if (!el) return;
    let cancel: (() => void) | null = null;
    const io = new IntersectionObserver((entries) => {
      if (!entries.some((e) => e.isIntersecting) || cancel) return;
      io.disconnect();
      cancel = requestThumbnail(key, () => makeRef.current!(), packMap, setUrl);
    }, { rootMargin: '120px' });
    io.observe(el);
    return () => {
      io.disconnect();
      cancel?.();
    };
  }, [key, packMap, epoch]);

  return [ref, url] as const;
}
