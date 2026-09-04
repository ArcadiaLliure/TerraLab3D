import {
  HORIZON_GLSL_FUNCTIONS,
  HORIZON_GLSL_UNIFORMS,
} from "./horizonOcclusionShader";

/** Photometric star shader with the shared terrain-horizon lookup. */
export const STAR_VERTEX_SHADER = /* glsl */ `
  attribute float magnitude;
  attribute vec3 color;

  uniform mat3 u_equatorialToENUMatrix;
  uniform mat3 u_equatorialToViewMatrix;
  uniform vec3 u_equatorialViewAnchor;
  uniform float u_magnitudeLimit;
  uniform float u_pointScale;
  uniform float u_devicePixelRatio;
  uniform float u_radius;
  uniform float u_zenithMagnitudeLimit;
  uniform float u_extinctionCoefficient;
  uniform float u_twilightSuppression;
  uniform float u_fadeWidthMag;
  ${HORIZON_GLSL_UNIFORMS}

  varying vec3 vColor;
  varying float vMagnitude;
  varying float vAlpha;
  ${HORIZON_GLSL_FUNCTIONS}

  void main() {
    vColor = color;
    vMagnitude = magnitude;
    vec3 posWorld = u_equatorialToENUMatrix * position;
    float altitudeDeg = degrees(asin(clamp(posWorld.y / length(posWorld), -1.0, 1.0)));

    if (altitudeDeg < horizonElevationAtDirection(posWorld)) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      vAlpha = 0.0;
      return;
    }

    // Atmospheric extinction remains independent of terrain occlusion.
    float hAtmosphere = max(-5.0, altitudeDeg);
    float denominator = sin(radians(hAtmosphere))
      + 0.50572 * pow(hAtmosphere + 6.07995, -1.6364);
    float airmass = denominator < 1e-5 ? 40.0 : 1.0 / denominator;
    float effectiveLimit = u_zenithMagnitudeLimit
      - u_extinctionCoefficient * (airmass - 1.0)
      - u_twilightSuppression;
    vAlpha = 1.0 - smoothstep(
      effectiveLimit - u_fadeWidthMag,
      effectiveLimit,
      magnitude
    );

    if (magnitude > u_magnitudeLimit || vAlpha < 0.02) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      return;
    }

    // Camera-relative angular floating origin. At telescope FOVs, multiplying
    // the absolute direction by two independent float32 matrices makes the
    // least-significant bits visible as pixel-scale wobble. The view-centre
    // anchor makes those operations act on small angular deltas instead.
    vec3 viewDirection = vec3(0.0, 0.0, -1.0)
      + u_equatorialToViewMatrix * (position - u_equatorialViewAnchor);
    vec4 mvPosition = vec4(viewDirection * u_radius, 1.0);
    gl_Position = projectionMatrix * mvPosition;
    float baseSize = max(1.8, (7.0 - magnitude) * 1.8);
    if (magnitude < 1.0) baseSize += (1.0 - magnitude) * 4.0;
    gl_PointSize = clamp(baseSize * u_pointScale * u_devicePixelRatio, 1.0, 64.0);
  }
`;

export const STAR_FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vMagnitude;
  varying float vAlpha;

  void main() {
    vec2 coord = gl_PointCoord - vec2(0.5);
    float distSq = dot(coord, coord);
    if (distSq > 0.25) discard;
    float dist = sqrt(distSq) * 2.0;
    float coreAlpha = smoothstep(1.0, 0.15, dist);
    float spikeAlpha = 0.0;
    if (vMagnitude < 1.5) {
      float spikeWidth = 0.04;
      float dx = abs(coord.x);
      float dy = abs(coord.y);
      float spikeIntensity = (1.5 - vMagnitude) * 0.7;
      float spikeX = smoothstep(spikeWidth, 0.0, dy) * smoothstep(0.48, 0.0, dx);
      float spikeY = smoothstep(spikeWidth, 0.0, dx) * smoothstep(0.48, 0.0, dy);
      spikeAlpha = (spikeX + spikeY) * spikeIntensity;
    }
    float finalAlpha = clamp(coreAlpha + spikeAlpha, 0.0, 1.0);
    vec3 finalColor = vColor;
    if (dist < 0.3) {
      finalColor = mix(vColor, vec3(1.0), (0.3 - dist) / 0.3 * 0.6);
    }
    gl_FragColor = vec4(finalColor, finalAlpha * vAlpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;
