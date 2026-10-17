# Pas 7.11 — Skyglow físic — Terreny, curvatura i visibilitat física

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Afegir l’oclusió i la geometria terrestre a la ruta directa abans del gate zenital.

## Dependències

7.10

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)

## Tasques

- [ ] Integrar DEM/geodèsia autoritatius per visibilitat source→P i truncament observer→sky.
- [ ] Implementar curvatura terrestre coherent amb ECEF/ENU.
- [ ] Representar visibilitat física binària o geomètricament justificada, sense transparències arbitràries.
- [ ] Crear fixtures de muntanya, font parcial, font llunyana i discontinuïtat d’oclusió.
- [ ] Comparar contra SG-REF amb les mateixes dades de terreny.

## Criteri de sortida

Els casos sintètics de terreny/curvatura verifiquen topologia i oclusió, documenten la comparació diagnòstica amb SG-REF i detecten els flips com a discontinuïtats. El primer PASS/FAIL numèric de transport és 7.12.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.11/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No introdueixis encara reuse per moviment. Primer fes correcta la topologia.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
