# ADR-012 — Gauss–Kronrod 7/15 adaptatiu candidat

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Un nombre fix de nodes M és arbitrari i poc robust a capes/horitzó.

## Decisió

Usar GK 7/15 per segment com a candidat de benchmark, amb subdivisió adaptativa.

## Conseqüències

Control local d'error; pot ser car o enganyat per integrands adversos.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Escombrat ε_quad i reference solver.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.