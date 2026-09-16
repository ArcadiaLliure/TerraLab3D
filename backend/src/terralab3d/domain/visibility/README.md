# Domini de visibilitat de trajectòries

Aquest mòdul modela la trajectòria aparent d'un objecte i la seva relació
geomètrica amb l'horitzó local. No depèn de Three.js, WebGL, la interfície, el
transport binari ni els adaptadors d'efemèrides.

Responsabilitats:

- identitat i capacitats de les famílies d'objectes observables;
- mostres topocèntriques amb unitats explícites en graus i marc ENU;
- procedència del perfil d'horitzó;
- classificació de trams visibles, ocults, sota l'horitzó astronòmic o amb
  dades insuficients;
- esdeveniments refinats de sortida, posta i tangència;
- resum de visibilitat de l'interval i circumpolaritat astronòmica.

L'aplicació obté les posicions mitjançant
[`ObservablePositionPort`](../../application/ports/observable_positions.py),
orquestra el mostreig a
[`apparent_trajectory.py`](../../application/apparent_trajectory.py) i publica
un DTO binari renderer-neutral. El frontend és l'únic responsable de convertir
aquest DTO en buffers i estils Three.js.

