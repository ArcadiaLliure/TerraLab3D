# ADR-013 — PhaseFunction unificada

- **Estat:** Acceptada — interfície i referències B1 implementades; Legendre/B3 pendents
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

[7.9](../../tasques/completat/pas7.9-rayleigh-aerosol-b1.md) implementa fase comuna amb densitat normalitzada 4π, Rayleigh amb despolarització, isòtropa, HG explícit de fallback i taula de referència. [Invariants, refinament i B1](../../evidencies/pas7.9/validacio-b1.md). Legendre/compressió i B3 continuen a 7.19.