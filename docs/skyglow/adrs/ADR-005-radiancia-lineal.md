# ADR-005 — Radiància lineal com a moneda

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Magnitud, log i RGB no són espais additius físics.

## Decisió

Acumular totes les contribucions en radiància lineal i projectar al final.

## Conseqüències

Evita errors de suma i manté traçabilitat.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Property test de commutativitat/linealitat.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.