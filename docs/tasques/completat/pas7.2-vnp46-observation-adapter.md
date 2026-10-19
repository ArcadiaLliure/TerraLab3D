# Pas 7.2 — Skyglow físic: adaptador VNP46 d’observació, qualitat i procedència

> **Estat:** completat. **Estat funcional:** lector local i CLI verificats amb fixtures i un grànul real de la col·lecció 2, sense integració de producte. **Origen:** planificat. **Abast vigent:** ingestió de l'observació VNP46A2.002 amb qualitat, temps i procedència, sense inferència d'emissió. **Pla canònic:** [pla executable](../../skyglow/19-pla-executable-codex.md).

## Descripció funcional

No hi ha encara cap comportament nou d'usuari. El lector local i l'eina de diagnòstic llegeixen mostres HDF5 amb SHA-256 esperat i retornen observacions serialitzables; s'han contrastat amb fixtures sintètiques i un grànul VNP46A2.002 real. Encara no es mostra skyglow físic.

## Fonts a consultar

- [Perfil skyglow v1](../../skyglow/skyglow-v1-profile.json) i [auditoria de fonts](../../evidencies/pas7.1/auditoria-fonts.md), consultats el 2026-10-17; la política `V1` està preregistrada i els valors PASS/FAIL es fixaran als gates que els apliquin.
- [Contractes de dades](../../skyglow/06-contractes-dades.md), [datasets i llicències](../../skyglow/10-datasets-llicencies.md) i [incertesa/procedència](../../skyglow/09-incertesa-proveniencia.md), consultats el 2026-10-17.
- [Fitxa oficial VNP46A2.002](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2) i [especificació de fitxer v2.0.4](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VNP46A2_v2.0.fs), consultades el 2026-10-17; dades LAADS amb política de reutilització indicada al perfil.
- [Metadades OPeNDAP d'un grànul Collection 2 real](https://ladsweb.modaps.eosdis.nasa.gov/opendap/RemoteResources/laads/allData/5200/VNP46A2/2022/050/VNP46A2.A2022050.h26v03.002.2025116070200.h5.html), consultades el 2026-10-17; confirmen camins HDF-EOS5 i atributs. El grànul binari de contrast ha estat aportat localment per l'usuari; l'URL exacte de descàrrega no s'ha verificat.
- [h5py, repositori oficial](https://github.com/h5py/h5py), consultat el 2026-10-17; interfície HDF5 BSD-3-Clause, versió 3.16.0 instal·lada per a les proves.

## Objectiu

Ingerir la font operativa congelada a 7.1 sense confondre radiància observada amb emissió hemisfèrica. Conservar exactament la semàntica de la capa i les metadades del grànul.

## Dependències

**Depèn de:**

- [Pas 7.1 — contracte científic v1](pas7.1-contracte-cientific-v1.md), completat documentalment.

**En depenen:**

- [Pas 7.3 — model de mesura DNB i RSR](pas7.3-dnb-rsr-measurement.md).

## Codi existent a reutilitzar

- **Repositori actual:** [model immutable](../../../backend/src/terralab3d/domain/light_pollution/vnp46.py), [port d'observació](../../../backend/src/terralab3d/application/ports/vnp46_observations.py), [lector HDF-EOS5](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/vnp46.py), [eina de diagnòstic](../../../tools/inspect_vnp46_granule.py) i [infraestructura de recursos](../../../backend/src/terralab3d/infrastructure/resources/) separada de la interpretació. L'adaptador s'ha verificat amb fixtures i un grànul real.
- **Projectes de referència autoritzats:** cap codi extern incorporat; especificacions NASA com a font de dades i semàntica.

## Flux tècnic

Grànul HDF5 `VNP46A2.002` → validació de producte, col·lecció, capa, atributs i checksum → preservació de valor cru, unitat, temps, georeferència i flags → `Vnp46Observation` immutable serialitzable. El perfil v1 defineix dia exacte, capa sense gap-fill, QA candidata 0 i tractament `LOW-RAD`. Descàrrega/cache i interpretació científica són responsabilitats separades.

## Errors, cancel·lació i recursos

Si falta el dia, la qualitat o una metadada obligatòria, el resultat és indisponible o en quarantena amb causa; no s'imputa cap dada. Un valor negatiu o fill es conserva cru i queda fora de la inferència; no hi ha clipping. El lector no aplica correccions de stray light ni cap altra correcció de radiància. La descàrrega queda fora del lector; el càlcul SHA-256 i la lectura de finestres accepten cancel·lació cooperativa i el context HDF5 tanca el fitxer en sortir. Cap recurs GPU.

## Tasques

- [x] Implementar `Vnp46Observation` immutable amb producte, release, data, unitat, georeferència, quality/nodata i provenance.
- [x] Aplicar la política temporal i `LOW-RAD` del manifest v1; conservar valors negatius o dubtosos, sense `max(0,·)` implícit.
- [x] Evitar doble correcció de stray light o altres correccions ja incorporades: el lector no les aplica.
- [x] Afegir fixtures reproduïbles de radiància alta, baixa, negativa, nodata, quality degradada i frontera temporal 2017.
- [x] Separar descàrrega/cache de dades de la interpretació científica.
- [x] Contrastar un grànul binari `VNP46A2.002` real amb el perfil i el lector; registrar procedència local, SHA-256, metadades, mostres i resultat. L'URL de descàrrega i un checksum publicat pel proveïdor no consten com a verificats.

## Criteri de sortida

El fixture VNP46 i un grànul real es llegeixen i serialitzen preservant unitats, quality, temps i provenance; cap transformació converteix l'observació en SPD o emissió angular. S'ha contrastat una mostra de diagnòstic i una fill del grànul aportat; aquest tile no conté QA 0, que queda coberta per les fixtures. El gate documental de 7.1 ja està completat.

## Proves i evidències obligatòries

- [x] Proves unitàries, golden i de propietats rellevants en verd, inclosos QA, fill, zero i frontera 2017.
- [x] Regressions del backend afectades en verd.
- [x] [Evidència reproduïble](../../evidencies/pas7.2/validacio-adaptador.md) sota `docs/evidencies/pas7.2/`, inclòs el contrast real i les seves limitacions.
- [x] README/inventari/estat actualitzats només segons el comportament comprovat, sense marcar passos posteriors prematurament.

**Resultats verificats:** 9 proves específiques i 186 proves de backend en verd el 2026-10-17; Ruff i Pyright sense errors. El lector ha obert el grànul real aportat per l'usuari, traslladat a `resolve_data_root()/data/earth/light-pollution/vnp46a2/2026/256/`, i n'ha llegit les dues mostres documentades a l'evidència.

## Fora d'abast

Inferència `SourceModel`, normalització espectral DNB/RSR, propagació i visualització del skyglow.

## Instrucció per a Codex

El [Pas 7.3](pas7.3-dnb-rsr-measurement.md) ha completat el contracte de mesura i la interpretació L3; [7.4](pas7.4-spectral-bandset-validation.md) ha homologat l'operador espectral tabulat, [7.5](pas7.5-source-model-v1.md) ha verificat una font definida S independent i [7.6](pas7.6-sg-ref-reference-solver.md) verifica el transport offline en el domini pla homogeni S/C. 7.7 verifica B0 geomètric i [7.8](pas7.8-optical-field-standard.md) el camp estàndard/columnes; [7.9](pas7.9-rayleigh-aerosol-b1.md) verifica B1 monocromàtic i el punt de represa actual és [7.10](../completat/pas7.10-gas-spectral-kernel.md). Es conserva la distinció entre radiància observada i inferència d'emissió. Qualsevol ambigüitat del producte torna al contracte de 7.1.

## Treball pendent

Cap tasca pendent del Pas 7.2. El Pas 7.3 ha validat l'operador DNB i ha etiquetat `Vnp46Observation` com a radiància Black Marble L3 corregida, sense reinterpretar-la com a imatge ni emissió espectral/angular. En la gestió posterior de recursos, un checksum publicat o URL de descàrrega verificat permetria autenticar independentment l'origen del grànul local; el SHA-256 actual només acredita la identitat dels bytes traslladats.
