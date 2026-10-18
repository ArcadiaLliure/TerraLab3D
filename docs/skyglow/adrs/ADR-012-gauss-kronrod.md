# ADR-012 — Gauss–Kronrod 7/15 adaptatiu candidat

- **Estat:** Acceptada — implementada per a B0; validació radiomètrica pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Un nombre fix de nodes M és arbitrari i poc robust a capes/horitzó.

## Decisió

Usar GK 7/15 per segment com a candidat de benchmark, amb subdivisió adaptativa.

## Conseqüències

Control local d'error; pot ser car o enganyat per integrands adversos.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Escombrat ε_quad i reference solver.

## Estat d'implementació

El [Pas 7.7](../../tasques/completat/pas7.7-kernel-geometry-b0.md) implementa GK7/15 propi i el contrasta amb antiderivades de polinomis/exponencial i discontinuïtats segmentades. B0 usa l’integrand 1, comptadors reproduïbles i pressupost global sobre segments. L’error estimat inclou un sòl d’arrodoniment; no és una cota rigorosa. El contrast radiomètric amb SG-REF queda pendent als passos físics i 7.12. [Evidències](../../evidencies/pas7.7/validacio-b0.md).