# ADR-014 — Single-scattering a la v1

- **Estat:** Acceptada — B1 monocromàtic implementat; espectre i producte pendents
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

Referència i contrast F5 offline implementats a 7.6 en el domini declarat. [7.9](../../tasques/completat/pas7.9-rayleigh-aerosol-b1.md) implementa dispersió simple monocromàtica en el mateix kernel amb dos trajectes, dependències i àrea directa. [B1 i referència revalidada](../../evidencies/pas7.9/validacio-b1.md). Espectre/gasos, producte connectat i incertesa estructural continuen als passos 7.10, 7.25–7.27 i 7.16; F5 no es promou a cota universal per al domini nou.

## Extensió espectral verificada a 7.10

Mateix operador directe S/C, amb columnes compartides entre λ i O3 prescrit offline; pressupost 0,01 mag revalidat, SG-REF refinat i sensibilitat 10–50 km mesurada. No homologa aire terrestre complet ni altres absorbidors. El gate radiomètric continua a 7.12 i no s'ha executat 7.11. [Resultats](../../evidencies/pas7.10/validacio-espectral-i-gasos.md).
