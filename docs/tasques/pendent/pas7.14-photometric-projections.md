# Pas 7.14 — Skyglow físic — Projeccions fotomètriques i sensors SQM/TESS

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Projectar radiància espectral física a magnituds/instruments sense retroalimentar el kernel.

## Dependències

7.13

## Referències obligatòries

- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Implementar luminància CIE i respostes espectrals/FOV versionades de SQM/TESS.
- [ ] Implementar zero points/calibratge només des de fonts documentades.
- [ ] Comparar cada projecció contra integració espectral/focal fina.
- [ ] Propagar l’error espectral a la projecció.
- [ ] Mantenir `BortleEquivalent` com a diagnòstic versionat i mai com a ground truth.

## Criteri de sortida

SQM/TESS/CIE coincideixen amb oracles de projecció dins toleràncies preregistrades i cap projecció modifica la radiància física.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.14/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No ajustis el SourceModel ni el kernel perquè una lectura SQM concreta coincideixi.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
