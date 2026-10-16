# ADR-015 — Benchmark abans de congelar configuració

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Legendre, H_TOA, AD i cache tenen costos multiplicatius desconeguts. El nombre de bandes és una decisió de configuració de l'usuari, no un paràmetre a seleccionar per benchmarking.

## Decisió

B0–B7 és gate obligatori de rendiment/precisió per la configuració activa abans de fixar SLO i optimitzacions, **excloent expressament benchmarks o sweeps per triar el nombre de bandes**.

## Conseqüències

Evita optimització intuïtiva; exigeix fixtures i instrumentació primer.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Informe precisió↔cost i SLO multidimensional.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.