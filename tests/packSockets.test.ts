import { describe, expect, it } from 'vitest';
import * as THREE from 'three';
import { moveEquipToPackSockets } from '../src/viewport/gltfPacks';
import type { Rig } from '../src/viewport/rig';

const equip = (socket: string | undefined, local: [number, number, number] = [0, 0, 0]) => {
  const o = new THREE.Group();
  o.position.set(...local);
  o.userData.pack = { id: 'p', socket };
  return o;
};
const rigWith = (objs: Record<string, THREE.Object3D>) => ({ equipObjects: objs }) as unknown as Rig;

describe('equipment packs follow the body pack sockets', () => {
  it('moves each pack-backed equip onto the SOC- node of the same name and keeps its local offset', () => {
    const scene = new THREE.Group();
    const bone = new THREE.Group();
    bone.position.set(0, 1, 0);
    const soc = new THREE.Group();
    soc.name = 'SOC-HeadTop';
    soc.position.set(0, 0.7, 0);
    bone.add(soc);
    scene.add(bone);
    const hat = equip('SOC-HeadTop', [0.01, 0.02, 0]);
    const placeholder = new THREE.Group();
    placeholder.add(hat);
    moveEquipToPackSockets(rigWith({ a: hat }), scene);
    expect(hat.parent).toBe(soc);
    expect(hat.position.toArray()).toEqual([0.01, 0.02, 0]);
    scene.updateMatrixWorld(true);
    expect(hat.getWorldPosition(new THREE.Vector3()).y).toBeCloseTo(1.7 + 0.02, 5);
  });

  it('prefers the socket_name custom property over the node name', () => {
    const scene = new THREE.Group();
    const node = new THREE.Group();
    node.name = 'Empty.012';
    node.userData.socket_name = 'SOC-Chest';
    scene.add(node);
    const e = equip('SOC-Chest');
    moveEquipToPackSockets(rigWith({ a: e }), scene);
    expect(e.parent).toBe(node);
  });

  it('leaves equipment alone when the pack has no matching socket, and ignores non-pack equipment', () => {
    const scene = new THREE.Group();
    const other = new THREE.Group();
    other.name = 'SOC-Back';
    scene.add(other);
    const home = new THREE.Group();
    const lost = equip('SOC-HeadTop');
    const procedural = new THREE.Group();
    home.add(lost, procedural);
    moveEquipToPackSockets(rigWith({ a: lost, b: procedural }), scene);
    expect(lost.parent).toBe(home);
    expect(procedural.parent).toBe(home);
  });

  it('does nothing for a body pack without any sockets', () => {
    const e = equip('SOC-HeadTop');
    const home = new THREE.Group();
    home.add(e);
    moveEquipToPackSockets(rigWith({ a: e }), new THREE.Group());
    expect(e.parent).toBe(home);
  });
});
