import type * as THREE from 'three';
import type { ImportedPack } from '../library/importer';
import type { BodyPose } from '../model/performance';
import type { Identity } from '../model/types';
import { buildDragon } from './dragon';
import { buildHumanoid } from './humanoid';
import { buildRobot } from './robot';
import { createCtx, finishRig, type Rig } from './rig';

/** Builds the procedural placeholder rig for any body kind. Imported packs attach afterwards. */
export function buildRig(identity: Identity, packs: Map<string, ImportedPack>, pose: BodyPose): Rig {
  const ctx = createCtx(identity, packs, pose);
  let root: THREE.Group;
  let head: THREE.Object3D | null;
  if (identity.bodyKind === 'robot') ({ root, head } = buildRobot(ctx));
  else if (identity.bodyKind === 'beast') ({ root, head } = buildDragon(ctx));
  else ({ root, head } = buildHumanoid(ctx));
  return finishRig(ctx, root, head);
}
