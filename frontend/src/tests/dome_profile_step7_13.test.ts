import golden from "../../../docs/evidencies/pas7.13/golden-pchip-python-typescript.json";
import { evaluateDome, evaluateProfile, type DomeField, type DomeProfile } from "../domain/skyglow/domeProfile";

let count = 0;
function assert(ok: boolean, message: string): void {
  if (!ok) throw new Error(message);
  count++;
}
for (const row of golden.cases) {
  for (const query of row.queries) {
    const actual = evaluateProfile(row.profile, query.elevationDeg);
    assert(actual !== null && Math.abs(actual / query.expected - 1) <= golden.toleranceRelative, "Golden SciPy/Python/TypeScript");
  }
}
const p: DomeProfile = { azimuthDeg: 0, elevationSamplesDeg: [.5, 2, 5, 90],
  radianceSamples: [0, 0, 1e-12, 2e-12], epsilonRadiance: 1e-27, blockedIntervals: [] };
assert(evaluateProfile(p, 1) === null && evaluateProfile(p, 3) === null, "No s'inventa llum entre zeros ni a una transició");
assert(evaluateProfile(p, .5) === 0, "Zero exacte");
assert(evaluateProfile({ ...p, blockedIntervals: [false, false, true] }, 30) === null, "Barrera opaca sense suavitzat");
const positive = golden.cases[0]!.profile;
const field: DomeField = { schemaVersion: 1, interpolation: "PCHIP_LOG", azimuthInterpolation: "PERIODIC_LINEAR_RADIANCE",
  radianceUnit: "relative m^-2 sr^-1", provenance: "Fixture de control C, sense calibratge absolut", revision: 0, topM: 75000,
  directOnly: false, profiles: [{ ...positive, azimuthDeg: 0 }, { ...positive, azimuthDeg: 180 }] };
for (const az of [-720, -360, 0, 360, 720]) {
  assert(evaluateDome(field, az, 20) === evaluateDome(field, 0, 20), "Wrap periòdic");
  assert(evaluateDome(field, az + 37.5, 90) === positive.radianceSamples[8], "Invariant zenital");
}
assert(evaluateDome({ ...field, directOnly: true }, 45, 90) === null, "DEM sense continuïtat inferida");
let invalid = false;
try { evaluateDome(field, 0, 0); } catch { invalid = true; }
assert(invalid, "Sense extrapolació sota0,5°");
console.log(`DomeProfile 7.13: ${count} comprovacions superades`);
