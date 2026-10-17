# Pas 7.25 — Skyglow físic — Bridge Python→TypeScript i SkyglowRuntime

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Transportar resultats físics ja homologats sense portar integració radiativa al frontend.

## Dependències

7.24

## Referències obligatòries

- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

## Tasques

- [ ] Definir DTO versionat per `PropagationResultSummary`/`DomeProfile`, bandSetId, unitats, revisions i provenance compacta.
- [ ] Implementar `SkyglowRuntime` amb requested/accepted revision, double-buffer de presentació i stale discard.
- [ ] Compartir golden tests de PCHIP si la reconstrucció es fa a TypeScript.
- [ ] Mesurar bytes de bridge, latència i upload preparatori.
- [ ] Prohibir nodes de quadratura, rasters massius i integrals del kernel al render loop.

## Criteri de sortida

TypeScript pot rebre/validar/swap resultats de skyglow amb revisió monotònica i sense executar física de propagació.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.25/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

El frontend transporta i presenta. Si necessites física nova per dibuixar, torna al backend.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
