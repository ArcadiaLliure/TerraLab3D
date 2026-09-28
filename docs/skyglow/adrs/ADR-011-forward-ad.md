# ADR-011 — Forward-mode AD geomètric

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

Moviments petits poden reutilitzar resultats si el canvi es pot estimar.

## Decisió

Propagar B i derivades espacials en la mateixa quadratura dins branques diferenciables.

## Conseqüències

Pot reduir recomputes; overhead pendent de B1b/B7.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

B1a vs B1b i finite differences offline.

## Estat d'implementació

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.