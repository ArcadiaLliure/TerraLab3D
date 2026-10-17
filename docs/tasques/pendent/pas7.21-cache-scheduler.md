# Pas 7.21 — Skyglow físic — Cache error-based, scheduler latest-wins i prefetch

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Fer interactiu el runtime sense alterar el resultat físic.

## Dependències

7.20

## Referències obligatòries

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Implementar clau de cache amb versions de font, atmosfera, terreny, bandSet i models.
- [ ] Aplicar guards topològics abans del bound d’AD/error.
- [ ] Implementar latest-wins, cancel·lació/coalescing, queue efectiva acotada i descarte de stale results.
- [ ] Implementar prefetch només si clau/envelope/error continuen vàlids en acceptació.
- [ ] Mesurar cold/warm/small-motion/moviment continu/teleport/tile-change/occlusion-flip.

## Criteri de sortida

Cap integral s’executa per frame; teleports i flips d’oclusió fan miss; small-motion només hit dins `RadiativeErrorBudget`; no hi ha stale swap.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.21/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

La cache és una optimització observable. Qualsevol hit sense prova de validesa és un bug científic.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
