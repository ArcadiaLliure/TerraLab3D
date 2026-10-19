# ADR-003 — PCHIP en log-radiància

- **Estat:** Acceptada — candidat implementat; gate angular pendent
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

La radiància varia diversos ordres de magnitud i splines cúbiques poden fer overshoot.

## Decisió

Interpolar `log(B+ε)` amb PCHIP; tornar a radiància abans de sumar.

## Conseqüències

Forma més estable i positiva; `ε` s'ha de controlar.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Comparar amb all-sky i escombrar mostra 1°.

## Estat d'implementació

El candidat Python/TypeScript està implementat a7.13 amb golden SciPy compartit. El [gate angular falla](../../evidencies/pas7.13/validacio-camp-angular.md): les9elevacions inicials no són suficients; no s'ha homologat la reconstrucció. Intervals amb zeros o barreres exigeixen ruta directa. El pas continua pendent.