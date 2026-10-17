# Pas 7.2 — Skyglow físic: adaptador VNP46 d’observació, qualitat i procedència

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** ingestió de l'observació VNP46A2.002 amb qualitat, temps i procedència, sense inferència d'emissió. **Pla canònic:** [pla executable](../../skyglow/19-pla-executable-codex.md).

## Descripció funcional

No hi ha encara cap comportament nou d'usuari. Quan el pas sigui executable i complet, el sistema podrà llegir observacions Black Marble verificables; encara no mostrarà skyglow físic.

## Fonts a consultar

- [Perfil skyglow v1](../../skyglow/skyglow-v1-profile.json) i [auditoria de fonts](../../evidencies/pas7.1/auditoria-fonts.md), consultats el 2026-10-17; la política `V1` està preregistrada i els valors PASS/FAIL es fixaran als gates que els apliquin.
- [Contractes de dades](../../skyglow/06-contractes-dades.md), [datasets i llicències](../../skyglow/10-datasets-llicencies.md) i [incertesa/procedència](../../skyglow/09-incertesa-proveniencia.md), consultats el 2026-10-17.
- [Fitxa oficial VNP46A2.002](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2) i [especificació de fitxer v2.0.4](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VNP46A2_v2.0.fs), consultades el 2026-10-17; dades LAADS amb política de reutilització indicada al perfil.

## Objectiu

Ingerir la font operativa congelada a 7.1 sense confondre radiància observada amb emissió hemisfèrica. Conservar exactament la semàntica de la capa i les metadades del grànul.

## Dependències

**Depèn de:**

- [Pas 7.1 — contracte científic v1](../completat/pas7.1-contracte-cientific-v1.md), completat documentalment.

**En depenen:**

- [Pas 7.3 — model de mesura DNB i RSR](pas7.3-dnb-rsr-measurement.md).

## Codi existent a reutilitzar

- **Repositori actual:** [ports de contaminació lumínica](../../../backend/src/terralab3d/domain/light_pollution/) per a la frontera del domini i [infraestructura de recursos](../../../backend/src/terralab3d/infrastructure/resources/) per separar adquisició i interpretació. No hi ha un adaptador VNP46 verificat.
- **Projectes de referència autoritzats:** cap codi extern incorporat; especificacions NASA com a font de dades i semàntica.

## Flux tècnic

Grànul HDF5 `VNP46A2.002` → validació de producte, col·lecció, capa, atributs i checksum → preservació de valor cru, unitat, temps, georeferència i flags → `Vnp46Observation` immutable serialitzable. El perfil v1 defineix dia exacte, capa sense gap-fill, QA candidata 0 i tractament `LOW-RAD`. Descàrrega/cache i interpretació científica són responsabilitats separades.

## Errors, cancel·lació i recursos

Si falta el dia, la qualitat o una metadada obligatòria, el resultat és indisponible o en quarantena amb causa; no s'imputa cap dada. Un valor negatiu o fill es conserva cru i queda fora de la inferència; no hi ha clipping. Evitar correccions duplicades de stray light. Les descàrregues i la lectura HDF5 han de poder interrompre's i alliberar fitxers oberts; cap recurs GPU.

## Tasques

- [ ] Implementar `Vnp46Observation` immutable amb producte, release, data, unitat, georeferència, quality/nodata i provenance.
- [ ] Aplicar exactament la política temporal i `LOW-RAD` del manifest v1; conservar valors negatius o dubtosos segons la política, mai amb `max(0,·)` implícit.
- [ ] Evitar doble correcció de stray light o altres correccions ja incorporades pel producte/release.
- [ ] Afegir fixtures reproduïbles de radiància alta, baixa, negativa, nodata, quality degradada i frontera temporal 2017.
- [ ] Separar descàrrega/cache de dades de la interpretació científica.

## Criteri de sortida

Un fixture VNP46 es pot llegir i serialitzar preservant unitats, quality, temps i provenance; cap transformació converteix encara l'observació en SPD o emissió angular. El gate documental de 7.1 ja està completat.

## Proves i evidències obligatòries

- [ ] Proves unitàries, golden i property rellevants en verd, inclosos els casos de QA, fill, zero i frontera 2017.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.2/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable i sense marcar passos posteriors prematurament.

**Resultats verificats:** 7.1 completat documentalment; les tasques d'implementació i proves d'aquest Pas 7.2 no s'han executat.

## Fora d'abast

Inferència `SourceModel`, normalització espectral DNB/RSR, propagació i visualització del skyglow.

## Instrucció per a Codex

Llegeix el manifest complet, verifica un grànul real i implementa només la sortida d'observació. Qualsevol ambigüitat del producte torna al contracte de 7.1; no la resolguis localment. Si no es pot demostrar el criteri de sortida, mantén aquest pas a `pendent/` i no continuïs a 7.3.

## Treball pendent

- [ ] Verificar el grànul de referència contra el perfil de dades i la política V1 preregistrada.
- [ ] Completar les tasques, proves i evidències abans de moure el pas a `completat/`.
