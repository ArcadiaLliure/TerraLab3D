/**
 * Shader estel·lar fotomètric per a Three.js.
 *
 * Vertex shader:
 *   - Aplica la matriu de rotació equatorial→ENU `u_equatorialToENUMatrix` (3x3).
 *   - Transforma posicions equatorials XYZ a posició ENU recentrada.
 *   - Calcula la mida de punt PSF en funció de la magnitud i el DPR.
 *
 * Fragment shader:
 *   - Utilitza `gl_PointCoord` per produir un disc PSF **circular** perfecte.
 *   - `discard` fora de la meitat del diàmetre → MAI quadrats visibles.
 *   - Antialiasing suau a la vora.
 *   - Spikes de difracció procedurals per a estrelles molts brillants (mag < 1.5: Sirius, Betelgeuse, Rigel...).
 */

export const STAR_VERTEX_SHADER = /* glsl */ `
  attribute float magnitude;
  attribute vec3 color;
  attribute float catalogIndex;

  uniform mat3 u_equatorialToENUMatrix;
  uniform float u_magnitudeLimit; // Límit dur absolut del catàleg
  uniform float u_pointScale;
  uniform float u_devicePixelRatio;
  uniform float u_radius;

  uniform float u_cameraHeight;

  // Uniforms de Visibilitat (Pas 7)
  uniform float u_zenithMagnitudeLimit;
  uniform float u_extinctionCoefficient;
  uniform float u_twilightSuppression;
  uniform float u_fadeWidthMag;

  varying vec3 vColor;
  varying float vMagnitude;
  varying float vAlpha;

  void main() {
    vColor = color;
    vMagnitude = magnitude;

    // Rotació equatorial → ENU/Three.js
    vec3 posWorld = u_equatorialToENUMatrix * position;

    // ── Lògica d'Extinció i Visibilitat amb Depressió de l'Horitzó ──
    float h = degrees(asin(clamp(posWorld.y / length(posWorld), -1.0, 1.0)));
    
    // Calcular depressió de l'horitzó per esfèricitat de la Terra
    float R_E = 6371000.0;
    float dip_angle = degrees(acos(R_E / (R_E + max(0.0, u_cameraHeight))));
    
    // Altitud efectiva centrada a l'horitzó físic percebut
    float h_calc = abs(h + dip_angle);
    
    // Kasten-Young Airmass
    float denominator = sin(radians(h_calc)) + 0.50572 * pow(h_calc + 6.07995, -1.6364);
    float base_airmass = denominator < 1e-5 ? 40.0 : 1.0 / denominator;
    
    // Atenuar extinció segons l'escala atmosfèrica
    float atmosphereScale = exp(-max(0.0, u_cameraHeight) / 8500.0);
    float airmass = 1.0 + (base_airmass - 1.0) * atmosphereScale;
    
    // Magnitud límit efectiva a aquesta altitud
    float effectiveLimit = u_zenithMagnitudeLimit - u_extinctionCoefficient * (airmass - 1.0) - u_twilightSuppression;
    
    // Fade suau (alpha=1 si mag < límit-fade, alpha=0 si mag > límit)
    // smoothstep requereix edge0 < edge1 en GLSL
    float edge0 = effectiveLimit - u_fadeWidthMag;
    float edge1 = effectiveLimit;
    vAlpha = 1.0 - smoothstep(edge0, edge1, magnitude);

    // Ocultació dura per optimització (invisible o fora de catàleg)
    if (magnitude > u_magnitudeLimit || vAlpha < 0.02) {
      gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
      gl_PointSize = 0.0;
      return;
    }

    // Col·locar a l'esfera celeste a distància u_radius
    vec4 mvPosition = modelViewMatrix * vec4(posWorld * u_radius, 1.0);
    gl_Position = projectionMatrix * mvPosition;

    // Càlcul de mida de punt PSF (brillants = més grans)
    // Sirius (mag -1.46) → ~20px, mag 6.0 → ~2.5px
    float baseSize = max(1.8, (7.0 - magnitude) * 1.8 * u_pointScale);
    if (magnitude < 1.0) {
      baseSize += (1.0 - magnitude) * 4.0; // Extra boost per super-brillants
    }

    gl_PointSize = clamp(baseSize * u_devicePixelRatio, 1.0, 64.0);
  }
`;

export const STAR_FRAGMENT_SHADER = /* glsl */ `
  varying vec3 vColor;
  varying float vMagnitude;
  varying float vAlpha;

  void main() {
    // gl_PointCoord està en [0, 1] x [0, 1]
    vec2 coord = gl_PointCoord - vec2(0.5);
    float distSq = dot(coord, coord);

    // Discard fora del diàmetre → MAI quadrats
    if (distSq > 0.25) {
      discard;
    }

    float dist = sqrt(distSq) * 2.0; // [0, 1]

    // Perfil PSF circular amb antialiasing a les vores
    float coreAlpha = smoothstep(1.0, 0.15, dist);

    // Spikes de difracció procedurals per a estrelles molt brillants (mag < 1.5)
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

    // Intensitat del nucli de l'estrella
    if (dist < 0.3) {
      finalColor = mix(vColor, vec3(1.0), (0.3 - dist) / 0.3 * 0.6);
    }

    gl_FragColor = vec4(finalColor, finalAlpha * vAlpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;
