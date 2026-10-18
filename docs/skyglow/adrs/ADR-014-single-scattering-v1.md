# ADR-014 — Single-scattering a la v1

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Multiple scattering general és costós i el producte necessita una primera vertical mesurable.

## Decisió

La primera implementació productiva candidata és single-scattering, sense atribuir aquesta simplificació a Cinzano–Falchi.

## Conseqüències

Redueix cost; introdueix un error estructural que s'ha de quantificar per escenari i incorporar a `PredictionUncertainty.modelStructural`.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

El [Pas 7.6](../../tasques/completat/pas7.6-sg-ref-reference-solver.md) implementa l’alternativa pròpia: Monte Carlo invers escalar independent, amb totes les ordres fins al truncament explícit i cota de cua. Nou benchmarks plans homogenis quantifiquen F5 amb errors mostrals. No depèn del Pas 7.65 ni acredita una cota universal urbana; els nous dominis s’han de revalidar. [Evidències](../../evidencies/pas7.6/validacio-sg-ref.md).

## Estat d'implementació

Referència i contrast F5 offline implementats a 7.6 en el domini declarat. La implementació productiva candidata i la propagació d’incertesa estructural continuen pendents als passos runtime i 7.16.