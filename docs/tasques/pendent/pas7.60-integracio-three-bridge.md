# Pas 7.60 — Integració del cel físic al bridge i Three.js sense stutter

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Connectar estratègies simulat/real amb revisions, LUT dinàmiques, recursos persistents i composició del skyglow sense acoblaments indeguts.

## Descripció funcional

Connectar estratègies simulat/real amb revisions, LUT dinàmiques, recursos persistents i composició del skyglow sense acoblaments indeguts.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md) i els seus documents d'arquitectura, física, llicències i validació.
- [Normes d'arquitectura](../../normes-arquitectura.md), [inventari](../../inventari-funcional.md) i codi real del repositori.
- [Dossier skyglow artificial](../../skyglow/README.md) només per compartir estat òptic i composició; no duplicar-ne el kernel.

## Objectiu

Connectar estratègies simulat/real amb revisions, LUT dinàmiques, recursos persistents i composició del skyglow sense acoblaments indeguts.

## Dependències

**Depèn de:**
- [Pas 7.59](pas7.59-illuminacio-terreny-eclipsis.md)

**En depenen:**
- [Pas 7.61](pas7.61-validacio-cel-fisic.md)

## Codi existent a reutilitzar

ThreeSceneHostImpl, RenderLoopImpl, ResourceRegistry, frontend/bridge, contracts i DomeSkyglowRenderer.

## Flux tècnic

snapshot autoritatiu + mode + revisions → contractes/bridge → SkyRendererSelector → GPU LUT/doble buffer → skyglow separat → frame lineal.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; resultats obsolets descartats i recursos GPU amb propietari i dispose.
- Les dades o llicències no verificades es publiquen com a unavailable, mai com a resultats científics inventats.
- **Risc:** Recreació de textures per frame, resultat temporal obsolet o doble shader de cel.
- **Rollback:** Selector simulat explícit i alliberament ordenat de recursos físics.

## Tasques

- [ ] Integrar el selector dins ThreeSceneHostImpl i RenderLoopImpl, reutilitzant ordre de render, càmera i horitzó.
- [ ] Fer latest-wins a 1 s/s i scrubbing ràpid, descartant revisions obsoletes sense debounce perceptible.
- [ ] Recalcular SkyView quan canvien Sol/Lluna/altura i reutilitzar LUT atmosfèriques si les claus continuen vàlides.
- [ ] Mantenir recursos GPU amb propietari/dispose i recuperar context WebGL/bridge sense reconstruir catàlegs.
- [ ] Compondre skyglow artificial, Sol/Lluna i fons natural només en radiància compatible; errors de disponibilitat visibles.

## Criteri de sortida

El cel real es pot activar de forma estable sense degradar el camí simulat ni el runtime del skyglow.

## Proves i evidències obligatòries

- [ ] Alternança repetida simulated↔physical, desconnexió/resync i pèrdua de context GPU.
- [ ] Scrubbing ràpid, latest-wins, LUT invalidada per altura i cap integral artificial per frame.
- [ ] Frame p50/p95/p99, memòria GPU i uploads; sense stutter induït per canvis de mode.
- [ ] Evidències reproduïbles sota docs/evidencies/pas7.60/ quan s'implementi.
- [ ] Executar tools/validate_docs.py i les regressions afectades abans de completar.

## Fora d'abast

Un segon runtime o bridge científic.

## Instrucció per a Codex

snapshot autoritatiu + mode + revisions → contractes/bridge → SkyRendererSelector → GPU LUT/doble buffer → skyglow separat → frame lineal. Respectar els límits de la vertical 7.51+, les llicències comercials i el mode simulat permanent. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a completat/.
