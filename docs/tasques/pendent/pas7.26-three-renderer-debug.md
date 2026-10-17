# Pas 7.26 — Skyglow físic — Renderer Three.js lineal i modes diagnòstics

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Renderitzar radiància artificial lineal amb doble buffer i fer-la inspeccionable sense alterar-la.

## Dependències

7.25

## Referències obligatòries

- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [13-debug.md](../../skyglow/13-debug.md)

## Tasques

- [ ] Implementar `DomeSkyglowRenderer` retingut amb buffer inactiu→upload→swap.
- [ ] Sumar radiància lineal abans de camera/exposure/tone mapping/display transform.
- [ ] Implementar overlays/fals color de components, revisions, cache/error i provenance sense payload massiu per defecte.
- [ ] Mesurar frame p95/p99, GPU upload, stutter, leaks i context loss/resync.
- [ ] Mantenir el fallback visual legacy disponible però no com a autoritat científica.

## Criteri de sortida

El renderer mostra el camp artificial sense càlcul radiatiu per frame, descarta resultats tardans i els modes debug OFF no alteren física ni rendiment materialment.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.26/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No tornis a convertir Bortle/SQM en brillantor de shader. La dada d’entrada és radiància física.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
