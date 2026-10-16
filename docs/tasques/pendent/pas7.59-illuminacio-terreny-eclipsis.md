# Pas 7.59 — Il·luminació solar/lunar del terreny, atmosfera i eclipsis

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Unificar disc, irradiància directa, llum difusa del cel, ombres i eclipsis en terreny/escena sense doble comptatge.

## Descripció funcional

Unificar disc, irradiància directa, llum difusa del cel, ombres i eclipsis en terreny/escena sense doble comptatge.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Unificar disc, irradiància directa, llum difusa del cel, ombres i eclipsis en terreny/escena sense doble comptatge.

## Dependències

**Depèn de:**
- [Pas 7.58](pas7.58-limbe-terrestre-altura.md)

**En depenen:**
- [Pas 7.60](pas7.60-integracio-three-bridge.md)

## Codi existent a reutilitzar

Pas 8.7, SceneLightingController, SolarTotalityRenderer, DEM i optical state.

## Flux tècnic

fonts físiques + visibilitat planetària/DEM + òptica → irradiància directa/difusa → escena neutral → SceneLightingController i materials.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Il·luminació físicament inconsistent entre cel, Terra i materials.
- **Rollback:** Reutilitzar el controlador simulat quan s'esculli simulated.

## Tasques

- [ ] Reutilitzar el SceneLightingController i les direccions autoritatives del Sol/Lluna.
- [ ] Distingir irradiància solar/lunar directa, difusa atmosfèrica i albedo/superfície, amb unitats.
- [ ] Fer coherent l'atenuació per eclipsi amb disc solar i scattering, inclòs el limbe vist des d'altura.
- [ ] Preservar la il·luminació històrica en mode simulat sense barrejar els dos models.
- [ ] Evitar que l'ambient artístic suplanti el càlcul físic quan physical està seleccionat.

## Criteri de sortida

Cel físic i terreny comparteixen fonts i òptica coherents; els eclipsis afecten tots els components pertinents.

## Proves i evidències obligatòries

- [ ] Alba/posta, nit lunar, eclipse parcial/total i vista elevada.
- [ ] Coherència entre color de cel, ombres, il·luminació del terreny i disc.
- [ ] Sense duplicació de component difusa ni canvi d'efemèrides.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.59/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Canviar les efemèrides o els materials de base per compensar errors atmosfèrics.

## Instrucció per a Codex

fonts físiques + visibilitat planetària/DEM + òptica → irradiància directa/difusa → escena neutral → SceneLightingController i materials. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
