import { useEffect, useMemo, useRef } from 'react';
import { create } from 'zustand';
import { BEAST_REGION_DRAG, CONTROL_BY_ID, REGION_DRAG, ROBOT_REGION_DRAG, isControlVisible } from '../model/controls';
import type { Region } from '../model/types';
import { useStore } from '../state/store';
import { Engine } from '../viewport/engine';

export const useHover = create<{ region: Region | null; equip: string | null; dragKeys: string[] }>(() => ({ region: null, equip: null, dragKeys: [] }));

let engineRef: Engine | null = null;
export const getEngine = () => engineRef;

const REGION_LABEL: Partial<Record<Region, string>> = {
  skull: 'Skull', eyes: 'Eyes', brows: 'Brows', nose: 'Nose', mouth: 'Mouth', jaw: 'Jaw and chin', cheeks: 'Cheeks', ears: 'Ears', neck: 'Neck',
  chest: 'Chest', waist: 'Waist', hips: 'Hips', shoulders: 'Shoulders', arms: 'Arms', hands: 'Hands', legs: 'Legs', feet: 'Feet', body: 'Body',
  hair: 'Hair', muzzle: 'Muzzle', tail: 'Tail', wings: 'Wings', horns: 'Horns', mane: 'Mane', frill: 'Frill', face: 'Face',
};
export const regionLabel = (r: Region | null) => (r ? REGION_LABEL[r] ?? r : '');

export function dragMapFor(kind: string) {
  return kind === 'beast' ? BEAST_REGION_DRAG : kind === 'robot' ? ROBOT_REGION_DRAG : REGION_DRAG;
}

export function Viewport() {
  const hostRef = useRef<HTMLDivElement>(null);
  const identity = useStore((s) => s.identity);
  const packs = useStore((s) => s.packs);
  const perf = useStore((s) => s.perf);
  const ui = useStore((s) => s.ui);
  const packMap = useMemo(() => new Map(packs.map((p) => [p.id, p])), [packs]);
  const dragState = useRef<{ keys: [string | undefined, string | undefined]; start: [number, number] } | null>(null);

  useEffect(() => {
    const host = hostRef.current!;
    const st = useStore.getState;
    const engine = new Engine(host, {
      onHover(region, equip) {
        const id = st().identity;
        const map = dragMapFor(id.bodyKind)[region as Region];
        const keys = map ? [map.frontX, map.frontY, map.sideX, map.sideY].filter((k): k is string => !!k) : [];
        useHover.setState({ region, equip, dragKeys: [...new Set(keys)] });
      },
      onPick(region, equip) {
        if (equip) {
          const isEquip = st().identity.equipped.some((e) => e.uid === equip);
          st().setUI({ selectedEquip: isEquip ? equip : null });
          return;
        }
        st().setUI({ selectedEquip: null });
        if (region) st().setUI({ rightPanel: 'modify', modifyTab: 'morphs', morphNode: `region:${region}`, morphSearch: '' });
      },
      onRegionDragStart(region, view) {
        const id = st().identity;
        const map = dragMapFor(id.bodyKind)[region];
        if (!map) return false;
        const ok = (k?: string) => (k && CONTROL_BY_ID[k] && isControlVisible(CONTROL_BY_ID[k], id.bodyKind, id.looks) ? k : undefined);
        const kx = ok(view === 'side' ? map.sideX ?? map.frontX : map.frontX);
        const ky = ok(view === 'side' ? map.sideY ?? map.frontY : map.frontY);
        if (!kx && !ky) return false;
        st().beginEdit();
        dragState.current = { keys: [kx, ky], start: [kx ? id.values[kx] ?? 0 : 0, ky ? id.values[ky] ?? 0 : 0] };
        st().setUI({ highlight: [region] });
        return true;
      },
      onRegionDrag(dx, dy) {
        const d = dragState.current;
        if (!d) return;
        if (d.keys[0]) st().setValueLive(d.keys[0], d.start[0] + dx * 60);
        if (d.keys[1]) st().setValueLive(d.keys[1], d.start[1] + dy * 60);
      },
      onRegionDragEnd() {
        dragState.current = null;
        st().endEdit();
        st().setUI({ highlight: null });
      },
      onGizmoStart() {
        st().beginEdit();
      },
      onGizmoChange(uid, p, r, s) {
        st().editLive((id) => {
          const e = id.equipped.find((x) => x.uid === uid);
          if (e) e.offset = { p, r, s };
        });
      },
      onGizmoEnd() {
        st().endEdit();
      },
      onClipFinished() {
        st().stopClip();
      },
      onPackReport(failed) {
        st().toast(`Could not load ${failed.map((f) => `${f.id} (${f.reason})`).join('; ')}`);
      },
    });
    engineRef = engine;
    return () => {
      engine.dispose();
      engineRef = null;
    };
  }, []);

  useEffect(() => {
    engineRef?.setCharacter(identity, packMap, perf.bodyPose);
    if (engineRef) engineRef.profile = identity.faceProfile;
  }, [identity, packMap, perf.bodyPose]);

  useEffect(() => {
    if (engineRef) engineRef.perf = perf;
  }, [perf]);

  useEffect(() => {
    const e = engineRef;
    if (!e) return;
    e.highlight = ui.highlight;
    e.selectedEquip = ui.selectedEquip;
    e.turntable = ui.turntable;
    e.shapeDrag = ui.shapeDrag;
    e.setGizmoMode(ui.gizmoMode);
    e.applySelection();
  }, [ui.highlight, ui.selectedEquip, ui.turntable, ui.shapeDrag, ui.gizmoMode, identity]);

  useEffect(() => {
    const req = ui.cameraRequest;
    if (!req || !engineRef) return;
    const saved = ui.savedViews.find((v) => v.name === req.name);
    engineRef.cameraPreset(req.name, saved);
  }, [ui.cameraRequest]);

  return <div className="viewport-canvas" ref={hostRef} />;
}
