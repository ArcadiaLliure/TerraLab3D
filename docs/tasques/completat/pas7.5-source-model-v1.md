# Pas 7.5 — SourceModel físic independent de VIIRS (S)

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** SourceModel S físic independent de VIIRS; extensió C separada a 7.5.1.

## Descripció funcional

Desenvolupar fonts amb SPD, emissió angular i geometria definides que es puguin simular sense una observació VIIRS. L’extensió Black Marble C relativa s’implementa prospectivament a 7.5.1; H és un contracte separat de 7.16/7.17 segons la [política S/C/H](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md).

## Fonts a consultar

- [CIE SPD de LED representatius](https://cie.co.at/datatable/relative-spectral-power-distributions-illuminants-representing-typical-led-lamps-1nm), font, escala relativa i checksum consultats el 2026-10-18; llicència i asset local al [manifest verificat](../../evidencies/pas7.4/cie-asset-manifest.json).
- [Cinzano i Falchi 2012](https://academic.oup.com/mnras/article/427/4/3337/973668), [World Atlas 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4928945/): possibles funcions angulars paramètriques, no solució de la ciutat real.
- [Model de dades](../../skyglow/06-contractes-dades.md), [oracle 7.4](pas7.4-spectral-bandset-validation.md), [auditoria històrica 7.5](../../evidencies/pas7.5/estat-inferencia-font-2026.md).

## Objectiu

Un `SourceModel` S físic, immutable, amb procedència, unitats i proves independents de SPD/normalització/potència; no un model de ciutat reconstruït de L3.

## Dependències

**Depèn de:** [7.3](pas7.3-dnb-rsr-measurement.md) i [7.4](pas7.4-spectral-bandset-validation.md); **no** depèn de RSR operativa 2026, HGS ni inversió L3→font.

**En depenen:** [Pas 7.5.1 — Black Marble i configuració](pas7.5.1-black-marble-spectral-simulation.md), [7.6 SG-REF](../pendent/pas7.6-sg-ref-reference-solver.md), [7.16 C](../pendent/pas7.16-uncertainty-provenance.md), [7.17 gates](../pendent/pas7.17-clear-sky-ground-truth.md).

## Codi existent a reutilitzar

- [SourceModel S, perfil angular i gate C/H](../../../backend/src/terralab3d/domain/light_pollution/source_model.py).
- [Oracle](../../../backend/src/terralab3d/domain/light_pollution/spectral_oracle.py), [bandset](../../../backend/src/terralab3d/domain/light_pollution/spectral_bandset.py) i [model DNB](../../../backend/src/terralab3d/domain/light_pollution/dnb_measurement.py).
- [Evidència S](../../evidencies/pas7.5/validacio-source-model-s-v1.md) i [sis RSR històriques](../../evidencies/pas7.5/auditoria-rsr-2026.json), aquestes darreres preservades com a diagnòstic C/H.

## Flux tècnic

SPD tabulada/sintètica energètica relativa → normalització integral per nm → font puntual geodèsica o rectangle uniforme al pla tangent local → patró angular axial o separable azimutal normalitzat a l'hemisferi → amplitud en W definida/mesurada o paràmetre relatiu → `SourceModel` S immutable i versionat. Els mètodes retornen flux, intensitat, exitància i, només per a l'àrea i `cosθ>0`, radiància espectrals amb unitats explícites. Aquesta sortida queda preparada com a entrada de SG-REF; el transport no s'executa a 7.5.

L’abast original d’aquest pas no implementa C/H. L’extensió prospectiva C de 7.5.1 executa: píxel Black Marble L3 i QA → hipòtesis SPD/angular amb RSR de referència explícita → normalització condicionada (7.5.1) i propagació d’incertesa (7.16) → contrast empíric per a H (7.17/7.24). **No aplicar la integral TOA directament com a inversa de L3.**

## Errors, cancel·lació i recursos

Rebutjar SPD negativa, NaN, unitats i geometria incompatibles, normals angulars degenerades, radiància negativa o amplitud sense semàntica. Escala desconeguda només en mode paramètric identificat, mai watts inventats. Mantenir llicència i checksums de les SPD. L'adquisició d'assets continua al Pas 24.

## Tasques

- [x] Gate L3/RSR i comprovacions QA/dia (treball anterior, només per C/H).
- [x] Forma angular tabulada i proves de normalització (treball anterior, no ciutat homologada).
- [x] Auditoria de sis registres RSR reals i VNP46 (resultat històric conservat).
- [x] Implementar `SourceModel` S immutable/versionat, amb `sourceMode=DEFINED_SOURCE`, geometria, amplitud, SPD, angularitat i provenance.
- [x] Definir clarament radiància superficial vs intensitat radiant vs flux espectral, relació amb àrea/angle sòlid, i tests de coherència dimensional.
- [x] Construir fixtures analítiques i adverses: fonts puntuals, àrees extenses, espectres estrets, SPD LED/mixtes, perfils angulars axials i anisòtrops.
- [x] Normalitzar angularitat amb integrals independents; cap perfil Lambert implícit.
- [x] Distingir potència mesurada/definida d'amplitud paramètrica (`absoluteCalibrationStatus`); cap potència mesurada real no s'afirma en aquest pas.
- [x] Exposar ensembles com a alternatives físiques sense pesos probabilístics ni precisió instrumental ficticis.
- [x] Assegurar que S mai exigeix RSR/L3 ni promociona cap proxy observacional a H.
- [x] Proves de conservació, regressions, Ruff/Pyright, traçabilitat i [evidències reproduïbles](../../evidencies/pas7.5/validacio-source-model-s-v1.md).

## Criteri de sortida

Hi ha un `SourceModel` S executable amb SPD, geometria, emissió angular, unitats i escala absoluta o paramètrica **declarada**; la integració i conservació es demostren amb proves independents. Es pot consumir a 7.6 sense RSR, L3 ni reconstrucció urbana. C/H manté el seu gate observacional separat i no s'ha homologat per aquest pas.

**Verificat el 2026-10-18 en el domini S declarat.** Les SPD CIE són formes representatives relatives, no fonts urbanes mesurades. La potència absoluta de la fixture és definida com a entrada; el model també permet amplitud paramètrica que no retorna watts. La revisió és prospectiva: les [evidències de l'antic bloqueig observacional](../../evidencies/pas7.5/estat-inferencia-font-2026.md) no es requalifiquen retrospectivament. Es pot preparar 7.6 sense RSR ni L3; no s'executa aquí.

## Proves i evidències obligatòries

- [x] Proves del gate parcial segons [auditoria històrica](../../evidencies/pas7.5/estat-inferencia-font-2026.md).
- [x] [Set proves noves](../../../backend/tests/test_defined_source_model_step7_5.py) del model S, unitats, espectres, potència, anisotropia, serialització i errors.
- [x] 216 proves backend; Ruff, Pyright i enllaços locals verificats. [Resultat i reproducció](../../evidencies/pas7.5/validacio-source-model-s-v1.md).
- [x] README, inventari, perfil v2, traçabilitat i dependències actualitzats segons la implementació S verificada.

## Fora d'abast

Extensió condicionada L3→font (7.5.1), incertesa propagada (7.16), validació empírica de ciutats (7.17/7.24), transport (7.6+), render, descàrregues. No eliminar infraestructura o resultats anteriors.

## Instrucció per a Codex

Implementa **exclusivament el SourceModel S**. No continuïs perseguint una RSR exacta de 2026 com a prerequisit. Quan 7.5 S passi el seu gate, mou el document a `completat/` i prepara la represa a 7.6 **sense executar-la en la mateixa sessió**.

## Treball pendent

La compatibilitat/homologació observacional C/H continua als passos 7.16–7.24; SG-REF i l'error de transport corresponen a 7.6 i posteriors. Els perfils definits no es promocionen a distribucions de ciutat mesurades.
