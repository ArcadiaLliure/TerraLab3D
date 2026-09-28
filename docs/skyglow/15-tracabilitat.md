# Matriu de traçabilitat

| Requeriment | Decisió | Document | Pas | Test/evidència |
|---|---|---|---|---|
| zenit i cúpules mateixa física | un `PropagationKernel` | 01, ADR-001 | 23.51+ | golden zenit=mostra 90° |
| radiància lineal | suma abans de projecció | 01, ADR-005 | 23.51,23.65 | property test de linealitat |
| VIIRS real | adaptador + source model | 01,04,10 | 23.54–23.57 | fixture VNL/RSR checksum |
| segmentació | watershed + quadtree | 01, ADR-004 | 23.58–23.59 | regions sintètiques + error patch |
| espectre | normalization vs propagation | 01,06 | 23.53–23.57 | solver espectral fi |
| RSR real | NOAA NCC | 04,10 | 23.54 | checksum/provenance |
| atmosfera extensible | provider + tiled field | 02,06 | 23.60–23.62 | contract/provider tests |
| Rayleigh | fórmula normalitzada | 01,04 | 23.52 | unit/golden |
| aerosols | PhaseFunction unificada | 01,04 | 23.61–23.63 | B3 |
| gas | LUT `T_eff` | 01,04 | 23.64 | B4 |
| terreny | visibilitat binària + patch | 01,02 | 23.59,23.66 | occlusion flip |
| cache | error de canvi | 01,09 | 23.67 | hit/miss matrix |
| AD | forward mode en branca suau | 01,09 | 23.68 | B1b/B7 |
| cúpules | 9 mostres + PCHIP log | 01 | 23.69 | all-sky compression |
| renderer | doble buffer lineal | 03 | 23.70 | frame/stutter telemetry |
| ground truth | TESS/SQM/all-sky | 08 | 23.72 | leave-one-site-out |
| núvols | single scattering v1 | 01,04 | 23.73 | B6 |
| full | B7 + SLO | 07,08 | 23.74 | report JSON/CSV/plots |

Els identificadors de pas d'aquesta taula són els proposats pel lot documental; la font de veritat final és `docs/README.md` un cop actualitzat.