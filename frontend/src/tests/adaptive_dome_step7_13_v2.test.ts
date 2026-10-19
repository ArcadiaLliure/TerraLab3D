import golden from "../../../docs/evidencies/pas7.13/adaptatiu-v2/golden-python-typescript-v2.json";
import { evaluateAdaptiveDome, type AdaptiveDomeField } from "../domain/skyglow/adaptiveDome";

let checks = 0;
function assert(value: boolean, message: string): void { if (!value) throw new Error(message); checks++; }
for (const item of golden.cases) {
  const field = item.field as AdaptiveDomeField;
  for (const query of item.queries) {
    const actual = evaluateAdaptiveDome(field,query.azimuthDeg,query.elevationDeg);
    assert(actual !== null && Math.abs(actual/query.expected-1) <= golden.relativeMaximum,"Golden SciPy v2");
  }
  assert(evaluateAdaptiveDome({...field,directOnly:true},22.5,45) === null,"DEM/àrea exigeixen directe entre nodes");
  assert(evaluateAdaptiveDome({...field,blockedAzimuthIntervals:[true,false,false,false,false,false,false,false]},22.5,45) === null,"No travessar barrera");
  const zero = {...field,profiles:field.profiles.map(p => ({...p,radianceSamples:p.radianceSamples.map(v => v===p.radianceSamples[0]?0:v)}))};
  assert(evaluateAdaptiveDome(zero,22.5,.5) === null,"No interpolar zeros físics");
}
console.log(`DomeProfile adaptatiu v2: ${checks} comprovacions superades`);
