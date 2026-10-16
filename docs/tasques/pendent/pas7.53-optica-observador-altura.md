# Pas 7.53 — Estat òptic compartit, geodèsia i altura de l'observador

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Construir un estat òptic autoritatiu reutilitzable per transport astral i skyglow, amb geodèsia i altitud coherent fins a fora de l'atmosfera.

## Descripció funcional

Construir un estat òptic autoritatiu reutilitzable per transport astral i skyglow, amb geodèsia i altitud coherent fins a fora de l'atmosfera.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Construir un estat òptic autoritatiu reutilitzable per transport astral i skyglow, amb geodèsia i altitud coherent fins a fora de l'atmosfera.

## Dependències

**Depèn de:**
- [Pas 7.52](pas7.52-selector-cel-simulat-real.md)

**En depenen:**
- [Pas 7.54](pas7.54-font-solar-espectral.md)

## Codi existent a reutilitzar

domain/atmosphere, domain/horizon, domain/terrain, escena neutral i providers existents.

## Flux tècnic

posició WGS84 + altitud/datum + temps + providers òptics → AtmosphericOpticsState immutable → revisió → deltes/diagnòstic → solvers consumidors.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Confondre alçada sobre DEM amb altura geodèsica i perdre precisió en grans distàncies.
- **Rollback:** Mantenir mode simulat i marcar el provider unavailable.

## Tasques

- [ ] Reutilitzar els dominis atmosphere, terrain i horizon; declarar datum, altitud ellipsoidal/ortomètrica, ECEF/ENU i alçada relativa al terreny.
- [ ] Resoldre perfils de densitat, Rayleigh, aerosols, ozó/gasos i disponibilitat de núvols amb unitats i procedència.
- [ ] Definir radi terrestre/atmosfèric i conversió local per al solver esfèric, amb limitacions davant l'el·lipsoide/DEM.
- [ ] Versionar i invalidar el camp quan canvia altitud, ubicació, temps o propietats òptiques; exposar diagnòstic observable.
- [ ] No acoblar l'estat compartit al PropagationKernel ni al shader simulat.

## Criteri de sortida

L'estat òptic i geomètric és coherent, versionat i observable per altituds diferents.

## Proves i evidències obligatòries

- [ ] Observador a superfície, muntanya, avió, estratosfera i òrbita; valors físics i geometria finits.
- [ ] Canvi d'altura invalida només dependències òptiques/geodèsiques afectades; cap recomputació estel·lar.
- [ ] Transició dins/fora de l'atmosfera amb datum coherent i procedència.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.53/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Transport radiatiu i llum solar/lunar encara no resolts.

## Instrucció per a Codex

posició WGS84 + altitud/datum + temps + providers òptics → AtmosphericOpticsState immutable → revisió → deltes/diagnòstic → solvers consumidors. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
