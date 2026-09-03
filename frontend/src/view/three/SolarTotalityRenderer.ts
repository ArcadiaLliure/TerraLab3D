import * as THREE from "three";

import type { AstronomicalEventSnapshot } from "../../contracts/astronomical_event_contracts";
import type { SolarSystemBodyState } from "../../contracts/solar_system_contracts";
import { threeFromEnu } from "./celestialCoordinates";

const MAX_BEADS = 96;

interface CoronaUniforms extends Record<string, THREE.IUniform<unknown>> {
  readonly uVisibility: THREE.IUniform<number>;
  readonly uSolarNorth: THREE.IUniform<number>;
  readonly uChromosphere: THREE.IUniform<number>;
  readonly uProminences: THREE.IUniform<number>;
  readonly uContactIsolation: THREE.IUniform<number>;
  readonly uContactAngle: THREE.IUniform<number>;
  readonly uContactHalfWidth: THREE.IUniform<number>;
}

/**
 * Persistent GPU presentation of corona, chromosphere and terrain-derived
 * photospheric openings.  It never creates a replacement solar disc.
 */
export class SolarTotalityRenderer {
  readonly root = new THREE.Group();
  private readonly coronaGeometry = new THREE.PlaneGeometry(1, 1, 1, 1);
  private readonly coronaUniforms: CoronaUniforms = {
    uVisibility: { value: 0 },
    uSolarNorth: { value: 0 },
    uChromosphere: { value: 0 },
    uProminences: { value: 0 },
    uContactIsolation: { value: 0 },
    uContactAngle: { value: 0 },
    uContactHalfWidth: { value: Math.PI },
  };
  private readonly coronaMaterial = new THREE.ShaderMaterial({
    uniforms: this.coronaUniforms,
    vertexShader: CORONA_VERTEX_SHADER,
    fragmentShader: CORONA_FRAGMENT_SHADER,
    transparent: true,
    depthTest: false,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    side: THREE.DoubleSide,
  });
  private readonly corona = new THREE.Mesh(this.coronaGeometry, this.coronaMaterial);
  private readonly beadPositions = new Float32Array(MAX_BEADS * 3);
  private readonly beadBrightness = new Float32Array(MAX_BEADS);
  private readonly beadWidths = new Float32Array(MAX_BEADS);
  private readonly beadGeometry = new THREE.BufferGeometry();
  private readonly beadMaterial = new THREE.ShaderMaterial({
    uniforms: {
      uDiamondPhase: { value: 0 },
    },
    vertexShader: BEAD_VERTEX_SHADER,
    fragmentShader: BEAD_FRAGMENT_SHADER,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthTest: false,
    depthWrite: false,
  });
  private readonly beads = new THREE.Points(this.beadGeometry, this.beadMaterial);
  private event: AstronomicalEventSnapshot | null = null;
  private sun: SolarSystemBodyState | null = null;
  private moon: SolarSystemBodyState | null = null;
  private presentationRadius = 900_000;
  private disposed = false;
  private previewActive = false;
  readonly geometryBuildCount = 2;
  readonly materialBuildCount = 2;

  constructor(parent: THREE.Object3D) {
    this.root.name = "solarTotalityAppearance";
    this.corona.name = "solarCorona";
    this.corona.renderOrder = -240;
    this.corona.frustumCulled = false;
    this.beads.name = "terrainCorrectedBailyBeads";
    this.beads.renderOrder = 20;
    this.beads.frustumCulled = false;
    this.beadGeometry.setAttribute("position", new THREE.BufferAttribute(this.beadPositions, 3));
    this.beadGeometry.setAttribute("brightness", new THREE.BufferAttribute(this.beadBrightness, 1));
    this.beadGeometry.setAttribute("beadWidth", new THREE.BufferAttribute(this.beadWidths, 1));
    this.beadGeometry.setDrawRange(0, 0);
    this.root.add(this.corona, this.beads);
    parent.add(this.root);
  }

  updateEvent(snapshot: AstronomicalEventSnapshot): void {
    this.event = snapshot;
    this.apply();
  }

  updateSun(state: SolarSystemBodyState, presentationRadius: number): void {
    this.sun = state;
    this.presentationRadius = presentationRadius;
    this.apply();
  }

  updateMoon(state: SolarSystemBodyState): void {
    this.moon = state;
    this.apply();
  }

  setPreviewActive(active: boolean): void {
    this.previewActive = active;
    if (active) {
      this.root.visible = false;
    } else {
      this.apply();
    }
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.root.removeFromParent();
    this.coronaGeometry.dispose();
    this.coronaMaterial.dispose();
    this.beadGeometry.dispose();
    this.beadMaterial.dispose();
  }

  private apply(): void {
    if (this.previewActive) {
      this.root.visible = false;
      return;
    }
    if (this.event === null || this.sun === null || this.moon === null) {
      this.root.visible = false;
      return;
    }
    const direction = threeFromEnu(this.sun.directionENU).normalize();
    const moonDirection = threeFromEnu(this.moon.directionENU).normalize();
    const towardSun = direction.clone()
      .addScaledVector(moonDirection, -direction.dot(moonDirection));
    if (towardSun.lengthSq() <= 1e-16) {
      const reference = Math.abs(direction.y) < 0.9
        ? new THREE.Vector3(0, 1, 0)
        : new THREE.Vector3(1, 0, 0);
      towardSun.copy(reference).addScaledVector(direction, -reference.dot(direction));
    }
    towardSun.normalize();
    towardSun.addScaledVector(direction, -towardSun.dot(direction)).normalize();
    const increasingPositionAngle = towardSun.clone().cross(direction).normalize();
    this.root.quaternion.setFromRotationMatrix(
      new THREE.Matrix4().makeBasis(increasingPositionAngle, towardSun, direction),
    );
    const solarRadius = this.presentationRadius
      * Math.sin(THREE.MathUtils.degToRad(this.sun.angularRadiusDeg));
    const lunarRadius = this.presentationRadius
      * Math.sin(THREE.MathUtils.degToRad(this.moon.angularRadiusDeg));
    this.root.position.copy(direction).multiplyScalar(this.presentationRadius);
    this.corona.scale.setScalar(solarRadius * 16);
    this.coronaUniforms.uVisibility.value = this.event.totalityAppearance.corona.visibility;
    const sunAroundMoonPositionAngle = (this.event.solar.moonPositionAngleDeg + 180) % 360;
    this.coronaUniforms.uSolarNorth.value = THREE.MathUtils.degToRad(
      this.event.totalityAppearance.corona.solarNorthPositionAngleDeg
        - sunAroundMoonPositionAngle,
    );
    this.coronaUniforms.uChromosphere.value = this.event.totalityAppearance.chromosphereVisibility;
    this.coronaUniforms.uProminences.value = this.event.totalityAppearance.prominenceQuality === "unavailable"
      ? 0
      : this.event.totalityAppearance.chromosphereVisibility;
    const source = this.event.totalityAppearance.beads.slice(0, MAX_BEADS);
    const diamondPhase = this.event.totalityAppearance.phase === "diamond_ingress"
      || this.event.totalityAppearance.phase === "diamond_egress";
    const contactPhase = diamondPhase
      || this.event.totalityAppearance.phase === "baily_ingress"
      || this.event.totalityAppearance.phase === "baily_egress";
    this.beadMaterial.uniforms.uDiamondPhase!.value = diamondPhase ? 1 : 0;
    const dominantBead = source.reduce<(typeof source)[number] | null>(
      (dominant, bead) => dominant === null
        || bead.exposedPhotosphereArea > dominant.exposedPhotosphereArea
        ? bead
        : dominant,
      null,
    );
    const contactAngle = dominantBead === null
      ? 0
      : THREE.MathUtils.degToRad(
        dominantBead.lunarPositionAngle - sunAroundMoonPositionAngle,
      );
    const contactHalfWidthDeg = dominantBead === null
      ? 180
      : THREE.MathUtils.clamp(
        Math.max(
          dominantBead.angularWidth * 0.65,
          ...source.map((bead) => (
            circularDistanceDeg(bead.lunarPositionAngle, dominantBead.lunarPositionAngle)
            + bead.angularWidth * 0.5
          )),
        ) + (diamondPhase ? 3 : 7),
        diamondPhase ? 9 : 14,
        diamondPhase ? 22 : 52,
      );
    this.coronaUniforms.uContactIsolation.value = contactPhase ? 1 : 0;
    this.coronaUniforms.uContactAngle.value = contactAngle;
    this.coronaUniforms.uContactHalfWidth.value = THREE.MathUtils.degToRad(contactHalfWidthDeg);
    for (let index = 0; index < source.length; index++) {
      const bead = source[index]!;
      const angle = THREE.MathUtils.degToRad(
        bead.lunarPositionAngle - sunAroundMoonPositionAngle,
      );
      const radial = lunarRadius * 1.001;
      this.beadPositions[index * 3] = Math.sin(angle) * radial;
      this.beadPositions[index * 3 + 1] = Math.cos(angle) * radial;
      this.beadPositions[index * 3 + 2] = 0;
      this.beadBrightness[index] = bead.brightness;
      this.beadWidths[index] = bead.angularWidth;
    }
    (this.beadGeometry.getAttribute("position") as THREE.BufferAttribute).needsUpdate = true;
    (this.beadGeometry.getAttribute("brightness") as THREE.BufferAttribute).needsUpdate = true;
    (this.beadGeometry.getAttribute("beadWidth") as THREE.BufferAttribute).needsUpdate = true;
    this.beadGeometry.setDrawRange(0, source.length);
    this.root.visible = source.length > 0
      || this.event.totalityAppearance.corona.visibility > 0.002
      || this.event.totalityAppearance.chromosphereVisibility > 0.002;
    this.root.userData.quality = {
      limb: this.event.limbQuality,
      corona: this.event.coronaQuality,
      appearance: this.event.appearanceQuality,
    };
  }
}

const CORONA_VERTEX_SHADER = /* glsl */ `
  varying vec2 vUv;
  void main() {
    vUv = uv;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const CORONA_FRAGMENT_SHADER = /* glsl */ `
  uniform float uVisibility;
  uniform float uSolarNorth;
  uniform float uChromosphere;
  uniform float uProminences;
  uniform float uContactIsolation;
  uniform float uContactAngle;
  uniform float uContactHalfWidth;
  varying vec2 vUv;

  float filament(float angle, float frequency, float sharpness) {
    return pow(max(0.0, cos(angle * frequency)), sharpness);
  }

  float angularDistance(float first, float second) {
    return abs(atan(sin(first - second), cos(first - second)));
  }

  void main() {
    vec2 p = (vUv - 0.5) * 16.0;
    float radius = length(p);
    float sceneAngle = atan(p.x, p.y);
    float angle = sceneAngle - uSolarNorth;
    if (radius < 0.992 || radius > 7.8) discard;

    float polar = pow(abs(cos(angle)), 9.0);
    float equatorial = pow(abs(sin(angle)), 5.0);
    float midLatitude = pow(max(0.0, cos(4.0 * angle - 0.7)), 5.0);
    float finePlumes = polar * filament(angle, 44.0, 12.0);
    float helmetStreamers = (equatorial + 0.45 * midLatitude)
      * exp(-pow((radius - 2.4) / 2.1, 2.0));
    float inner = exp(-max(0.0, radius - 1.012) * 2.8)
      * smoothstep(0.997, 1.018, radius);
    float outer = exp(-max(0.0, radius - 1.0) * 0.62)
      * (0.025 + 0.62 * helmetStreamers + 0.54 * finePlumes);
    float striation = 0.72 + 0.28 * filament(angle + radius * 0.013, 73.0, 8.0);
    float innerStructure = 0.08 + 0.18 * striation
      + 0.14 * polar + 0.10 * equatorial + 0.08 * midLatitude;
    float coronaAlpha = uVisibility
      * (inner * innerStructure + outer * striation * 0.31);

    float contactDistance = angularDistance(sceneAngle, uContactAngle);
    float contactArc = 1.0 - smoothstep(
      uContactHalfWidth * 0.72,
      uContactHalfWidth,
      contactDistance
    );
    float phaseArc = mix(1.0, contactArc, uContactIsolation);
    float chromosphereRing = smoothstep(0.996, 1.002, radius)
      * (1.0 - smoothstep(1.008, 1.018, radius))
      * phaseArc;
    float prominenceBand = smoothstep(0.998, 1.006, radius)
      * (1.0 - smoothstep(1.018, 1.052, radius));
    float prominencePattern = pow(max(0.0, sin(angle * 5.0 + 1.4)), 18.0);
    float prominence = uProminences * prominenceBand * prominencePattern
      * phaseArc * 0.34;
    vec3 coronaColor = mix(vec3(0.55, 0.68, 0.9), vec3(0.98, 0.99, 1.0), inner);
    vec3 chromosphereColor = vec3(1.0, 0.16, 0.12)
      * (uChromosphere * chromosphereRing * 0.72 + prominence * 1.25);
    float alpha = coronaAlpha + uChromosphere * chromosphereRing * 0.72 + prominence;
    if (alpha < 0.002) discard;
    gl_FragColor = vec4(coronaColor * coronaAlpha + chromosphereColor, alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;

function circularDistanceDeg(first: number, second: number): number {
  const delta = Math.abs((first - second) % 360);
  return Math.min(delta, 360 - delta);
}

const BEAD_VERTEX_SHADER = /* glsl */ `
  attribute float brightness;
  attribute float beadWidth;
  uniform float uDiamondPhase;
  varying float vBrightness;
  void main() {
    vBrightness = brightness;
    float photosphereSize = 4.0 + sqrt(max(beadWidth, 0.0)) * 2.4;
    gl_PointSize = clamp(photosphereSize * mix(1.0, 1.65, uDiamondPhase), 5.0, 32.0);
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;

const BEAD_FRAGMENT_SHADER = /* glsl */ `
  varying float vBrightness;
  void main() {
    vec2 point = gl_PointCoord - 0.5;
    float radial = length(point) * 2.0;
    float core = 1.0 - smoothstep(0.20, 0.88, radial);
    float diffraction = exp(-radial * 2.8) * 0.32;
    float alpha = (core + diffraction) * mix(0.7, 1.0, vBrightness);
    if (alpha < 0.002) discard;
    float photosphereLuminance = 2.2 + 4.5 * vBrightness;
    gl_FragColor = vec4(vec3(1.0, 0.93, 0.70) * photosphereLuminance, alpha);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>
  }
`;
