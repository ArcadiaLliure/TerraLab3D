# ADR-003 — PCHIP en log-radiància

- **Estat:** Accepted for implementation
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

No implementat per aquest ADR. El tancament depèn del pas de TerraLab3D corresponent i de les seves evidències.