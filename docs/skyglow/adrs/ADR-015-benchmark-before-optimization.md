# ADR-015 — Benchmark abans de congelar configuració

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Bandes, Legendre, H_TOA, AD i cache tenen costos multiplicatius desconeguts.

## Decisió

B0–B7 és gate obligatori abans de fixar configuració de producció.

## Conseqüències

Evita optimització intuïtiva; exigeix fixtures i instrumentació primer.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Informe precisió↔cost i SLO multidimensional.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.