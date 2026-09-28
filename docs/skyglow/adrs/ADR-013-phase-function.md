# ADR-013 — PhaseFunction unificada

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Branques runtime Mie/HG/taules compliquen kernel i cache.

## Decisió

Convertir models a una representació comuna, preferentment Legendre; HG és fallback.

## Conseqüències

Kernel simple; cal triar ordre per error↔cost.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

B3 HG/L4/L8/L12/L20.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.