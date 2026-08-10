export const GALACTIC_VERTEX_SHADER = /* glsl */ `
  precision highp float;

  uniform mat3 u_equatorialToThree;
  uniform float u_radius;
  varying vec3 v_equatorialDirection;
  varying vec3 v_localDirection;

  void main() {
    v_equatorialDirection = normalize(position);
    v_localDirection = normalize(u_equatorialToThree * v_equatorialDirection);
    vec3 localPosition = v_localDirection * u_radius;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(localPosition, 1.0);
  }
`;

export const GALACTIC_FRAGMENT_SHADER = /* glsl */ `
  precision highp float;

  uniform sampler2D u_milkyWayTexture;
  uniform sampler2D u_planckDustTexture;
  uniform bool u_milkyWayEnabled;
  uniform bool u_planckDustEnabled;
  uniform float u_milkyWayOpacity;
  uniform float u_dustDensityStrength;
  uniform float u_dustExtinctionStrength;
  uniform float u_skyVisibility;

  varying vec3 v_equatorialDirection;
  varying vec3 v_localDirection;

  const float PI = 3.14159265358979323846;
  const float TAU = 6.28318530717958647692;

  // IAU J2000: ICRS/equatorial -> Galactic. GLSL constructors are column-major.
  const mat3 EQUATORIAL_TO_GALACTIC = mat3(
    -0.0548755604,  0.4941094279, -0.8676661490,
    -0.8734370902, -0.4448296300, -0.1980763734,
    -0.4838350155,  0.7469822445,  0.4559837762
  );

  vec2 milkyWayUv(vec3 equatorial) {
    float ra = atan(equatorial.y, equatorial.x);
    float dec = asin(clamp(equatorial.z, -1.0, 1.0));
    // EXRLoader reverses source scanlines into WebGL texture order: v=0 is
    // celestial south and v=1 celestial north for the decoded NASA texture.
    return vec2(fract(0.5 - ra / TAU), 0.5 + dec / PI);
  }

  vec2 planckUv(vec3 equatorial) {
    vec3 galactic = normalize(EQUATORIAL_TO_GALACTIC * equatorial);
    float longitude = atan(galactic.y, galactic.x);
    float latitude = asin(clamp(galactic.z, -1.0, 1.0));
    return vec2(fract(longitude / TAU), 0.5 - latitude / PI);
  }

  float atmosphericTransmission(vec3 localDirection) {
    float altitudeDeg = degrees(asin(clamp(localDirection.y, -1.0, 1.0)));
    float aboveHorizon = smoothstep(-1.0, 4.0, altitudeDeg);
    float safeAltitude = max(0.0, altitudeDeg);
    float denominator = sin(radians(safeAltitude))
      + 0.50572 * pow(safeAltitude + 6.07995, -1.6364);
    float airmass = denominator > 0.00001 ? min(40.0, 1.0 / denominator) : 40.0;
    return aboveHorizon * exp(-0.12 * max(0.0, airmass - 1.0));
  }

  void main() {
    if (!u_milkyWayEnabled && !u_planckDustEnabled) discard;

    vec3 equatorial = normalize(v_equatorialDirection);
    float dust = u_planckDustEnabled
      ? texture2D(u_planckDustTexture, planckUv(equatorial)).r
      : 0.0;

    vec3 milkyWay = vec3(0.0);
    if (u_milkyWayEnabled) {
      milkyWay = texture2D(u_milkyWayTexture, milkyWayUv(equatorial)).rgb;
      milkyWay *= max(0.0, 1.0 - dust * u_dustExtinctionStrength);
      milkyWay *= u_milkyWayOpacity;
    }

    // La pols és una densitat visual opcional; l'extinció modula només el
    // fons difús i no duplica ni altera el catàleg Gaia.
    vec3 dustEmission = vec3(0.22, 0.095, 0.035)
      * pow(max(dust, 0.0), 1.25)
      * u_dustDensityStrength;

    float visibility = u_skyVisibility * atmosphericTransmission(normalize(v_localDirection));
    vec3 color = (milkyWay + dustEmission) * visibility;
    if (max(max(color.r, color.g), color.b) < 0.000001) discard;

    gl_FragColor = vec4(color, visibility);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;
