import * as THREE from "three";
import { LineMaterial } from "three/addons/lines/LineMaterial.js";

/**
 * Llenguatge visual compartit pels overlays lineals.
 *
 * Renderitzat en un sol pas mitjançant GlowLineMaterial:
 * - Nucli d'alta intensitat amb transició subpíxel suau.
 * - Halo continu amb caiguda exponencial orgànica (Gaussiana) sense bandes dures.
 * - Antialiasing analític per shader als extrems (zero efecte escaleta).
 */
export interface OverlayLineProfile {
  readonly color: THREE.ColorRepresentation;
  readonly coreColor?: THREE.ColorRepresentation;
  readonly linewidthPx: number;
  readonly coreWidthPx: number;
  readonly coreOpacity: number;
  readonly haloOpacity: number;
  readonly depthTest: boolean;
  readonly dashed?: boolean;
  readonly dashSize?: number;
  readonly gapSize?: number;
  readonly dashScale?: number;
}

export interface OverlayLineMaterials {
  readonly material: GlowLineMaterial;
  readonly core: GlowLineMaterial;
  readonly halo: GlowLineMaterial;
  readonly profile: OverlayLineProfile;
}

export const OVERLAY_LINE_PROFILES = {
  constellationCatalog: {
    color: 0xffffff, // Blanc viu amb resplendor subtil
    coreColor: 0xffffff,
    linewidthPx: 6.5,
    coreWidthPx: 1.2,
    coreOpacity: 0.90,
    haloOpacity: 0.35,
    depthTest: true,
  },
  constellationSelected: {
    color: 0xffffff,
    coreColor: 0xffffff,
    linewidthPx: 8.5,
    coreWidthPx: 1.6,
    coreOpacity: 1.0,
    haloOpacity: 0.55,
    depthTest: true,
  },
  constellationUser: {
    color: 0x6ee7a8, // Verd maragda suau
    coreColor: 0xffffff,
    linewidthPx: 7.5,
    coreWidthPx: 1.35,
    coreOpacity: 0.95,
    haloOpacity: 0.45,
    depthTest: true,
  },
  measurementNormal: {
    color: 0xffffff,
    coreColor: 0xffffff,
    linewidthPx: 7.0,
    coreWidthPx: 1.4,
    coreOpacity: 0.95,
    haloOpacity: 0.40,
    depthTest: false,
  },
  measurementHover: {
    color: 0xffffff,
    coreColor: 0xffffff,
    linewidthPx: 8.5,
    coreWidthPx: 1.7,
    coreOpacity: 1.0,
    haloOpacity: 0.55,
    depthTest: false,
  },
  measurementSelected: {
    color: 0xffd24a, // Or càlid vibrant
    coreColor: 0xffffff,
    linewidthPx: 9.0,
    coreWidthPx: 1.8,
    coreOpacity: 1.0,
    haloOpacity: 0.65,
    depthTest: false,
  },
  trajectoryPrimary: {
    color: 0x38bdf8, // Cian brillant vibrant
    coreColor: 0xffffff,
    linewidthPx: 8.5,
    coreWidthPx: 1.6,
    coreOpacity: 1.0,
    haloOpacity: 0.55,
    depthTest: true,
  },
  trajectorySecondary: {
    color: 0xc084fc,
    coreColor: 0xffffff,
    linewidthPx: 6.5,
    coreWidthPx: 1.3,
    coreOpacity: 0.95,
    haloOpacity: 0.40,
    depthTest: false,
    dashed: true,
    dashSize: 0.40,
    gapSize: 0.25,
    dashScale: 1,
  },
} as const satisfies Record<string, OverlayLineProfile>;

const GLOW_LINE_FRAGMENT_SHADER = /* glsl */ `
  uniform vec3 diffuse;
  uniform vec3 coreColor;
  uniform float opacity;
  uniform float linewidth;
  uniform float coreWidth;
  uniform float coreOpacity;
  uniform float haloOpacity;
  uniform float intensity;

  #ifdef USE_DASH
    uniform float dashOffset;
    uniform float dashSize;
    uniform float gapSize;
  #endif

  varying float vLineDistance;
  varying vec2 vUv;

  #include <common>
  #include <color_pars_fragment>
  #include <fog_pars_fragment>
  #include <logdepthbuf_pars_fragment>
  #include <clipping_planes_pars_fragment>

  void main() {
    #include <clipping_planes_fragment>

    #ifdef USE_DASH
      if ( abs( vUv.y ) > 1.0 ) discard;
      if ( mod( vLineDistance + dashOffset, dashSize + gapSize ) > dashSize ) discard;
    #endif

    float len;
    if ( abs( vUv.y ) > 1.0 ) {
      float a = vUv.x;
      float b = ( vUv.y > 0.0 ) ? vUv.y - 1.0 : vUv.y + 1.0;
      len = sqrt( a * a + b * b );
    } else {
      len = abs( vUv.x );
    }

    // Radi total de la línia en píxels de pantalla
    float totalRadiusPx = max( 0.5, linewidth * 0.5 );
    float distPx = len * totalRadiusPx;

    // Antialiasing analític a la vora exterior
    float edgeAntialias = 1.0 - smoothstep( totalRadiusPx - 1.0, totalRadiusPx, distPx );
    if ( distPx > totalRadiusPx ) discard;

    // Semi-amplada del nucli blanc en píxels
    float halfCorePx = max( 0.2, coreWidth * 0.5 );

    // Factor de nucli: 1.0 al centre, caiguda suau subpíxel
    float coreT = 1.0 - smoothstep( halfCorePx - 0.6, halfCorePx + 0.6, distPx );

    // Factor de halo: caiguda exponencial suau tipus Gaussiana cap a les vores
    float haloT = clamp( ( distPx - halfCorePx ) / max( 0.1, totalRadiusPx - halfCorePx ), 0.0, 1.0 );
    float haloFalloff = exp( - 2.8 * haloT * haloT ) * ( 1.0 - haloT );

    // Alfa combinat amb opacitat i intensitat transitòria
    float effectiveIntensity = max( 0.0, intensity );
    float combinedAlpha = ( coreT * coreOpacity + ( 1.0 - coreT ) * haloFalloff * haloOpacity ) * opacity * edgeAntialias * effectiveIntensity;

    // Color: nucli blanc brillant transicionant cap al color d'halo vibrant
    vec3 col = mix( diffuse, coreColor, coreT * 0.90 );

    #include <logdepthbuf_fragment>
    #include <color_fragment>

    gl_FragColor = vec4( col, clamp( combinedAlpha, 0.0, 1.0 ) );

    #include <tonemapping_fragment>
    #include <colorspace_fragment>
    #include <fog_fragment>
    #include <premultiplied_alpha_fragment>
  }
`;

/** Material especialitzat per a overlays lineals amb nucli brillant i halo continu. */
export class GlowLineMaterial extends LineMaterial {
  constructor(parameters: {
    color?: THREE.ColorRepresentation;
    coreColor?: THREE.ColorRepresentation;
    linewidth?: number;
    coreWidth?: number;
    coreOpacity?: number;
    haloOpacity?: number;
    opacity?: number;
    depthTest?: boolean;
    dashed?: boolean;
    dashScale?: number;
    dashSize?: number;
    gapSize?: number;
  } = {}) {
    super({
      color: parameters.color ?? 0xffffff,
      linewidth: parameters.linewidth ?? 7.0,
      opacity: parameters.opacity ?? 1.0,
      transparent: true,
      depthWrite: false,
      depthTest: parameters.depthTest ?? true,
      worldUnits: false,
      dashed: parameters.dashed ?? false,
      dashScale: parameters.dashScale ?? 1,
      dashSize: parameters.dashSize ?? 3,
      gapSize: parameters.gapSize ?? 2,
    });

    this.fragmentShader = GLOW_LINE_FRAGMENT_SHADER;
    this.uniforms.coreColor = { value: new THREE.Color(parameters.coreColor ?? 0xffffff) };
    this.uniforms.coreWidth = { value: parameters.coreWidth ?? 1.4 };
    this.uniforms.coreOpacity = { value: parameters.coreOpacity ?? 0.95 };
    this.uniforms.haloOpacity = { value: parameters.haloOpacity ?? 0.45 };
    this.uniforms.intensity = { value: 1.0 };
    this.blending = THREE.NormalBlending;
    this.toneMapped = false;
  }

  get coreColor(): THREE.Color {
    return this.uniforms.coreColor?.value ?? new THREE.Color(0xffffff);
  }

  set coreColor(value: THREE.ColorRepresentation) {
    if (this.uniforms.coreColor) this.uniforms.coreColor.value.set(value);
  }

  get coreWidth(): number {
    return this.uniforms.coreWidth?.value ?? 1.4;
  }

  set coreWidth(value: number) {
    if (this.uniforms.coreWidth) this.uniforms.coreWidth.value = value;
  }

  get coreOpacity(): number {
    return this.uniforms.coreOpacity?.value ?? 0.95;
  }

  set coreOpacity(value: number) {
    if (this.uniforms.coreOpacity) this.uniforms.coreOpacity.value = value;
  }

  get haloOpacity(): number {
    return this.uniforms.haloOpacity?.value ?? 0.45;
  }

  set haloOpacity(value: number) {
    if (this.uniforms.haloOpacity) this.uniforms.haloOpacity.value = value;
  }

  get intensity(): number {
    return this.uniforms.intensity?.value ?? 1.0;
  }

  set intensity(value: number) {
    if (this.uniforms.intensity) this.uniforms.intensity.value = value;
  }
}

export function withOverlayColor(
  base: OverlayLineProfile,
  color: THREE.ColorRepresentation,
  opacity = base.coreOpacity,
  depthTest = base.depthTest,
  dashed = base.dashed,
): OverlayLineProfile {
  const opacityRatio = base.coreOpacity > 0 ? opacity / base.coreOpacity : 1;
  return {
    ...base,
    color,
    coreOpacity: opacity,
    haloOpacity: THREE.MathUtils.clamp(base.haloOpacity * opacityRatio, 0, 1),
    depthTest,
    dashed,
  };
}

export function createOverlayLineMaterials(profile: OverlayLineProfile): OverlayLineMaterials {
  const material = new GlowLineMaterial({
    color: profile.color,
    coreColor: profile.coreColor ?? 0xffffff,
    linewidth: profile.linewidthPx,
    coreWidth: profile.coreWidthPx,
    coreOpacity: profile.coreOpacity,
    haloOpacity: profile.haloOpacity,
    depthTest: profile.depthTest,
    dashed: profile.dashed ?? false,
    dashSize: profile.dashSize ?? 0.40,
    gapSize: profile.gapSize ?? 0.25,
    dashScale: profile.dashScale ?? 1,
  });

  return { material, core: material, halo: material, profile };
}

export function setOverlayResolution(
  materials: OverlayLineMaterials | GlowLineMaterial,
  widthPx: number,
  heightPx: number,
): void {
  const mat = "material" in materials ? materials.material : materials;
  mat.resolution.set(Math.max(1, widthPx), Math.max(1, heightPx));
}

/** Intensitat transitòria; no altera el color ni la semàntica del perfil. */
export function setOverlayIntensity(
  materials: OverlayLineMaterials | GlowLineMaterial,
  intensity: number,
): void {
  const mat = "material" in materials ? materials.material : materials;
  const value = Math.max(0, intensity);
  mat.intensity = value;
  mat.opacity = THREE.MathUtils.clamp(value, 0, 1);
}

export function disposeOverlayLineMaterials(materials: OverlayLineMaterials | GlowLineMaterial): void {
  const mat = "material" in materials ? materials.material : materials;
  mat.dispose();
}

/**
 * Equivalent SDF del mateix llenguatge per als contorns instanciats d'NGC.
 * El shader consumidor conserva la paleta i decideix on és el contorn.
 */
export const OVERLAY_LINE_HALO_GLSL = `
  float overlayLineAlpha(float distanceToCore, float coreWidth, float haloWidth,
                         float coreOpacity, float haloOpacity) {
    float core = smoothstep(coreWidth, 0.0, distanceToCore) * coreOpacity;
    float halo = smoothstep(haloWidth, 0.0, distanceToCore) * haloOpacity;
    return clamp(max(core, halo) + min(core, halo) * 0.35, 0.0, 1.0);
  }
`;
