# Third-party models used in the library

## Head base (q31)

The v2 head's face front and ears come from a reworked dataset head:

- **"Autumn Girl" by Aryzus** (Sketchfab), licensed **CC Attribution 4.0** (CC BY 4.0).
  TexVerse uid `d60fb4427e6e4858bc82c4175b0fdbb5`.
- Changes: re-proportioned to the median of five verified dataset heads, eye sockets filled, smoothed and resampled
  into a signed-distance grid (`blender/head_v3/base_head.py` makes `blender/head_v3/base_grid_d60.npz`).
  `blender/head_v2/sdf_head.py` blends that grid with our own measured skull, back of the head, jaw sides and neck,
  narrows the lower face and closes the eye sockets. Eyes, brows, nose, mouth, hair and shading are our own pieces.

This credit must ship with any exported head, pack or app build that contains the head.
