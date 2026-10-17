# Matriu de traçabilitat — pla executable redissenyat

> La numeració de passos anterior a 2026-10-17 queda històrica. Aquesta taula segueix el [pla executable canònic](19-pla-executable-codex.md).

| Requeriment | Decisió | Pas | Test/evidència |
|---|---|---:|---|
| contracte/dades v1 | manifest i política V1 preregistrada; valors diferits als gates | 7.1 completat | [perfil](skyglow-v1-profile.json), [fonts](../evidencies/pas7.1/auditoria-fonts.md) i [validació](../evidencies/pas7.1/validacio-contracte.txt) |
| VNP46 operatiu | observació immutable, no emissió | 7.2 | fixtures product/release/quality/LOW-RAD |
| mesura DNB | RSR real + BAND_INTEGRATED | 7.3 | oracle espectral fi de mesura |
| error espectral V1 | pressupost justificat abans de seleccionar bandes; manca de valor bloqueja aquí | 7.4 | oracle fi, origen i registre congelat + SPDs adverses + bandSetId homologat |
| SourceModel | SPD + angular + incertesa | 7.5 | F1 tancada o pas bloquejat |
| oracle transport | SG-REF independent + àrea directa | 7.6 | convergència, incertesa numèrica i fixtures analítiques per fonamentar 7.12 |
| kernel únic | zenit=direcció ordinària | 7.7 | B0 + invariants geomètrics |
| camp òptic | provider estàndard tiled | 7.8 | fixtures multi-tile |
| Rayleigh/aerosol | fase de referència primer, comparació diagnòstica | 7.9 | B1, invariants i residuals SG-REF sense PASS/FAIL numèric |
| gas/espectral | absorció no nul·la, comparació diagnòstica | 7.10 | B2/B4 i invariants, sense PASS/FAIL de transport |
| terreny/curvatura | visibilitat física, comparació diagnòstica | 7.11 | topologia i oclusió, sense PASS/FAIL de transport |
| gate zenital V1 | preregistrar tolerància abans del runtime candidat | 7.12 | origen admissible, convergència SG-REF 7.6 i PASS/FAIL runtime↔SG-REF |
| cúpules | DomeProfile des de ruta directa | 7.13 | all-sky dens + invariant zenit |
| projeccions | SQM/TESS/CIE post-kernel | 7.14 | sensor golden |
| atmosfera real | ERA5/CAMS com providers | 7.15 | fixtures/camps parcials |
| incertesa | ledger quantitatiu | 7.16 | coverage/provenance |
| ground truth clear V1 | criteris empírics preregistrats abans del conjunt reservat, amb incerteses instrumental, de dades i del model | 7.17 | partició `held-out`, origen i validació leave-one-site-out |
| compressió fonts | watershed/quadtree com backend | 7.18 | B5 vs àrea directa |
| compressió fase | Legendre com backend | 7.19 | B3 vs fase ref |
| AD/error budget | cotes conservadores | 7.20 | FD + bounds |
| cache/scheduler | reuse només dins error | 7.21 | cold/warm/movement/teleport |
| LUT/FFT opcional V1 | SLO de producte aprovats abans de decidir; manca de requisit bloqueja 7.22 | 7.22 | aprovació, plataforma, SLO congelats i directe vs accelerat |
| núvols | CloudOpticalState + B6 | 7.23 | clear limit + oracle |
| validació final | domini homologable congelat | 7.24 | clear/cloudy report |
| bridge | DTO + revisions | 7.25 | stale discard/bytes |
| renderer/debug | doble buffer lineal | 7.26 | frame/stutter/leaks |
| composició | canals lineals separats | 7.27 | reference/instantaneous |
| homologació | B7 + SLO + cap bloqueig ocult; només criteris congelats, cap llindar nou | 7.28 | informe final amb versions i procedència dels gates previs |

## Frontera amb el cel astral

El cel físic 7.51+ conserva la seva vertical. Els dos únics contractes que aquesta reordenació mou i que són consumits explícitament per la vertical astral són:
- `RadiativeErrorBudget`: ara es formalitza a **7.20**.
- `CloudOpticalState`: ara es formalitza a **7.23**.

No hi ha dependència del skyglow cap al Pas 7.65: l’oracle artificial és `SG-REF` de 7.6.
