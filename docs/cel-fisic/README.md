# Cel físic solar i lunar — dossier de la vertical 7.51+

> **Estat:** especificació pendent d'implementació. El Pas 7 històric continua completat només pel seu cel visual. Cap solver físic Hillaire, LUT solar/lunar ni halo del limbe terrestre es declara implementat.

## Abast i numeració

- **7.1–7.50:** reservat exclusivament a contaminació lumínica artificial. Els passos 7.1–7.28 provenen del bloc històric 23.50–23.74, amb equivalència documental preservada; 7.29–7.50 queden lliures per ampliar aquesta vertical.
- **7.51 en endavant:** Sol, Lluna, dispersió atmosfèrica, color del cel, altura de l'observador, geometria de la Terra i il·luminació. No es trasllada el PropagationKernel artificial a aquesta vertical.
- **Pas 7 (completat):** cel visual heretat i controls Bortle/magnitud; es conserva el seu estat i les evidències originals.

## Contracte de producte

Hi haurà un selector persistent **Cel simulat / Cel real (físic)**. Simulat manté exactament el shader/paleta actuals; real usa transport atmosfèric físic d'estil Hillaire. La selecció no altera efemèrides, observador, contaminació lumínica, SQM/TESS ni autoritat de les dades. L'absència del solver real s'informa; no es fa fallback silenciós ni es presenta la simulació com a mesura científica.

La SkyView LUT pot ser **RGB lineal** per pintar la pantalla. No és un substitut d'un camp espectral: les projeccions instrumentals i la composició científica utilitzen radiància espectral o bandes configurades i compatibles. La radiància del Sol/Lluna i el skyglow artificial se sumen linealment abans de l'exposició; les magnituds o RGB amb tone mapping no es poden sumar.

## Documentació

1. [Arquitectura, separació de responsabilitats i mode](01-arquitectura-i-modes.md).
2. [Física solar/lunar, observador i limbe terrestre](02-fisica-altura-limbe.md).
3. [Llicències comercials i procedència](03-llicencies.md).
4. [Contractes, proves i acceptació](04-contractes-validacio.md).
5. [Dossier de contaminació lumínica artificial](../skyglow/README.md).

## Dependències compartides

Reutilitzar efemèrides del Pas 8, eclipsis del Pas 9, terreny/horitzó dels Passos 15/16, il·luminació del Pas 8.7 i l'estat òptic atmosfèric versionat. Compartir **dades físiques i ports**, no compartir integradors incompatibles ni introduir un segon rellotge o una segona font de veritat.

## Condició legal

Només s'incorporen codi i dades amb autorització comercial explícita i obligacions documentades. El codi MIT de l'exemple Hillaire no concedeix llicència general sobre Unreal Engine. Vegeu [auditoria de llicències](03-llicencies.md).
