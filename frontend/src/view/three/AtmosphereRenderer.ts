import * as THREE from "three";
import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import { skyVertexShader, skyFragmentShader } from "./shaders/skyShader";

export class AtmosphereRenderer {
  private readonly material: THREE.ShaderMaterial;
  private readonly mesh: THREE.Mesh;

  constructor(private readonly parent: THREE.Object3D) {
    this.material = new THREE.ShaderMaterial({
      vertexShader: skyVertexShader,
      fragmentShader: skyFragmentShader,
      uniforms: {
        u_sunDirectionENU: { value: new THREE.Vector3(0, -1, 0) },
        u_sunAltitudeDeg: { value: -90.0 },
        u_twilightFactor: { value: 1.0 },
        u_turbidity: { value: 2.5 },
        u_bortleClass: { value: 4.0 },
        u_artificialBrightness: { value: 0.15 },
        u_atmosphereEnabled: { value: true },
        u_pureColors: { value: false },
      },
      depthWrite: false,
      depthTest: false,
      transparent: false,
      side: THREE.BackSide, // Dins del box
    });

    // Box gegant, com que estarà al celestialRoot no hi ha parallax
    const geometry = new THREE.BoxGeometry(2000, 2000, 2000);
    this.mesh = new THREE.Mesh(geometry, this.material);
    
    // Assegurar que es renderitza abans de tot (-1000) i que no fa frustum culling
    this.mesh.renderOrder = -1000;
    this.mesh.frustumCulled = false;
    
    // Afegim a l'arrel especificada (celestialRoot)
    this.parent.add(this.mesh);
  }

  public updateEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    const u = this.material.uniforms;
    
    const sunDir = snapshot.sunDirectionENU;
    // Three.js utilitza -Z per al Nord i +Z per al Sud, així que hem d'invertir l'eix Z
    u.u_sunDirectionENU.value.set(sunDir[0], sunDir[1], -sunDir[2]);
    u.u_sunAltitudeDeg.value = snapshot.sunAltitudeDeg;
    u.u_twilightFactor.value = snapshot.twilightFactor;
    u.u_turbidity.value = snapshot.turbidity;
    
    // Light Pollution
    if (snapshot.lightPollutionEnabled && snapshot.bortleClass !== null) {
      u.u_bortleClass.value = snapshot.bortleClass;
      // Per ara calculem l'artificial brightness aquí si no arriba explícit al snapshot.
      // Opcional: afegir artificial_sky_brightness al snapshot en un futur refactor.
      const linear = (snapshot.bortleClass - 1.0) / 8.0;
      u.u_artificialBrightness.value = linear * linear * (3.0 - 2.0 * linear);
    } else {
      u.u_bortleClass.value = 1.0;
      u.u_artificialBrightness.value = 0.0;
    }
    
    u.u_atmosphereEnabled.value = snapshot.atmosphereEnabled;
  }

  public setPureColors(enabled: boolean): void {
    this.material.uniforms.u_pureColors.value = enabled;
  }

  public dispose(): void {
    this.scene.remove(this.mesh);
    this.mesh.geometry.dispose();
    this.material.dispose();
  }
}
