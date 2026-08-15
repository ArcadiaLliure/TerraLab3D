export const HORIZON_GLSL_UNIFORMS = /* glsl */ `
  uniform sampler2D u_horizonTexture;
  uniform float u_horizonSampleCount;
  uniform float u_horizonTextureWidth;
  uniform float u_horizonTextureHeight;
  uniform float u_horizonEnabled;
`;

export const HORIZON_GLSL_FUNCTIONS = /* glsl */ `
  float horizonSampleAtIndex(float indexValue) {
    float wrapped = mod(indexValue + u_horizonSampleCount, u_horizonSampleCount);
    float column = mod(wrapped, u_horizonTextureWidth);
    float row = floor(wrapped / u_horizonTextureWidth);
    vec2 uv = vec2(
      (column + 0.5) / u_horizonTextureWidth,
      (row + 0.5) / u_horizonTextureHeight
    );
    return texture2D(u_horizonTexture, uv).r;
  }

  float horizonElevationAtDirection(vec3 localThreeDirection) {
    if (u_horizonEnabled < 0.5 || u_horizonSampleCount < 1.0) return 0.0;
    vec3 direction = normalize(localThreeDirection);
    float azimuthDeg = degrees(atan(direction.x, -direction.z));
    if (azimuthDeg < 0.0) azimuthDeg += 360.0;
    float position = azimuthDeg * u_horizonSampleCount / 360.0;
    float leftIndex = floor(position);
    float fraction = position - leftIndex;
    return mix(
      horizonSampleAtIndex(leftIndex),
      horizonSampleAtIndex(leftIndex + 1.0),
      fraction
    );
  }
`;
