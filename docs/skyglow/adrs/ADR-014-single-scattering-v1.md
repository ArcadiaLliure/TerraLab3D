# ADR-014 — Single-scattering a la v1

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Multiple scattering general és costós i el producte necessita una primera vertical mesurable.

## Decisió

La primera implementació productiva candidata és single-scattering, sense atribuir aquesta simplificació a Cinzano–Falchi.

## Conseqüències

Redueix cost; limita núvols i atmosferes òpticament gruixudes.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Comparació offline amb solver més general i ground truth.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.