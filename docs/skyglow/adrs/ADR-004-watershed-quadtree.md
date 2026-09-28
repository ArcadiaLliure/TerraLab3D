# ADR-004 — Watershed + quadtree intern

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Municipis/radis no defineixen fonts radiomètriques i un píxel per font és massa car.

## Decisió

Watershed defineix `EmissionRegion`; quadtree adaptatiu només dins la regió.

## Conseqüències

Separa identitat de font de resolució interna.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Fixtures amb conques, ponts febles i oclusió parcial.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.