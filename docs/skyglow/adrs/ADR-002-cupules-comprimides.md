# ADR-002 — Cúpules comprimides en lloc d'all-sky runtime

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Un all-sky dens per cada moviment és massa costós com a hipòtesi inicial.

## Decisió

Mostrejar poques elevacions per font i validar la reconstrucció contra solver all-sky.

## Conseqüències

Redueix volum de càlcul/render; introdueix error de compressió mesurable.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Pla all-sky amb MAE, P95 Δm, energia, pic i amplada.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.