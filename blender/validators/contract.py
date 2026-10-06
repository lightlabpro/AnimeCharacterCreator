"""Names and lists copied from docs/CLAUDE_BUILD_PROMPT.md. Change them there first."""
from __future__ import annotations

from typing import Dict, Tuple

ADULT_BODY_KEYS = (
    "ID-BodyBulk ID-BodyLean ID-BodySoft ID-NarrowWaist ID-WideHips ID-BroadShoulders ID-Chest ID-Belly ID-Glute "
    "ID-ThighBulk ID-CalfBulk ID-UpperArmBulk ID-ForeArmBulk ID-MuscleChest ID-MuscleAbs ID-MuscleArms ID-MuscleLegs "
    "ID-NeckThickness ID-HandSize ID-FootSize ID-NailLength"
).split()

ADULT_FACE_KEYS = (
    "ID-FaceRound ID-FaceLong ID-FaceSquare ID-FaceHeart ID-FaceDiamond ID-JawWidth ID-JawHeight ID-ChinLength "
    "ID-ChinWidth ID-ChinCleft ID-CheekFull ID-CheekHollow ID-Cheekbone ID-BrowRidge ID-EarSize ID-EarPoint ID-EarOut "
    "ID-EarLobe ID-NoseBridgeHigh ID-NoseBridgeWide ID-NoseTipUp ID-NoseTipWide ID-NoseSmall ID-NoseLong ID-NostrilFlare "
    "ID-EyeSize ID-EyeHeight ID-EyeSpacing ID-EyeTilt ID-EyeAlmond ID-EyeRound ID-EyeNarrow ID-EyeDroop ID-EyeUpturn "
    "ID-LidCrease ID-LidHood ID-MouthWidth ID-MouthHeight ID-LipUpper ID-LipLower ID-LipThin ID-CornerUp ID-CornerDown "
    "ID-Philtrum ID-LashShort ID-LashDefault ID-LashLong"
).split()

# Per-side keys exist as _L/_R pairs on the body; the contract lists the base name.
PERFORMANCE_KEYS = (
    "PF-Blink_L PF-Blink_R PF-EyeWide_L PF-EyeWide_R PF-Squint_L PF-Squint_R PF-LidUpperDown_L PF-LidUpperDown_R "
    "PF-LidLowerUp_L PF-LidLowerUp_R PF-Squeeze_L PF-Squeeze_R PF-JawOpen "
    "PF-VisMBP PF-VisSmall PF-VisMid PF-VisAA PF-VisEE PF-VisIH PF-VisOH PF-VisOO PF-VisFV PF-VisL PF-VisTH PF-VisSZ "
    "PF-VisWide PF-SmileClosed PF-SmileOpenJaw PF-Smirk_L PF-Smirk_R PF-Frown PF-FrownOpen PF-Pout PF-Press PF-LipBite "
    "PF-Grimace PF-Snarl PF-Disgust PF-Surprise PF-Cry PF-MouthSide_L PF-MouthSide_R"
).split()

# The child omits these (build prompt CHILD SPECIES).
CHILD_FORBIDDEN = "ID-Chest ID-WideHips ID-Glute ID-MuscleChest ID-MuscleAbs ID-MuscleArms ID-MuscleLegs".split()

SOCKETS_HUMAN = (
    "SOC-HeadTop SOC-HairScalp SOC-HairFront SOC-HairSide_L SOC-HairSide_R SOC-HairBack SOC-HairExtra SOC-Ear_L SOC-Ear_R "
    "SOC-Eyewear SOC-Moustache SOC-Beard SOC-Sideburn_L SOC-Sideburn_R SOC-Neck SOC-Chest SOC-Back SOC-Shoulder_L "
    "SOC-Shoulder_R SOC-UpperArm_L SOC-UpperArm_R SOC-ForeArm_L SOC-ForeArm_R SOC-Hand_L SOC-Hand_R SOC-Waist SOC-Hip_L "
    "SOC-Hip_R SOC-Thigh_L SOC-Thigh_R SOC-Shin_L SOC-Shin_R SOC-Foot_L SOC-Foot_R SOC-Cape SOC-Weapon_L SOC-Weapon_R "
    "SOC-OrganicForeArm_L"
).split()

SOCKETS_BY_KIND: Dict[str, Tuple[str, ...]] = {
    "adult": tuple(SOCKETS_HUMAN),
    # Child: same human socket names; facial hair sockets are tolerated but not required.
    "child": tuple(s for s in SOCKETS_HUMAN if s not in ("SOC-Moustache", "SOC-Beard", "SOC-Sideburn_L", "SOC-Sideburn_R")),
    "robot": tuple("SOC-HeadTop SOC-Neck SOC-Chest SOC-Back SOC-Shoulder_L SOC-Shoulder_R SOC-Hand_L SOC-Hand_R "
                   "SOC-Waist SOC-Foot_L SOC-Foot_R SOC-Antenna SOC-Core".split()),
    "dragon": tuple("SOC-Crest SOC-Neck SOC-Back SOC-Wing_L SOC-Wing_R SOC-Tail SOC-Shoulder_L SOC-Shoulder_R".split()),
}

ROBOT_KEYS = "ID-ChassisBulk ID-ChestCore ID-OpticStyle PF-Blink_L PF-Blink_R PF-VisSmall PF-VisMid PF-VisWide PF-JawOpen".split()
DRAGON_KEYS = ("ID-SnoutLong ID-SnoutShort ID-JawWidth ID-HornStyle ID-Crest ID-EarFin ID-ClawLength PF-Blink_L PF-Blink_R "
               "PF-VisMBP PF-VisSmall PF-VisMid PF-VisWide PF-SmileClosed PF-Snarl PF-Surprise PF-JawOpen").split()

REQUIRED_OBJECTS: Dict[str, Tuple[str, ...]] = {
    "adult": ("CHR_Armature", "CHR_Body", "CHR_Eye_L", "CHR_Eye_R", "CHR_Lashes", "CHR_Brows",
              "CHR_TeethUpper", "CHR_TeethLower", "CHR_Tongue"),
    "child": ("CHR_Armature_Child", "CHR_Body_Child"),
    "robot": ("CHR_Armature_Robot", "CHR_Body_Robot"),
    "dragon": ("CHR_Armature_Dragon", "CHR_Body_Dragon"),
}


def required_keys(kind: str):
    if kind in ("adult", "child"):
        # The child prompt only fixes face + performance keys; its body sliders are "child proportions".
        body = () if kind == "child" else ADULT_BODY_KEYS
        return set(body) | set(ADULT_FACE_KEYS) | set(PERFORMANCE_KEYS)
    return set(ROBOT_KEYS if kind == "robot" else DRAGON_KEYS)
