# Matriu de traçabilitat — pla executable redissenyat

> La numeració de passos anterior a 2026-10-17 queda històrica. Aquesta taula segueix el [pla executable canònic](19-pla-executable-codex.md).

| Requeriment | Decisió | Pas | Test/evidència |
|---|---|---:|---|
| contracte/dades v1 | manifest + bloquejos explícits | 7.1 | manifest, fonts i decisions |
| VNP46 operatiu | observació immutable, no emissió | 7.2 | fixtures product/release/quality/LOW-RAD |
| mesura DNB | RSR real + BAND_INTEGRATED | 7.3 | oracle espectral fi de mesura |
| espectre runtime | V3 abans del kernel | 7.4 | SPDs adverses + bandSetId homologat |
| SourceModel | SPD + angular + incertesa | 7.5 | F1 tancada o pas bloquejat |
| oracle transport | SG-REF independent + àrea directa | 7.6 | convergència i fixtures analítiques |
| kernel únic | zenit=direcció ordinària | 7.7 | B0 + invariants geomètrics |
| camp òptic | provider estàndard tiled | 7.8 | fixtures multi-tile |
| Rayleigh/aerosol | fase de referència primer | 7.9 | B1 vs SG-REF |
| gas/espectral | absorció no nul·la | 7.10 | B2/B4 vs oracle fi |
| terreny/curvatura | visibilitat física | 7.11 | muntanya/curvatura vs SG-REF |
| gate zenital | transport directe abans d’optimitzar | 7.12 | runtime vs SG-REF |
| cúpules | DomeProfile des de ruta directa | 7.13 | all-sky dens + invariant zenit |
| projeccions | SQM/TESS/CIE post-kernel | 7.14 | sensor golden |
| atmosfera real | ERA5/CAMS com providers | 7.15 | fixtures/camps parcials |
| incertesa | ledger quantitatiu | 7.16 | coverage/provenance |
| ground truth clear | font i transport separats | 7.17 | leave-one-site-out |
| compressió fonts | watershed/quadtree com backend | 7.18 | B5 vs àrea directa |
| compressió fase | Legendre com backend | 7.19 | B3 vs fase ref |
| AD/error budget | cotes conservadores | 7.20 | FD + bounds |
| cache/scheduler | reuse només dins error | 7.21 | cold/warm/movement/teleport |
| LUT/FFT opcional | només si SLO ho exigeix | 7.22 | directe vs accelerat |
| núvols | CloudOpticalState + B6 | 7.23 | clear limit + oracle |
| validació final | domini homologable congelat | 7.24 | clear/cloudy report |
| bridge | DTO + revisions | 7.25 | stale discard/bytes |
| renderer/debug | doble buffer lineal | 7.26 | frame/stutter/leaks |
| composició | canals lineals separats | 7.27 | reference/instantaneous |
| homologació | B7 + SLO + cap bloqueig ocult | 7.28 | informe final |

## Frontera amb el cel astral

El cel físic 7.51+ conserva la seva vertical. Els dos únics contractes que aquesta reordenació mou i que són consumits explícitament per la vertical astral són:
- `RadiativeErrorBudget`: ara es formalitza a **7.20**.
- `CloudOpticalState`: ara es formalitza a **7.23**.

No hi ha dependència del skyglow cap al Pas 7.65: l’oracle artificial és `SG-REF` de 7.6.
