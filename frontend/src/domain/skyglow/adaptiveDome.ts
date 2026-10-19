/** Reconstrucció de presentació v2; transport autoritatiu exclusivament Python. */
import { evaluateProfile, pchipValue, type DomeProfile } from "./domeProfile";

export interface AdaptiveDomeField {
  schemaVersion: 2;
  strategy: "adaptive-pchip-log-az-el-v2";
  interpolation: "PCHIP_LOG";
  azimuthInterpolation: "PERIODIC_PCHIP_LOG";
  radianceUnit: string;
  provenance: string;
  revision: number;
  topM: number;
  profiles: readonly DomeProfile[];
  blockedAzimuthIntervals: readonly boolean[];
  directOnly: boolean;
}

export function evaluateAdaptiveDome(field: AdaptiveDomeField, azimuth: number, elevation: number): number | null {
  const profiles = field.profiles, n = profiles.length;
  if (field.schemaVersion !== 2 || field.strategy !== "adaptive-pchip-log-az-el-v2" ||
      field.interpolation !== "PCHIP_LOG" || field.azimuthInterpolation !== "PERIODIC_PCHIP_LOG" ||
      !field.radianceUnit || !field.provenance || !Number.isSafeInteger(field.revision) || field.revision < 0 ||
      !Number.isFinite(field.topM) || field.topM <= 0 || n < 4 ||
      (field.blockedAzimuthIntervals.length !== 0 && field.blockedAzimuthIntervals.length !== n)) throw new Error("Camp adaptatiu invàlid");
  const az = profiles.map(p => p.azimuthDeg);
  if (az.some((a, i) => !Number.isFinite(a) || a < 0 || a >= 360 || (i > 0 && a <= az[i - 1]!)) ||
      profiles.some(p => p.elevationSamplesDeg[0] !== .5 || p.elevationSamplesDeg[p.elevationSamplesDeg.length - 1] !== 90)) throw new Error("Domini angular invàlid");
  const zenith = profiles.map(p => p.radianceSamples[p.radianceSamples.length - 1]!);
  if (Math.max(...zenith) - Math.min(...zenith) > 1e-12 * Math.max(...zenith)) throw new Error("Zenit inconsistent");
  if (!Number.isFinite(azimuth) || !Number.isFinite(elevation) || elevation < .5 || elevation > 90) throw new Error("Direcció fora del domini");
  const q = ((azimuth % 360) + 360) % 360;
  const exact = az.indexOf(q);
  if (exact >= 0) {
    const profile = profiles[exact]!;
    if (field.directOnly && !profile.elevationSamplesDeg.includes(elevation)) return null;
    return evaluateProfile(profile, elevation);
  }
  if (field.directOnly) return null;
  let i = -1;
  while (i < n - 1 && az[i + 1]! < q) i++;
  const index = (k: number) => ((k % n) + n) % n;
  if (field.blockedAzimuthIntervals[index(i)]) return null;
  const positions = [i - 1, i, i + 1, i + 2];
  const values = positions.map(k => evaluateProfile(profiles[index(k)]!, elevation));
  if (values.some(v => v === null || v <= 0)) return null;
  const b = values as number[];
  const epsilon = Math.min(...b) * 1e-15;
  const x = positions.map(k => az[index(k)]! + 360 * Math.floor(k / n));
  return Math.max(0, Math.exp(pchipValue(x, b.map(v => Math.log(v + epsilon)), q)) - epsilon);
}
