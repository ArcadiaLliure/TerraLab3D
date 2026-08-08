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
uniform float u_twilightFactor;
uniform float u_turbidity;
uniform float u_bortleClass;
uniform float u_artificialBrightness;
uniform bool u_atmosphereEnabled;
uniform bool u_pureColors;

varying vec3 vViewRay;

const float PI = 3.14159265359;

// Colors físics aproximats (calibrats amb TerraLab sky_color_phys)
const vec3 COLOR_DAY_ZENITH = vec3(0.15, 0.35, 0.70);
const vec3 COLOR_DAY_HORIZON = vec3(0.55, 0.65, 0.75);

const vec3 COLOR_SUNSET_ZENITH = vec3(0.1, 0.2, 0.5);
const vec3 COLOR_SUNSET_HORIZON = vec3(0.9, 0.4, 0.1);

const vec3 COLOR_CIVIL_ZENITH = vec3(0.05, 0.1, 0.25);
const vec3 COLOR_CIVIL_HORIZON = vec3(0.4, 0.15, 0.1);

const vec3 COLOR_NAUTICAL_ZENITH = vec3(0.01, 0.02, 0.05);
const vec3 COLOR_NAUTICAL_HORIZON = vec3(0.05, 0.05, 0.1);

const vec3 COLOR_NIGHT_ZENITH = vec3(0.0, 0.0, 0.0);
const vec3 COLOR_NIGHT_HORIZON = vec3(0.0, 0.0, 0.0);

const vec3 COLOR_LP_GLOW = vec3(0.55, 0.51, 0.43); // 140, 130, 110 (warm yellow/brown)
const vec3 COLOR_GROUND = vec3(0.01, 0.01, 0.01);

void main() {
    vec3 viewDir = normalize(vViewRay);
    
    // Altitud de vista (ENU Y és amunt)
    float viewAlt = asin(clamp(viewDir.y, -1.0, 1.0));
    float viewAltDeg = viewAlt * 180.0 / PI;
    
    if (viewDir.y < -0.05) {
        // Sota l'horitzó (night floor)
        // Utilitzem una transició suau per evitar aliasing
        float blend = smoothstep(-0.05, 0.0, viewDir.y);
        gl_FragColor = vec4(mix(COLOR_GROUND, vec3(0.0), blend), 1.0);
        
        // Si estem per sota i no prop de l'horitzó, sortim ràpid
        if (viewDir.y < -0.1) {
            return;
        }
    }
    
    if (!u_atmosphereEnabled) {
        // Sense atmosfera: fons negre
        gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
        return;
    }
    
    // 1. COLORS BASE (Interpolació per altitud solar)
    vec3 zenithColor = vec3(0.0);
    vec3 horizonColor = vec3(0.0);
    
    if (u_sunAltitudeDeg >= 6.0) {
        zenithColor = COLOR_DAY_ZENITH;
        horizonColor = COLOR_DAY_HORIZON;
    } else if (u_sunAltitudeDeg >= 0.0) {
        float t = u_sunAltitudeDeg / 6.0;
        zenithColor = mix(COLOR_SUNSET_ZENITH, COLOR_DAY_ZENITH, t);
        horizonColor = mix(COLOR_SUNSET_HORIZON, COLOR_DAY_HORIZON, t);
    } else if (u_sunAltitudeDeg >= -6.0) {
        float t = (u_sunAltitudeDeg + 6.0) / 6.0;
        zenithColor = mix(COLOR_CIVIL_ZENITH, COLOR_SUNSET_ZENITH, t);
        horizonColor = mix(COLOR_CIVIL_HORIZON, COLOR_SUNSET_HORIZON, t);
    } else if (u_sunAltitudeDeg >= -12.0) {
        float t = (u_sunAltitudeDeg + 12.0) / 6.0;
        zenithColor = mix(COLOR_NAUTICAL_ZENITH, COLOR_CIVIL_ZENITH, t);
        horizonColor = mix(COLOR_NAUTICAL_HORIZON, COLOR_CIVIL_HORIZON, t);
    } else if (u_sunAltitudeDeg >= -18.0) {
        float t = (u_sunAltitudeDeg + 18.0) / 6.0;
        zenithColor = mix(COLOR_NIGHT_ZENITH, COLOR_NAUTICAL_ZENITH, t);
        horizonColor = mix(COLOR_NIGHT_HORIZON, COLOR_NAUTICAL_HORIZON, t);
    } else {
        zenithColor = COLOR_NIGHT_ZENITH;
        horizonColor = COLOR_NIGHT_HORIZON;
    }
    
    // 2. MIX HORITZÓ - ZENIT (per a la vista actual)
    // El gradient va ràpid a prop de l'horitzó i és estable amunt
    float zenithBlend = clamp(pow(max(0.0, viewDir.y), 0.5), 0.0, 1.0);
    vec3 skyColor = mix(horizonColor, zenithColor, zenithBlend);
    
    // 3. GLOW SOLAR (Scattering)
    float gamma = acos(clamp(dot(viewDir, u_sunDirectionENU), -1.0, 1.0));
    
    if (u_sunAltitudeDeg > -18.0) {
        // Intensitat base depèn de l'altitud solar
        float sunIntensity = smoothstep(-18.0, 10.0, u_sunAltitudeDeg);
        
        // El glow es concentra al voltant del sol: cos^4(gamma)
        float glowFactor = pow(max(0.0, cos(gamma)), 4.0);
        // Ampliat per terbolesa
        glowFactor *= min(1.0, u_turbidity * 0.5);
        
        vec3 glowColor = mix(vec3(1.0, 0.8, 0.4), vec3(1.0, 1.0, 0.9), sunIntensity);
        skyColor += glowColor * glowFactor * sunIntensity * 0.5;
    }
    
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
    
    // Transició suau horitzó - sota terra (si viewDir.y és entre -0.05 i 0.0)
    if (viewDir.y < 0.0) {
        float blend = smoothstep(-0.05, 0.0, viewDir.y);
        gl_FragColor.rgb = mix(COLOR_GROUND, gl_FragColor.rgb, blend);
    }
}
`;
