# Pas 7.14 — Skyglow físic — Projeccions fotomètriques i sensors SQM/TESS

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Projectar radiància espectral física a magnituds/instruments sense retroalimentar el kernel.

## Dependències

[Pas 7.13 — perfils de cúpula](pas7.13-dome-profile-direct.md) i [Pas 7.4 — bandset tabulat v1](../completat/pas7.4-spectral-bandset-validation.md). Les noves respostes fotomètriques requereixen revalidació espectral pròpia.

## Referències obligatòries

- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Implementar luminància CIE i respostes espectrals/FOV versionades de SQM/TESS.
- [ ] Implementar zero points/calibratge només des de fonts documentades.
- [ ] Comparar cada projecció contra integració espectral/focal fina.
- [ ] Propagar l’error espectral a la projecció.
- [ ] Revalidar el pressupost de discretització `0,01 mag` de [7.4](../../evidencies/pas7.4/criteri-preregistrat-v1.json) sobre les respostes SQM/TESS/CIE realment implementades. Si falla, versionar i rehomologar el `SpectralBandSet`, sense relaxació retroactiva.
- [ ] Justificar i preregistrar qualsevol tolerància de projecció pròpia abans de comparar el candidat amb l'oracle, amb incertesa de resposta/FOV i error espectral pertinents.
- [ ] Mantenir `BortleEquivalent` com a diagnòstic versionat i mai com a ground truth.

## Criteri de sortida

SQM/TESS/CIE coincideixen amb oracles de projecció dins toleràncies justificades i preregistrades a 7.14 abans de la comparació decisòria; sense aquestes toleràncies, 7.14 es bloqueja. La discretització també compleix el criteri heretat de 7.4 en aquest domini nou o el bandset es versiona i rehomologa. Cap projecció modifica la radiància física.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.14/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No ajustis el SourceModel ni el kernel perquè una lectura SQM concreta coincideixi.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
