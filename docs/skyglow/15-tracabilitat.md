# Matriu de traçabilitat

| Requeriment | Decisió | Document | Pas | Test/evidència |
|---|---|---|---|---|
| zenit i cúpules mateixa física | un `PropagationKernel` | 01, ADR-001 | 7.2+ | golden zenit=mostra 90° |
| gate zenital absolut | validar 90° abans de promoure cúpules | 01,08, ADR-017 | 7.20 | reference solver + unitats + convergència |
| radiància lineal | suma abans de projecció | 01, ADR-005 | 7.2–7.28 | property test de linealitat |
| VIIRS real | adaptador + source model | 01,04,10 | 7.5–7.10 | fixture VNL/RSR checksum |
| segmentació | watershed + quadtree | 01, ADR-004 | 7.9–7.10 | regions sintètiques + error patch |
| espectre | normalization vs propagation, N configurat | 01,06, ADR-006 | 7.5–7.7 | unitats, vectors i projeccions de la configuració activa; cap benchmark per triar N |
| RSR real | NOAA NCC | 04,10, ADR-007 | 7.6 | checksum/provenance |
| atmosfera extensible | provider + tiled field | 02,06, ADR-008/009 | 7.11, 7.15–7.16 | contract/provider tests |
| Rayleigh | fórmula normalitzada | 01,04 | 7.3 | unit/golden |
| aerosols | PhaseFunction unificada | 01,04, ADR-013 | 7.12–7.13 | B3 |
| gas | LUT `T_eff` | 01,04 | 7.14 | B4 |
| terreny | visibilitat binària + patch | 01,02 | 7.10,7.17 | occlusion flip |
| cache | error de canvi | 01,09, ADR-010 | 7.18 | hit/miss + small-motion + teleport |
| AD | forward mode en branca suau | 01,09, ADR-011 | 7.4,7.18 | B1b/B7 |
| rendiment runtime | cap integral per frame; coalescing/prefetch validat | 02,03,05,07, ADR-018 | 7.18,7.24,7.28 | recomputeHz, TTFF, queue, stale/cancel |
| cúpules | 9 mostres + PCHIP log | 01, ADR-002/003 | 7.21 | all-sky compression + zenit invariant |
| projeccions fotomètriques | post-kernel, sensor-specific | 01,06,08, ADR-017 | 7.22 | CIE/sensor golden, zero point/FOV |
| composició del cel | artificial+natural+Lluna+crepuscle lineal | 01,06, ADR-017 | 7.23 | reference vs instantaneous |
| renderer | doble buffer lineal | 03 | 7.24 | frame/stutter telemetry |
| ground truth | TESS/SQM/all-sky | 08 | 7.26 | leave-one-site-out |
| núvols | single scattering v1 | 01,04 | 7.27 | B6 |
| full | B7 + SLO | 07,08 | 7.28 | report JSON/CSV/plots |

Els identificadors de pas d'aquesta taula són els proposats pel lot documental; la font de veritat final és `docs/README.md` un cop actualitzat.

## Matriu de frontera amb el cel astral

| Requeriment | Decisió | Document | Pas | Test/evidència |
|---|---|---|---|---|
| Llicències comercials | Hillaire MIT, Bruneton BSD-3, Third-Party per recurs incorporat | cel-fisic/03 | 7.51 | gate de manifests i avisos |
| Selector simulat/real | flag persistent, estratègies independents | cel-fisic/01 | 7.52 | alternança i regressió legacy |
| Altura | estat geodèsic i òptic compartit | cel-fisic/02 | 7.53,7.58 | superfície/estratosfera/òrbita |
| Fonts Sol/Lluna | irradiància espectral i fase separades | cel-fisic/02 | 7.54–7.55 | unitats/fase/eclipsi |
| SkyView LUT | RGB lineal només per render, sensors espectrals | cel-fisic/01,04 | 7.56–7.57 | colorimetria i projeccions independents |
| Limbe solar terrestre | raigs tangents, oclusió i terminador | cel-fisic/02 | 7.58 | arc diürn/nocturn i altitud |
| Integració i homologació | latest-wins, sense stutter, mode simulat permanent | cel-fisic/04 | 7.59–7.62 | SLO, llicències i regressions |
