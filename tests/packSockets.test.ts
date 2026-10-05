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

import { applyPackPose } from '../src/viewport/gltfPacks';

describe('pack pose clips', () => {
  const scene = () => {
    const root = new THREE.Group();
    const arm = new THREE.Bone();
    arm.name = 'DEF-upperarm.L';
    root.add(arm);
    return { root, arm };
  };
  const clip = (name: string) => {
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 2);
    return new THREE.AnimationClip(name, 0.04, [new THREE.QuaternionKeyframeTrack('DEF-upperarm.L.quaternion', [0, 0.04], [...q.toArray(), ...q.toArray()])]);
  };

  it('applies the clip named for the chosen pose', () => {
    const { root, arm } = scene();
    expect(applyPackPose(root, [clip('POSE-tpose')], 'tpose')).toBe(true);
    expect(arm.quaternion.angleTo(new THREE.Quaternion())).toBeCloseTo(Math.PI / 2, 4);
  });

  it('samples the LAST frame, so a clip that goes from rest to the pose ends in the pose', () => {
    const { root, arm } = scene();
    const q = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), Math.PI / 2);
    const rest = new THREE.Quaternion();
    const c = new THREE.AnimationClip('POSE-tpose', 0.5, [new THREE.QuaternionKeyframeTrack('DEF-upperarm.L.quaternion', [0, 0.5], [...rest.toArray(), ...q.toArray()])]);
    expect(applyPackPose(root, [c], 'tpose')).toBe(true);
    expect(arm.quaternion.angleTo(new THREE.Quaternion())).toBeCloseTo(Math.PI / 2, 4);
  });

  it('matches names loosely, so POSE_TPose and pose.tpose work', () => {
    for (const name of ['POSE_TPose', 'pose.tpose', 'Pose-Tpose']) {
      const { root } = scene();
      expect(applyPackPose(root, [clip(name)], 'tpose')).toBe(true);
    }
  });

  it('leaves the rest pose alone when the pack has no clip for that pose', () => {
    const { root, arm } = scene();
    expect(applyPackPose(root, [clip('POSE-tpose')], 'hero')).toBe(false);
    expect(applyPackPose(root, [], 'apose')).toBe(false);
    expect(arm.quaternion.angleTo(new THREE.Quaternion())).toBe(0);
  });
});

import { applyIdentityToScene } from '../src/viewport/gltfPacks';
import { newCharacter } from '../src/model/character';

describe('bone names after the glTF loader sanitises them', () => {
  const rig = (loaderName: string, original?: string) => {
    const root = new THREE.Group();
    const bone = new THREE.Bone();
    bone.name = loaderName;
    if (original) bone.userData.name = original;
    root.add(bone);
    return { root, bone };
  };
  const longArm = () => {
    const id = newCharacter('adult');
    id.values['upperArm.length'] = 100;
    return id;
  };

  it('a Rigify style DEF-upper_arm.L bone still follows the upper arm length control', () => {
    // three's GLTFLoader strips the dot, so the loaded name is DEF-upper_armL and the original is in userData.name
    const { root, bone } = rig('DEF-upper_armL', 'DEF-upper_arm.L');
    applyIdentityToScene(root, longArm());
    expect(bone.scale.y).toBeGreaterThan(1.05);
  });

  it('also works when only the sanitised name is available', () => {
    const { root, bone } = rig('DEF-upper_armR');
    applyIdentityToScene(root, longArm());
    expect(bone.scale.y).toBeGreaterThan(1.05);
  });

  it('underscore sides and unsided bones still work', () => {
    const a = rig('DEF-upper_arm_L', 'DEF-upper_arm_L');
    const b = rig('DEF-upper_arm');
    applyIdentityToScene(a.root, longArm());
    applyIdentityToScene(b.root, longArm());
    expect(a.bone.scale.y).toBeGreaterThan(1.05);
    expect(b.bone.scale.y).toBeGreaterThan(1.05);
  });

  it('does not mistake an unrelated bone ending in a capital letter for a side', () => {
    const { root, bone } = rig('DEF-upper_armX');
    applyIdentityToScene(root, longArm());
    expect(bone.scale.y).toBe(1);
  });
});
