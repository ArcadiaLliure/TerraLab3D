# ADR-006 — Separar NormalizationSpectrum i PropagationBandSet

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

La RSR DNB exigeix resolució diferent de la propagació runtime.

## Decisió

Normalització amb espectre fi; propagació amb band set versionat.

## Conseqüències

Permet canviar nombre de bandes sense API incompatible.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Benchmark espectral 4/6/8/10/12 bandes.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.