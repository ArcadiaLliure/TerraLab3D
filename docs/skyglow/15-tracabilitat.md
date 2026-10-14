# Matriu de traçabilitat

| Requeriment | Decisió | Document | Pas | Test/evidència |
|---|---|---|---|---|
| zenit i cúpules mateixa física | un `PropagationKernel` | 01, ADR-001 | 23.51+ | golden zenit=mostra 90° |
| gate zenital absolut | validar 90° abans de promoure cúpules | 01,08, ADR-017 | 23.681 | reference solver + unitats + convergència |
| radiància lineal | suma abans de projecció | 01, ADR-005 | 23.51–23.74 | property test de linealitat |
| VIIRS real | adaptador + source model | 01,04,10 | 23.54–23.59 | fixture VNL/RSR checksum |
| segmentació | watershed + quadtree | 01, ADR-004 | 23.58–23.59 | regions sintètiques + error patch |
| espectre | normalization vs propagation | 01,06 | 23.54–23.56 | solver espectral fi |
| RSR real | NOAA NCC | 04,10, ADR-007 | 23.55 | checksum/provenance |
| atmosfera extensible | provider + tiled field | 02,06, ADR-008/009 | 23.60, 23.64–23.65 | contract/provider tests |
| Rayleigh | fórmula normalitzada | 01,04 | 23.52 | unit/golden |
| aerosols | PhaseFunction unificada | 01,04, ADR-013 | 23.61–23.62 | B3 |
| gas | LUT `T_eff` | 01,04 | 23.63 | B4 |
| terreny | visibilitat binària + patch | 01,02 | 23.59,23.66 | occlusion flip |
| cache | error de canvi | 01,09, ADR-010 | 23.67 | hit/miss + small-motion + teleport |
| AD | forward mode en branca suau | 01,09, ADR-011 | 23.53,23.67 | B1b/B7 |
| rendiment runtime | cap integral per frame; coalescing/prefetch validat | 02,03,05,07, ADR-018 | 23.67,23.70,23.74 | recomputeHz, TTFF, queue, stale/cancel |
| cúpules | 9 mostres + PCHIP log | 01, ADR-002/003 | 23.69 | all-sky compression + zenit invariant |
| projeccions fotomètriques | post-kernel, sensor-specific | 01,06,08, ADR-017 | 23.691 | CIE/sensor golden, zero point/FOV |
| composició del cel | artificial+natural+Lluna+crepuscle lineal | 01,06, ADR-017 | 23.692 | reference vs instantaneous |
| renderer | doble buffer lineal | 03 | 23.70 | frame/stutter telemetry |
| ground truth | TESS/SQM/all-sky | 08 | 23.72 | leave-one-site-out |
| núvols | single scattering v1 | 01,04 | 23.73 | B6 |
| full | B7 + SLO | 07,08 | 23.74 | report JSON/CSV/plots |

Els identificadors de pas d'aquesta taula són els proposats pel lot documental; la font de veritat final és `docs/README.md` un cop actualitzat.
