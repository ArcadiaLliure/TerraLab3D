# Pas 7.8 — Skyglow físic — OpticalField tiled i atmosfera estàndard determinista

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Donar al kernel un estat atmosfèric offline, versionat i espacialment segmentable abans de connectar reanàlisi.

## Dependències

7.7

## Referències obligatòries

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

## Tasques

- [ ] Implementar `OpticalState`, `OpticalField` i dependency sets per tiles/capes.
- [ ] Afegir un `AtmosphericOpticsProvider` estàndard versionat i determinista.
- [ ] Interpolar perfils verticals i travesses multi-tile amb cadena d’unitats explícita.
- [ ] Separar completament detalls de proveïdor del `PropagationKernel`.
- [ ] Afegir fixtures 1/2/8 tiles i proves de dependències exactes.

## Criteri de sortida

El kernel pot recórrer un camp òptic determinista i registrar exactament quins tiles/versions ha utilitzat.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.8/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No connectis ERA5/CAMS encara. Aquest pas existeix perquè els gates físics no depenguin de xarxa ni serveis externs.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
