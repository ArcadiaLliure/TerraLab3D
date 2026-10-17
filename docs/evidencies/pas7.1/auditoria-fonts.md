# Auditoria de fonts del contracte skyglow v1 (2026-10-17)

## Fonts primàries consultades

| Font | Verificació | Conseqüència per al perfil |
|---|---|---|
| [Fitxa LAADS de VNP46A2 Collection 2](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2) | Consultada el 2026-10-17. Confirma producte diari, Collection 2, ArchiveSet 5200, nou format de radiància float i QA 0–5. | `VNP46A2.002` en processament estàndard. |
| [Guia Black Marble Collection 2, taules 8–10 i apèndix B](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf) | Consultada el 2026-10-17. Documenta `DNB_BRDF-Corrected_NTL`, unitat `nW cm⁻² sr⁻¹`, rang vàlid no negatiu, fill `-999.9`, QA 0 com a qualitat alta, 1–5 degradats i 255 sense recuperació. | Capa principal sense ompliment de buits; flags degradats només diagnòstics; valor cru preservat. |
| [Especificació LAADS VNP46A2 v2.0.4](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VNP46A2_v2.0.fs) | Consultada el 2026-10-17. Confirma atributs de grànul i de capa. | Validar `LocalGranuleID`, versió de procés, data, unitat, fill, escala i offset de cada grànul. |
| [Política de dades LAADS](https://ladsweb.modaps.eosdis.nasa.gov/learn) | Consultada el 2026-10-17. Autoritza reutilització i redistribució de productes LAADS i demana citació. | Es pot consumir/redistribuir amb citació i procedència; no s'ha descarregat cap grànul. |
| [Coesfeld et al. 2020](https://doi.org/10.3390/s20113287) | Consultat el 2026-10-17. Analitza variabilitat del punt zero en una sèrie VIIRS DNB i correcció del seu processament. | No traslladar cap correcció numèrica universal a VNP46A2 Collection 2. Comparacions febles pre/post-2017 continuen no validades. |

## Inconsistències i límits detectats

- L'extracció textual de la taula 8 concatena l'offset `0.0` amb el número de pàgina `16`; l'apèndix B i l'especificació v2.0.4 també indiquen `0`. Igualment, l'adaptador llegirà l'atribut del grànul i posarà en quarantena les incompatibilitats; no fixarà un offset implícit.
- L'especificació v2.0.4 escriu `valid_range = 0 - 3` per a `Mandatory_Quality_Flag`, però la seva descripció i la guia enumeren 0–5. El descodificador ha de conservar el valor cru i emprar la taula descriptiva 0–5; 0 és l'únic candidat del perfil actual.
- NASA publica objectius de detecció i robustesa de *VNP46* a la taula 14 de la guia. Aquests no són llindars d'error del solver TerraLab3D, de discretització espectral, de latència ni de freqüència de recomputació. No els reutilitzem com a PASS/FAIL del projecte.
- No s'ha descarregat cap grànul ni verificat un checksum de dades. El perfil defineix el contracte previst; l'adaptador i les fixtures reals continuen pendents del pas 7.2.

## Decisió de gate

**Registre de la revisió inicial:** `skyglow-v1-profile.json` era llegible i versionat, però `acceptanceProfile.status=unresolved`; amb el criteri de sortida inicial, 7.1 es considerava bloquejat. No s'havia fet cap benchmark ni cap inferència d'emissió.

**Reavaluació del 2026-10-17:** el [pla executable](../../skyglow/19-pla-executable-codex.md) corregeix la seqüència: 7.1 congela la política d'acceptació, no els valors que depenen d'evidència posterior. El perfil té ara `acceptanceProfile.status=policy_preregistered`. `DATA-VNP46`, `LOW-RAD`, `DNB-2017`, `S1`, `F5`, `F7` i l'abast `F6` són suficients per iniciar 7.2 i 7.3. 7.1 queda completat documentalment; no s'ha fet cap benchmark, lectura de grànul ni inferència d'emissió. Els valors PASS/FAIL es preregistraran al primer gate que els utilitzi.
