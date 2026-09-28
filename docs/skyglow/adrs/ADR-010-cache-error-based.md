# ADR-010 — Cache basada en error de canvi

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Llindars de metres/graus no tenen significat radiomètric universal.

## Decisió

Comprovar discontinuïtats primer i després estimar `ΔB` contra pressupost.

## Conseqüències

Més robust; necessita sensibilitats/bounds.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Matriu hit/miss incloent flip d'oclusió.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.