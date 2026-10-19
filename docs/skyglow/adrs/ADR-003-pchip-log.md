# ADR-003 — PCHIP en log-radiància

- **Estat:** Acceptada — v2 verificada en domini numèric registrat
- **Data:** 2026-09-28
- **Àmbit:** skyglow físic

## Context

La radiància varia diversos ordres de magnitud i splines cúbiques poden fer overshoot.

## Decisió

Sumar les fonts en radiància lineal abans del logaritme. Interpolar `log(B+ε)` amb PCHIP vertical i, a la v2, PCHIP log periòdic azimutal; tornar a radiància per a composició i presentació. Els perfils tenen nusos irregulars; ε és estabilitzador numèric, no un sòl físic.

## Conseqüències

Forma més estable i positiva; `ε` s'ha de controlar.

## Alternatives

Es mantenen documentades al TDD i a l'especificació d'algorismes; qualsevol alternativa futura que canviï aquesta decisió requereix un ADR que la substitueixi.

## Validació

Preregistrar estratègia, toleràncies i cost; congelar el camp abans de comparar-lo amb kernel directe i SG-REF sobre punts independents. Els probes de refinament no són validació. La validació finita no prova exactitud uniforme per a qualsevol entrada.

## Estat d'implementació

La [v2 adaptativa Python/TypeScript](../../evidencies/pas7.13/adaptatiu-v2/validacio-adaptativa-v2.md) supera 0,01 mag en els dominis i holdouts registrats; golden SciPy compartits. El [FAIL v1](../../evidencies/pas7.13/validacio-camp-angular.md) de les nou elevacions i interpolació azimutal inicial es conserva. Trams verticals positius se separen per zeros/barreres; DEM/àrea sense garanties requereixen transport directe. La v2 no acredita interpolació azimutal segmentada: amb barreres, l’ús aprovat és directOnly. No hi ha homologació COESA angular general ni C/H observacional.
