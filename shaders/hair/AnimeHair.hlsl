// AnimeHair.hlsl - line-for-line HLSL port of the app's anime hair shader (src/viewport/hairShader.ts, HAIR_GLSL).
// The app itself runs WebGL, so it uses the GLSL version; this file is the same shading for Unity (URP/HDRP custom
// function or a hand-written pass) or Unreal (Custom node). Keep the two in sync: same names, same maths.
//
// Mesh requirements: uv.x around each strand (0..1), uv.y from root (0) to tip (1); hair modelled around the head
// centre so object-space position O gives the head-space elevation used by the head-space highlight ring.
//
// Parameters (VRoid name where it has one):
//   HairShade, HairShadeMix   own shadow colour and how much of it replaces the toon shadow
//   HairArea, HairHard        VRoid "Shading Area" / "Shading Hardness"
//   HairRootDark              darker roots over the first quarter of the strand
//   RingPos, RingWidth        highlight band position (VRoid "Highlights Position") and width
//   RingStrength, RingColor
//   RingFollow                0 painted at RingPos .. 1 follows the light (Kajiya-Kay style)
//   RingSpace                 0 along each strand .. 1 on the head (one continuous ring across clumps)
//   RingJag, RingTeeth        jagged band edge and teeth count
//   StrandLines, StrandCount  thin darker lines down each strand, strands per clump
//   HairRim, HairRimPow       VRoid "Rim Light Intensity" / "Concentration"

cbuffer AnimeHairParams
{
    float3 HairShade;
    float  HairShadeMix;
    float  HairArea;
    float  HairHard;
    float  HairRootDark;
    float  RingPos;
    float  RingWidth;
    float  RingStrength;
    float3 RingColor;
    float  RingFollow;
    float  RingSpace;
    float  RingJag;
    float  RingTeeth;
    float  StrandLines;
    float  StrandCount;
    float  HairRim;
    float  HairRimPow;
};

float HairHash(float n) { return frac(sin(n * 127.1) * 43758.5453); }

// Strand direction (root to tip) in view space, from screen derivatives of position and uv.
float3 HairTangent(float3 p, float2 uv, float3 N)
{
    float3 dpx = ddx(p), dpy = ddy(p);
    float2 dux = ddx(uv), duy = ddy(uv);
    float det = dux.x * duy.y - dux.y * duy.x;
    float3 T = (dpy * dux.x - dpx * duy.x) * sign(det);
    T -= N * dot(N, T);
    return length(T) > 1e-6 ? normalize(T) : float3(0.0, -1.0, 0.0);
}

// base: strand colour (root..tip); shadowCol / litCol: your toon pass colours for this pixel; ndl: N.L;
// N, V, L: view-space normal, view and light directions; P: view-space position; O: head-space (object) position;
// strength: per-group highlight amount.
float3 AnimeHair(float3 base, float3 shadowCol, float3 litCol, float ndl, float3 N, float3 V, float3 L,
                 float3 P, float3 O, float2 uv, float strength)
{
    float y = saturate(uv.y);
    float root = lerp(1.0 - HairRootDark, 1.0, smoothstep(0.0, 0.25, y));

    float w = lerp(0.3, 0.004, saturate(HairHard));
    float c = -HairArea * 0.5;
    float lit = smoothstep(c - w, c + w, ndl);

    float3 shade = lerp(shadowCol, HairShade * (0.6 + 0.4 * base / max(max(base.r, base.g), max(base.b, 0.001))), HairShadeMix);
    float3 col = lerp(shade, litCol, lit) * root;

    float3 T = HairTangent(P, uv, N);
    float3 H = normalize(L + V);
    float th = dot(T, H);
    float bandPos = lerp(RingPos, saturate(0.5 - th * 0.5), RingFollow);
    float strand = floor(uv.x * max(StrandCount, 1.0));
    float3 od = normalize(O + float3(0.0, 1e-4, 0.0));
    float headT = 0.5 - 0.5 * od.y;
    float az = atan2(od.x, od.z) / 6.2831853 + 0.5;
    float saw = lerp(frac(uv.x * max(RingTeeth, 1.0) * max(StrandCount, 1.0) + HairHash(strand) * 0.7),
                     frac(az * max(RingTeeth, 1.0) * 6.0), step(0.5, RingSpace));
    float jag = (saw - 0.5) * RingJag * RingWidth * 2.0;
    float coord = lerp(y, headT, RingSpace);
    float d = abs(coord - bandPos - jag);
    float ring = 1.0 - smoothstep(RingWidth * 0.6, RingWidth, d);
    ring *= smoothstep(-0.2, 0.4, ndl);
    float3 ringCol = lerp(RingColor, RingColor * (base * 1.5 + 0.12), 0.55);
    col = lerp(col, ringCol, ring * RingStrength * strength);

    float sx = frac(uv.x * max(StrandCount, 1.0) + HairHash(strand + 7.0) * 0.15 + sin(y * 9.0 + strand) * 0.03);
    float line = smoothstep(0.0, 0.05, abs(sx - 0.5) - 0.44);
    line *= smoothstep(0.08, 0.3, y);
    col *= 1.0 - line * StrandLines * 0.45;

    float ndv = max(dot(N, V), 0.0);
    float rim = pow(1.0 - ndv, max(HairRimPow, 0.5)) * HairRim;
    col += rim * lerp(float3(1.0, 1.0, 1.0), base, 0.4) * (0.4 + 0.6 * lit);
    return col;
}
