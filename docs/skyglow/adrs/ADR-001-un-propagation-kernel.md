# ADR-001 — Un únic PropagationKernel

- **Estat:** Accepted for implementation
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Zenit i cúpules podrien divergir si es modelen per separat.

## Decisió

Tota radiància artificial direccional s'obté del mateix `PropagationKernel`; el zenit és una direcció més.

## Conseqüències

Evita doble física i facilita validació. Augmenta l'exigència de fer el kernel prou general.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Golden test: el valor zenital coincideix amb la mostra de 90° del perfil de la mateixa font.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.