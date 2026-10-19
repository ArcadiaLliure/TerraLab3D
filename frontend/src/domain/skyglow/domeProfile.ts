/** PCHIP de presentació, compartit amb Python; sense física ni connexió Three.js. */
export interface DomeProfile {
  azimuthDeg: number;
  elevationSamplesDeg: readonly number[];
  radianceSamples: readonly number[];
  epsilonRadiance: number;
  blockedIntervals: readonly boolean[];
}

export interface DomeField {
  schemaVersion: 1;
  interpolation: "PCHIP_LOG";
  azimuthInterpolation: "PERIODIC_LINEAR_RADIANCE";
  radianceUnit: string;
  provenance: string;
  revision: number;
  topM: number;
  directOnly: boolean;
  profiles: readonly DomeProfile[];
}

export function pchipSlopes(x: readonly number[], y: readonly number[]): number[] {
  if (x.length !== y.length || x.length < 2 || [...x, ...y].some(v => !Number.isFinite(v)) ||
      x.some((v, i) => i > 0 && v <= x[i - 1]!)) throw new Error("Nusos PCHIP invàlids");
  const h = x.slice(1).map((v, i) => v - x[i]!);
  const d = y.slice(1).map((v, i) => (v - y[i]!) / h[i]!);
  if (x.length === 2) return [d[0]!, d[0]!];
  const edge = (h0: number, h1: number, d0: number, d1: number) => {
    const v = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1);
    if (v === 0 || d0 === 0 || (v > 0) !== (d0 > 0)) return 0;
    return (d0 > 0) !== (d1 > 0) && Math.abs(v) > 3 * Math.abs(d0) ? 3 * d0 : v;
  };
  const slopes = [edge(h[0]!, h[1]!, d[0]!, d[1]!)];
  for (let i = 1; i < x.length - 1; i++) {
    const a = d[i - 1]!, b = d[i]!;
    const w1 = 2 * h[i]! + h[i - 1]!, w2 = h[i]! + 2 * h[i - 1]!;
    slopes.push(a === 0 || b === 0 || (a > 0) !== (b > 0) ? 0 : (w1 + w2) / (w1 / a + w2 / b));
  }
  const n = h.length;
  slopes.push(edge(h[n - 1]!, h[n - 2]!, d[n - 1]!, d[n - 2]!));
  return slopes;
}

export function pchipValue(x: readonly number[], y: readonly number[], query: number): number {
  const slopes = pchipSlopes(x, y);
  if (!Number.isFinite(query) || query < x[0]! || query > x[x.length - 1]!) throw new Error("PCHIP no extrapola");
  let i = 0;
  while (i < x.length - 2 && x[i + 1]! <= query) i++;
  const h = x[i + 1]! - x[i]!, t = (query - x[i]!) / h;
  return (2 * t ** 3 - 3 * t ** 2 + 1) * y[i]! + (t ** 3 - 2 * t ** 2 + t) * h * slopes[i]! +
    (-2 * t ** 3 + 3 * t ** 2) * y[i + 1]! + (t ** 3 - t ** 2) * h * slopes[i + 1]!;
}

export function evaluateProfile(p: DomeProfile, elevation: number): number | null {
  const x = p.elevationSamplesDeg, b = p.radianceSamples;
  pchipSlopes(x, b);
  if (!Number.isFinite(p.azimuthDeg) || x[0]! < .5 || x[x.length - 1]! > 90 ||
      b.some(v => v < 0) || !Number.isFinite(p.epsilonRadiance) || p.epsilonRadiance <= 0 ||
      (p.blockedIntervals.length !== 0 && p.blockedIntervals.length !== b.length - 1) ||
      b.some(v => v > 0 && p.epsilonRadiance > v * 1e-12)) throw new Error("Perfil invàlid");
  if (!Number.isFinite(elevation) || elevation < x[0]! || elevation > x[x.length - 1]!) throw new Error("Elevació fora del perfil");
  const exact = x.indexOf(elevation);
  if (exact >= 0) return b[exact]!;
  let i = 0;
  while (x[i + 1]! < elevation) i++;
  const usable = (k: number) => b[k]! > 0 && b[k + 1]! > 0 && !p.blockedIntervals[k];
  if (!usable(i)) return null;
  let lo = i, hi = i + 1;
  while (lo > 0 && usable(lo - 1)) lo--;
  while (hi < b.length - 1 && usable(hi)) hi++;
  return Math.max(0, Math.exp(pchipValue(x.slice(lo, hi + 1),
    b.slice(lo, hi + 1).map(v => Math.log(v + p.epsilonRadiance)), elevation)) - p.epsilonRadiance);
}

export function evaluateDome(field: DomeField, azimuth: number, elevation: number): number | null {
  if (!Number.isFinite(azimuth) || field.schemaVersion !== 1 || field.interpolation !== "PCHIP_LOG" ||
      field.azimuthInterpolation !== "PERIODIC_LINEAR_RADIANCE" || !field.radianceUnit || !field.provenance ||
      !Number.isSafeInteger(field.revision) || field.revision < 0 || !Number.isFinite(field.topM) || field.topM <= 0 ||
      field.profiles.length < 2) throw new Error("Camp angular invàlid");
  const az = field.profiles.map(p => p.azimuthDeg);
  if (az[0]! < 0 || az[az.length - 1]! >= 360 || az.some((v, i) => !Number.isFinite(v) || (i > 0 && v <= az[i - 1]!))) throw new Error("Azimuts invàlids");
  azimuth = ((azimuth % 360) + 360) % 360;
  const x = field.profiles[0]!.elevationSamplesDeg;
  if (!Number.isFinite(elevation) || elevation < x[0]! || elevation > x[x.length - 1]!) throw new Error("Elevació fora del camp");
  if (field.profiles.some(p => p.elevationSamplesDeg.length !== x.length || p.elevationSamplesDeg.some((v, i) => v !== x[i]))) throw new Error("Malles verticals diferents");
  const exact = az.indexOf(azimuth);
  if (exact >= 0) {
    const p = field.profiles[exact]!;
    if (field.directOnly && !p.elevationSamplesDeg.includes(elevation)) return null;
    return evaluateProfile(p, elevation);
  }
  if (field.directOnly) return null;
  let i = az.length - 1;
  for (let k = 0; k < az.length; k++) if (az[k]! < azimuth) i = k;
  const j = (i + 1) % az.length;
  const a = evaluateProfile(field.profiles[i]!, elevation), b = evaluateProfile(field.profiles[j]!, elevation);
  if (a === null || b === null || a <= 0 || b <= 0) return null;
  const w = ((azimuth - az[i]! + 360) % 360) / ((az[j]! - az[i]! + 360) % 360);
  return (1 - w) * a + w * b;
}
