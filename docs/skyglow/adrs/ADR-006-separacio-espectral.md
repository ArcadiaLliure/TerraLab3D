# ADR-006 — Separar NormalizationSpectrum i PropagationBandSet

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

La RSR DNB exigeix resolució diferent de la propagació runtime.

## Decisió

Normalització amb espectre fi; propagació amb band set versionat i `spectralBandCount` configurable, amb límits/ponderacions explícits i invalidació de caches. Cap N fix.

## Conseqüències

Permet canviar nombre de bandes sense API incompatible.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Proves de coherència espectral, dimensions, unitats i respostes instrumentals amb la configuració activa. No s'executen benchmarks ni sweeps per determinar el nombre de bandes.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.