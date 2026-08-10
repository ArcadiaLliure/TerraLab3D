export const skyVertexShader = `
varying vec3 vViewRay;

void main() {
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    
    // Atès que aquest mesh es fixa a la càmera, position ja és el vector de vista correcte.
    vViewRay = position;
}
`;

export const skyFragmentShader = `
uniform vec3 u_sunDirectionENU;
uniform float u_sunAltitudeDeg;
uniform float u_solarDiscTransmission;
uniform float u_skyEclipseDimmingFactor;
uniform float u_twilightFactor;
uniform float u_turbidity;
uniform float u_bortleClass;
uniform float u_artificialBrightness;
uniform bool u_atmosphereEnabled;
uniform bool u_pureColors;
uniform vec3 u_zenithColorLinear;
uniform vec3 u_horizonColorLinear;
uniform vec3 u_groundColorLinear;

varying vec3 vViewRay;

const float PI = 3.14159265359;

// sRGB (0.55, 0.51, 0.43) decoded once to linear-sRGB.
const vec3 COLOR_LP_GLOW = vec3(0.2633, 0.2232, 0.1559);

void main() {
    vec3 viewDir = normalize(vViewRay);
    
    // Altitud de vista (ENU Y és amunt)
    float viewAlt = asin(clamp(viewDir.y, -1.0, 1.0));
    float viewAltDeg = viewAlt * 180.0 / PI;
    

    
    if (!u_atmosphereEnabled) {
        // Sense atmosfera: fons negre
        gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }
    
    // 1. PALETA COMPARTIDA — resolta una vegada al snapshot del Pas 7.
    vec3 zenithColor = u_zenithColorLinear;
    vec3 horizonColor = u_horizonColorLinear;

    // 2. MIX HORITZÓ - ZENIT (per a la vista actual)
    // El gradient va ràpid a prop de l'horitzó i és estable amunt
    float zenithBlend = clamp(pow(max(0.0, viewDir.y), 0.5), 0.0, 1.0);
    vec3 skyColor = mix(horizonColor, zenithColor, zenithBlend);
    if (viewDir.y < 0.0) {
        skyColor = mix(horizonColor, u_groundColorLinear, clamp(-viewDir.y * 4.0, 0.0, 1.0));
    }
    
    // 3. GLOW SOLAR (Scattering)
    float gamma = acos(clamp(dot(viewDir, u_sunDirectionENU), -1.0, 1.0));
    
    if (u_sunAltitudeDeg > -18.0) {
        // Intensitat base depèn de l'altitud solar
        float sunIntensity = smoothstep(-18.0, 10.0, u_sunAltitudeDeg);
        
        // El glow es concentra al voltant del sol: cos^4(gamma)
        float glowFactor = pow(max(0.0, cos(gamma)), 4.0);
        // Ampliat per terbolesa
        glowFactor *= min(1.0, u_turbidity * 0.5);
        
        // Constants are linear-sRGB equivalents of the established sRGB
        // scattering colours, so output encoding does not brighten them twice.
        vec3 glowColor = mix(
            vec3(1.0, 0.6038, 0.1329),
            vec3(1.0, 1.0, 0.7874),
            sunIntensity
        );
        skyColor += glowColor * glowFactor * sunIntensity * 0.5 * u_solarDiscTransmission;
    }

    // 3b. AURÈOLA SOLAR ATMOSFÈRICA (Mie, sense lens flare)
    // Dues escales angulars donen un nucli compacte i una dispersió exterior
    // suau. La terbolesa amplia l'aurèola; el Sol sota l'horitzó no la dibuixa.
    float sunAboveHorizon = smoothstep(-0.833, 1.5, u_sunAltitudeDeg);
    float haze = clamp((u_turbidity - 1.0) / 9.0, 0.0, 1.0);
    float innerWidthRad = mix(0.018, 0.040, haze);
    float outerWidthRad = mix(0.055, 0.120, haze);
    float innerAureole = exp(-gamma / innerWidthRad);
    float outerAureole = exp(-gamma / outerWidthRad);
    float lowSunWarmth = 1.0 - smoothstep(3.0, 25.0, u_sunAltitudeDeg);
    vec3 solarHaloColor = mix(
        vec3(1.0, 0.6383, 0.2957),
        vec3(1.0, 0.1195, 0.0072),
        lowSunWarmth
    );
    float solarHalo = sunAboveHorizon
        * (innerAureole * mix(0.72, 0.92, haze)
            + outerAureole * mix(0.10, 0.22, haze));
    skyColor += solarHaloColor * solarHalo * u_solarDiscTransmission;
    
    // The backend palette already carries the eclipse dimming.  Keep only a
    // modest local contrast response here: applying the full factor twice made
    // totality look like an ordinary black night instead of deep twilight.
    skyColor *= mix(0.88, 1.0, u_skyEclipseDimmingFactor);
    
    // 4. CONTAMINACIÓ LUMÍNICA (Bortle Glow)
    if (u_artificialBrightness > 0.0) {
        // El glow de contaminació lluminosa decreix amb l'elevació (model simple)
        // elevation_falloff = (90 - viewAlt) / 90.0, elevat a la 2.5
        float viewAltNormalized = max(0.0, viewAltDeg) / 90.0;
        float lpFalloff = pow(1.0 - viewAltNormalized, 2.5);
        
        // Multiplicat pel twilight factor perquè de dia no es veu la LP
        float lpStrength = u_artificialBrightness * u_twilightFactor * lpFalloff;
        
        // Limitem el màxim teòric per no saturar
        lpStrength = min(0.8, lpStrength);
        
        skyColor = mix(skyColor, COLOR_LP_GLOW, lpStrength);
    }
    
    // 5. COLORS PURS vs REALISTES
    if (u_pureColors) {
        // En mode pur, quantitzem o exagerem saturació per debug visual
        skyColor = floor(skyColor * 8.0) / 8.0; 
    }
    
    // Clamp final i alpha 1.0
    gl_FragColor = vec4(clamp(skyColor, 0.0, 1.0), 1.0);
    #include <tonemapping_fragment>
    #include <colorspace_fragment>

}
`;

/** CPU mirror of the shader's scalar halo profile for deterministic QA. */
export function solarAtmosphericHaloStrength(
  angularSeparationDeg: number,
  sunAltitudeDeg: number,
  turbidity: number,
): number {
  if (![angularSeparationDeg, sunAltitudeDeg, turbidity].every(Number.isFinite)) return 0;
  const gamma = Math.max(0, angularSeparationDeg) * Math.PI / 180;
  const aboveHorizon = smoothstep(-0.833, 1.5, sunAltitudeDeg);
  const haze = clamp01((turbidity - 1) / 9);
  const innerWidth = lerp(0.018, 0.040, haze);
  const outerWidth = lerp(0.055, 0.120, haze);
  return aboveHorizon * (
    Math.exp(-gamma / innerWidth) * lerp(0.72, 0.92, haze)
    + Math.exp(-gamma / outerWidth) * lerp(0.10, 0.22, haze)
  );
}

function smoothstep(edge0: number, edge1: number, value: number): number {
  const t = clamp01((value - edge0) / (edge1 - edge0));
  return t * t * (3 - 2 * t);
}

function lerp(start: number, end: number, fraction: number): number {
  return start + (end - start) * fraction;
}

function clamp01(value: number): number {
  return Math.max(0, Math.min(1, value));
}
