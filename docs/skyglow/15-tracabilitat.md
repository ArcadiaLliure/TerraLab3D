# Matriu de traçabilitat — pla executable redissenyat

> La numeració de passos anterior a 2026-10-17 queda històrica. Aquesta taula segueix el [pla executable canònic](19-pla-executable-codex.md).

| Requeriment | Decisió | Pas | Test/evidència |
|---|---|---:|---|
| contracte/dades v1 | manifest i política V1 preregistrada per SNPP; valors diferits als gates | 7.1 completat | [perfil v1](skyglow-v1-profile.json), [fonts](../evidencies/pas7.1/auditoria-fonts.md) i [validació](../evidencies/pas7.1/validacio-contracte.txt) |
| VNP46 inicial | observació immutable, no emissió; lector local verificat amb grànul real, sense ampliar resultat a J1/J2 | 7.2 completat | [fixtures, proves i contrast binari](../evidencies/pas7.2/validacio-adaptador.md) en verd; QA 0 real encara no contrastada |
| política multisatèl·lit | tres candidates C2, identitat i estat d'admissibilitat específic; cap fallback silenciós | 7.3 contracte completat; admissibilitat observacional C/H a 7.16–7.24 | [perfil v2](skyglow-v2-profile.json), [matriu J1/J2](../evidencies/pas7.3/revisio-multisatel-lit.md) i [dos grànuls VJ146 reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) |
| mesura DNB | operador TOA `BAND_INTEGRATED`, RSR versionada, Eq. (1) NASA TOA→L3 corregit, QA/unitats/llinatge VNP46 i VJ146 reals; RSR concretes de 2026 no homologades | 7.3 completat | [proves](../evidencies/pas7.3/validacio-model-dnb.md), [LUT SNPP](../evidencies/pas7.3/recerca-rsr-2026.md), [revisió multisatèl·lit](../evidencies/pas7.3/revisio-multisatel-lit.md) i [guia/grànuls](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) |
| error espectral V1 | `0,01 mag` de producte congelat abans de candidats; màxim per cas i regla absoluta prop de zero | 7.4 completat en domini tabulat; repetir 7.10/7.14 | [criteri preregistrat](../evidencies/pas7.4/criteri-preregistrat-v1.json), [238/238 casos i `bandSetId`](../evidencies/pas7.4/homologacio-bandset-v1.md); RSR històriques diagnòstiques, incertesa instrumental separada |
| SourceModel S | SPD, geometria, amplitud i emissió angular definides independentment de VIIRS; gate L3 preexistent segregat | 7.5 completat en el domini definit | [Validació S](../evidencies/pas7.5/validacio-source-model-s-v1.md), [política S/C/H](20-politica-rsr-i-validacio-per-dominis.md) i [auditoria observacional històrica](../evidencies/pas7.5/estat-inferencia-font-2026.md) |
| oracle transport | SG-REF independent + àrea directa | 7.6 | convergència, incertesa numèrica i fixtures analítiques per fonamentar 7.12 |
| kernel únic | zenit=direcció ordinària | 7.7 | B0 + invariants geomètrics |
| camp òptic | provider estàndard tiled | 7.8 | fixtures multi-tile |
| Rayleigh/aerosol | fase de referència primer, comparació diagnòstica | 7.9 | B1, invariants i residuals SG-REF sense PASS/FAIL numèric |
| gas/espectral | absorció no nul·la, comparació diagnòstica i revalidació del pressupost de bandes de 7.4 amb gasos/dispersió | 7.10 | B2/B4, invariants i error de discretització ≤0,01 mag o bandset nou rehomologat; el PASS/FAIL de transport és 7.12 |
| terreny/curvatura | visibilitat física, comparació diagnòstica | 7.11 | topologia i oclusió, sense PASS/FAIL de transport |
| gate zenital V1 | preregistrar tolerància abans del runtime candidat | 7.12 | origen admissible, convergència SG-REF 7.6 i PASS/FAIL runtime↔SG-REF |
| cúpules | DomeProfile des de ruta directa | 7.13 | all-sky dens + invariant zenit |
| projeccions | SQM/TESS/CIE post-kernel i revalidació de `0,01 mag` de 7.4 en aquest nou domini | 7.14 | oracles de projecció i bandset versionat si el pressupost falla |
| atmosfera real | ERA5/CAMS com providers | 7.15 | fixtures/camps parcials |
| incertesa i escenaris C | Ledger físic S, priors SPD/angular, RSR de referència com hipòtesi i incerteses explícites; H pendent de validació | 7.16 | [Política S/C/H](20-politica-rsr-i-validacio-per-dominis.md) |
| gate S i validació C/H | Gate de transport S per oracles, independent de RSR; empírica `held-out` C/H separada amb criteris preregistrats | 7.17 | oracle de S; `held-out` C/H si existeix; no PASS empíric fictici |
| compressió fonts | watershed/quadtree com backend | 7.18 | B5 vs àrea directa |
| compressió fase | Legendre com backend | 7.19 | B3 vs fase ref |
| AD/error budget | cotes conservadores | 7.20 | FD + bounds |
| cache/scheduler | reuse només dins error | 7.21 | cold/warm/movement/teleport |
| LUT/FFT opcional V1 | SLO de producte aprovats abans de decidir; manca de requisit bloqueja 7.22 | 7.22 | aprovació, plataforma, SLO congelats i directe vs accelerat |
| núvols | CloudOpticalState + B6 | 7.23 | clear limit + oracle |
| validació final | domini homologable per plataforma/producte/release/període congelat | 7.24 | clear/cloudy report i discrepàncies intersensor sense suma/SBAF per defecte |
| bridge | DTO + revisions | 7.25 | stale discard/bytes |
| renderer/debug | doble buffer lineal | 7.26 | frame/stutter/leaks |
| composició | canals lineals separats | 7.27 | reference/instantaneous |
| homologació | B7 + SLO + cap bloqueig ocult; només criteris congelats, cap llindar nou | 7.28 | informe final amb versions, dominis per font i procedència dels gates previs |
| adquisició Black Marble | un únic gestor autenticat i persistent per VNP46/VJ146/VJ246, checksum de font separat del SHA local | 24 | [pas executable](../tasques/pendent/pas24-cataleg-recursos-descarregues.md); proves de grànuls reals pendents |

**Revisió de dependències 2026-10-18:** [política S/C/H i candidat NOAA-20/RSR](20-politica-rsr-i-validacio-per-dominis.md). És un canvi prospectiu; es conserven totes les evidències de 7.1–7.5.

## Frontera amb el cel astral

El cel físic 7.51+ conserva la seva vertical. Els dos únics contractes que aquesta reordenació mou i que són consumits explícitament per la vertical astral són:
- `RadiativeErrorBudget`: ara es formalitza a **7.20**.
- `CloudOpticalState`: ara es formalitza a **7.23**.

No hi ha dependència del skyglow cap al Pas 7.65: l’oracle artificial és `SG-REF` de 7.6.
