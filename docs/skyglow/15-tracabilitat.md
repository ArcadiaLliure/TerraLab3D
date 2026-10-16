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
| Llicències comercials | allowlist permissiva; Hillaire MIT, Bruneton BSD-3, ROLO/USGS PD, Copernicus amb atribució; copyleft només referència sota política actual | cel-fisic/03 | 7.51 | manifests, avisos i gate de distribució |
| Selector simulat/real | flag persistent i estratègies independents | cel-fisic/01 | 7.52 | alternança i regressió legacy |
| Altura/geodèsia | estat ECEF/ENU + òptica compartida | cel-fisic/02 | 7.53, 7.58 | superfície/estratosfera/òrbita |
| Font solar | irradiància espectral + disc/distància/eclipsis | cel-fisic/02 | 7.54 | unitats i geometria |
| Lluna | ROLO/USGS + reflectància Hapke/LS separada | cel-fisic/02,05 | 7.55 | fixtures ROLO, fase i extrapolació |
| Transport | Hillaire runtime + branca espectral independent | cel-fisic/01 | 7.56 | Bruneton/path tracer |
| SkyView | RGB lineal; 192×108 perfil inicial configurable; sensors espectrals | cel-fisic/01,04 | 7.57 | colorimetria, format i projeccions |
| Limbe/terminador | raigs tangents + high-quality pass per error | cel-fisic/02 | 7.58 | superfície→òrbita, arc dia/nit |
| Il·luminació | directe/difús/ombra/eclipsi sense doble comptatge | cel-fisic/02 | 7.59 | terreny/cel/eclipsi |
| Integració | façana Three.js, lifecycle i revisions | cel-fisic/01 | 7.60 | context loss/resync |
| Fons natural | airglow + zodiacal + integrated starlight; Pas 10 conserva Via Làctia | cel-fisic/02,05 | 7.61 | GAMBONS/ESO extern + no double count |
| Error budget | cota superior; 0,1 % individual / 0,5 % acumulat defaults | cel-fisic/04,05 | 7.62 | falsos pruning = 0, sensor bounds |
| Núvols | CloudOpticalState compartit; delta-Eddington astral | cel-fisic/02,04 | 7.63 | clear/τ i oracle cloud |
| Scheduler | latest-wins monotònic, queue efectiva <=1 | cel-fisic/01,04 | 7.64 | stale/cancel/scrub |
| Oracle | Bruneton + Hillaire path tracer + ROLO + oracles específics | cel-fisic/04,05 | 7.65 | fixtures reproduïbles |
| Validació | radiometria/sensors/geometria separats | cel-fisic/04 | 7.66 | matriu i gates |
| Rendiment | perfil desktop-60; p95/p99; independent de N | cel-fisic/04 | 7.67 | telemetry reproduïble |
| Homologació | legal + científica + runtime + simulated permanent | cel-fisic/04 | 7.68 | informe final i recovery |
