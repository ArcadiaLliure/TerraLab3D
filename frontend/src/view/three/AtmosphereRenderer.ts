import * as THREE from "three";

import type { SkyEnvironmentSnapshot } from "../../contracts/sky_environment_contracts";
import { setThreeFromEnu } from "./celestialCoordinates";
import { skyFragmentShader, skyVertexShader } from "./shaders/skyShader";

export class AtmosphereRenderer {
  private readonly material: THREE.ShaderMaterial;
  private readonly mesh: THREE.Mesh;
  private readonly sunDirection = { value: new THREE.Vector3(0, -1, 0) };
  private readonly sunAltitude = { value: -90.0 };
  private readonly solarDiscTransmission = { value: 1.0 };
  private readonly skyEclipseDimmingFactor = { value: 1.0 };
  private readonly twilight = { value: 1.0 };
  private readonly turbidity = { value: 2.5 };
  private readonly bortle = { value: 4.0 };
  private readonly artificialBrightness = { value: 0.15 };
  private readonly atmosphereEnabled = { value: true };
  private readonly pureColors = { value: false };
  private readonly zenithColor = { value: new THREE.Color(0, 0, 0) };
  private readonly horizonColor = { value: new THREE.Color(0, 0, 0) };
  private readonly groundColor = { value: new THREE.Color(0, 0, 0) };
  private disposed = false;

  constructor(private readonly parent: THREE.Object3D) {
    this.material = new THREE.ShaderMaterial({
      vertexShader: skyVertexShader,
      fragmentShader: skyFragmentShader,
      uniforms: {
        u_sunDirectionENU: this.sunDirection,
        u_sunAltitudeDeg: this.sunAltitude,
        u_solarDiscTransmission: this.solarDiscTransmission,
        u_skyEclipseDimmingFactor: this.skyEclipseDimmingFactor,
        u_twilightFactor: this.twilight,
        u_turbidity: this.turbidity,
        u_bortleClass: this.bortle,
        u_artificialBrightness: this.artificialBrightness,
        u_atmosphereEnabled: this.atmosphereEnabled,
        u_pureColors: this.pureColors,
        u_zenithColorLinear: this.zenithColor,
        u_horizonColorLinear: this.horizonColor,
        u_groundColorLinear: this.groundColor,
      },
      depthWrite: false,
      depthTest: false,
      side: THREE.BackSide,
    });
    this.mesh = new THREE.Mesh(new THREE.BoxGeometry(2000, 2000, 2000), this.material);
    this.mesh.name = "atmosphere";
    this.mesh.renderOrder = -1000;
    this.mesh.frustumCulled = false;
    this.parent.add(this.mesh);
  }

  updateEnvironment(snapshot: SkyEnvironmentSnapshot): void {
    setThreeFromEnu(this.sunDirection.value, snapshot.sunDirectionENU);
    this.sunAltitude.value = snapshot.sunAltitudeDeg;
    this.twilight.value = snapshot.twilightFactor;
    this.turbidity.value = snapshot.turbidity;
    this.solarDiscTransmission.value = snapshot.solarDiscTransmission;
    this.skyEclipseDimmingFactor.value = snapshot.skyEclipseDimmingFactor;
    if (snapshot.lightPollutionEnabled && snapshot.bortleClass !== null) {
      this.bortle.value = snapshot.bortleClass;
      const linear = (snapshot.bortleClass - 1.0) / 8.0;
      this.artificialBrightness.value = linear * linear * (3.0 - 2.0 * linear);
    } else {
      this.bortle.value = 1.0;
      this.artificialBrightness.value = 0.0;
    }
    this.atmosphereEnabled.value = snapshot.atmosphereEnabled;
    this.zenithColor.value.setRGB(...snapshot.zenithColorLinear);
    this.horizonColor.value.setRGB(...snapshot.horizonColorLinear);
    this.groundColor.value.setRGB(...snapshot.groundColorLinear);
  }

  setPureColors(enabled: boolean): void {
    this.pureColors.value = enabled;
  }

  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;
    this.parent.remove(this.mesh);
    this.mesh.geometry.dispose();
    this.material.dispose();
  }
}
