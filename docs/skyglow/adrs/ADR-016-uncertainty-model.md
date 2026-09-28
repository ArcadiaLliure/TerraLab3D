# ADR-016 — Separar incertesa de predicció i de validesa de cache

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Un error absolut sistemàtic no implica que un resultat cachejat hagi canviat.

## Decisió

Dos contractes: `PredictionUncertainty` i `CacheValidityUncertainty`.

## Conseqüències

Evita misses inútils i conserva rigor estadístic.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Tests amb calibratge sistemàtic constant i atmosfera canviant.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.