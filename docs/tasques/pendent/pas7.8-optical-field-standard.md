# Pas 7.8 — Skyglow físic — OpticalField tiled i atmosfera estàndard determinista

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** camp òptic tiled/vertical estàndard, versionat i determinista; sense ERA5/CAMS ni scattering de 7.9.

## Descripció funcional

Donar al kernel un estat atmosfèric offline, versionat i espacialment segmentable abans de connectar reanàlisi.

## Objectiu

Substituir la partició purament geomètrica de B0 per travesses amb estat òptic i versions/dependències exactes, sense dependència de xarxa.

## Dependències

**Depèn de:**

- [Pas 7.7 — Kernel geomètric B0](../completat/pas7.7-kernel-geometry-b0.md)

**En depenen:**

- [Pas 7.9 — Rayleigh/aerosol B1](pas7.9-rayleigh-aerosol-b1.md)

## Fonts a consultar

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

Fonts locals revisades en normalitzar la dependència el 2026-10-18. Cap provider no es declara implementat per aquesta normalització.

## Codi existent a reutilitzar

- **Repositori actual:** [PropagationKernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [partició geomètrica B0](../../../backend/src/terralab3d/domain/light_pollution/geometric_transport.py), [guard de revisions](../../../backend/src/terralab3d/application/geometric_propagation.py) i [SG-REF](../../../backend/src/terralab3d/domain/light_pollution/reference_transport.py). Compartir contractes; ampliar i revalidar la referència abans de comparar medis variables.
- **Projectes externs autoritzats:** cap implementació incorporada. Verificar fonts/llicències dels models físics escollits.

## Flux tècnic

Estat atmosfèric estàndard versionat → provider darrere un port → tiles/capes i interpolació vertical → travesses segmentades del kernel → estat òptic i dependency sets exactes. La partició B0 no es pot etiquetar com a camp òptic sense dades/versions.

## Errors, cancel·lació i recursos

Rebutjar coeficients no finits, unitats/revisions incompatibles i cobertura absent; cap zero òptic fabricat com a fallback. Propagar cancel·lació i revisions de B0. Camps persistents sota propietari explícit, sense reenviament per frame. No connectar serveis externs en aquest pas.

## Tasques

- [ ] Implementar `OpticalState`, `OpticalField` i dependency sets per tiles/capes.
- [ ] Afegir un `AtmosphericOpticsProvider` estàndard versionat i determinista.
- [ ] Interpolar perfils verticals i travesses multi-tile amb cadena d’unitats explícita.
- [ ] Separar completament detalls de proveïdor del `PropagationKernel`.
- [ ] Afegir fixtures 1/2/8 tiles i proves de dependències exactes.

## Criteri de sortida

El kernel pot recórrer un camp òptic determinista i registrar exactament quins tiles/versions ha utilitzat.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.8/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

**Resultats verificats:** no executat. B0 només demostra geometria i integració unitària, no estat atmosfèric.

## Fora d'abast

ERA5/CAMS, dispersió B1, absorció gasosa detallada, DEM/curvatura física, cache/LUT, renderer i homologació empírica H.

## Instrucció per a Codex

No connectis ERA5/CAMS encara. Aquest pas existeix perquè els gates físics no depenguin de xarxa ni serveis externs.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

## Treball pendent

- [ ] Implementar les tasques, les fixtures 1/2/8 tiles i el criteri de sortida; ampliar/revalidar SG-REF per als medis nous abans dels contrasts.
