# Pas 7.8 — Skyglow físic — OpticalField tiled i atmosfera estàndard determinista

> **Estat:** completat. **Estat funcional:** observable. **Origen:** planificat. **Abast vigent:** camp òptic tiled/vertical estàndard, versionat i determinista; sense ERA5/CAMS ni scattering de 7.9.

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

Fonts locals revisades i implementació contrastada el 2026-10-19. Fonts primàries: [COESA 1975, NASA TR R-459 (1976)](https://ntrs.nasa.gov/api/citations/19760017709/downloads/19760017709.pdf), constants/taula 3/hidrostàtica d’aire sec 0–50 km, i [NIST kB SI exacte](https://physics.nist.gov/cgi-bin/cuu/Value?k%7Csearch_for=Boltzmann). Consultades; equacions i constants implementades, sense codi extern incorporat. [Resultats, fonts i límits](../../evidencies/pas7.8/validacio-optical-field.md).

## Codi existent a reutilitzar

- **Repositori actual:** [PropagationKernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [partició geomètrica B0](../../../backend/src/terralab3d/domain/light_pollution/geometric_transport.py), [guard de revisions](../../../backend/src/terralab3d/application/geometric_propagation.py) i [SG-REF](../../../backend/src/terralab3d/domain/light_pollution/reference_transport.py). Compartir contractes. L’oracle de columnes [GK21 independent](../../../backend/src/terralab3d/domain/light_pollution/reference_optical_column.py) revalida el domini variable de P/T/n; el transport radiomètric homogeni de 7.6 no es modifica.
- **Projectes externs autoritzats:** cap implementació incorporada. Verificar fonts/llicències dels models físics escollits.

## Flux tècnic

`OpticalFieldRequest` (origen fix, instant amb zona, bounds ENU/versions, sostre i pas vertical) → `StandardAtmosphericOpticsProvider` darrere el [port](../../../backend/src/terralab3d/application/ports/atmospheric_optics.py) → perfils P(Pa)/T(K), log(P)/T lineals → [OpticalField](../../../backend/src/terralab3d/domain/light_pollution/optical_field.py) immutable i travessa per cares/nusos → `OpticalState` amb n=P/(kBT) en m⁻³ i procedència per camp → columna diagnòstica en m⁻² i dependències exactes per LOS.

Provider `coesa1975-nasa-tr459-dry-0-50km-v1`; camp `optical-field-tabulated-v1`. Tiles semioberts en ENU fix del camp, altura radial esfèrica, sense extrapolació. La signatura completa inclou totes les entrades; la signatura utilitzada només les capes mostrejades més origen/radi/instant/revisió. Amb camp, resultat esquema 2 diagnòstic; sense camp, B0 conserva esquema 1. Coeficients de dispersió/absorció i núvols absents, mai zeros inventats. La partició geomètrica B0 continua separada.

## Errors, cancel·lació i recursos

Rebutjar coeficients no finits, unitats/revisions incompatibles i cobertura absent; cap zero òptic fabricat com a fallback. Propagar cancel·lació i revisions de B0. Camps immutables sota propietat del consumidor, sense reenviament per frame; pressupost de 4.096 nusos i límit de segments. Els buits positius de cobertura es rebutgen. Prova amb fil real de descart d’un camp/revisió substituït; l’oracle també admet cancel·lació. No connectar serveis externs en aquest pas.

## Tasques

- [x] Implementar `OpticalState`, `OpticalField` i dependency sets per tiles/capes.
- [x] Afegir un `AtmosphericOpticsProvider` estàndard versionat i determinista.
- [x] Interpolar perfils verticals i travesses multi-tile amb cadena d’unitats explícita.
- [x] Separar completament detalls de proveïdor del `PropagationKernel`.
- [x] Afegir fixtures 1/2/8 tiles i proves de dependències exactes.

## Criteri de sortida

El kernel pot recórrer un camp òptic determinista i registrar exactament quins tiles/versions ha utilitzat.

## Proves i evidències obligatòries

- [x] Proves unitàries/golden/property rellevants en verd.
- [x] Regressions afectades en verd.
- [x] Evidència reproduïble sota `docs/evidencies/pas7.8/`.
- [x] README/inventari/estat actualitzats només segons comportament observable.
- [x] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

**Resultats verificats (2026-10-19):** 33 proves noves i 363 proves backend superades; Ruff/Pyright dels fitxers afectats sense incidències. Pyright global conserva 67 errors/3 avisos previs. Fixtures 1/2/8 tiles i contrast lateral prescrit: diferència relativa màxima de columna vs GK21 5,56·10⁻¹⁶. Convergència d’interpolació registrada; regressió B0 principal 900 LOS amb signatura idèntica. [Informe reproduïble](../../evidencies/pas7.8/validacio-optical-field.md), [protocol](../../evidencies/pas7.8/protocol-optical-field-v1.json), [resultats](../../evidencies/pas7.8/resultats-optical-field-v1.json) i [proves](../../evidencies/pas7.8/proves-backend.txt). Camp/columnes implementats; cap radiància ni gate H anticipats.

## Fora d'abast

ERA5/CAMS, dispersió B1, absorció gasosa detallada, DEM/curvatura física, cache/LUT, renderer i homologació empírica H.

## Instrucció per a Codex

No connectis ERA5/CAMS encara. Aquest pas existeix perquè els gates físics no depenguin de xarxa ni serveis externs.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

## Treball pendent

Cap dins d’aquest pas. [7.9](pas7.9-rayleigh-aerosol-b1.md) introduirà dispersió i haurà d’ampliar/revalidar SG-REF per al domini radiomètric corresponent. No s’ha executat aquí.
