# ADR-017 — Gate zenital i projeccions fotomètriques post-kernel

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-10-15
- **Àmbit:** skyglow físic

## Context

La primera iteració podia produir camps direccionals plausibles abans de tancar la cadena d'unitats absolutes, cosa que facilita amagar errors amb factors de calibratge finals.

## Decisió

La direcció de 90° es valida primer com a gate radiomètric absolut amb el mateix `PropagationKernel`. El kernel només produeix radiància física. Luminància CIE, SQM, TESS-W, altres sensors i `BortleEquivalent` són projeccions post-kernel amb resposta espectral, FOV, zero point/calibratge i versió explícits.

No s'accepta conversió directa VIIRS→SQM ni `relativeRadiance × calibrationFactor → cd/m²` sense model físic traçable. Artificial, natural sense Lluna, lunar i crepuscular es mantenen separats i se sumen linealment. El `BortleEquivalent` de lloc usa condicions de referència sense Lluna ni crepuscle.

## Conseqüències

El zenit es converteix en invariant de les cúpules i els sensors es poden canviar sense tocar propagació.

## Alternatives

Solver zenital separat, calibratge final opac i Bortle derivat de la Lluna instantània: descartats.

## Validació

Passos 23.681, 23.691, 23.692 i 23.72.

## Estat d'implementació

No implementat per aquest ADR.
