# Cel físic solar i lunar — dossier de la vertical 7.51+

> **Estat:** especificació pendent d'implementació. El Pas 7 històric continua completat només pel seu cel visual. Cap solver físic Hillaire, model ROLO, fons nocturn físic, LUT solar/lunar ni halo del limbe terrestre es declara implementat fins que el subpas corresponent aporti proves.

## Abast i numeració

- **7.1–7.50:** exclusiu de contaminació lumínica artificial. Els passos 7.1–7.28 provenen del bloc històric 23.50–23.74; 7.29–7.50 queden reservats.
- **7.51–7.68:** cel físic solar/lunar, fons natural, pressupost d'error, núvols, scheduler, solver de referència, validació i SLO.
- **Pas 7 (completat):** cel visual heretat i controls Bortle/magnitud. Es conserva com a mode `simulated`.
- El `PropagationKernel` artificial **no** es converteix en el solver solar/lunar.

## Contracte de producte

Hi ha un selector persistent **Cel simulat / Cel real (físic)**. `simulated` conserva el shader/paleta actuals; `physical` usa transport atmosfèric físic. La selecció no altera efemèrides, observador, contaminació lumínica, SQM/TESS ni l'autoritat de les dades. Si el solver físic no és disponible, s'exposa `unavailable`; no hi ha fallback silenciós.

La **SkyView LUT és RGB lineal i només de visualització**. La fotometria científica conserva radiància espectral o integrada per bandes configurades. SQM/TESS/CIE no es deriven dels píxels RGB. `spectralBandCount` és configurable i **no es decideix mitjançant benchmarks o sweeps de N**.

## Decisions científiques tancades

- Lluna: **ROLO/USGS** com a autoritat d'irradiància integrada en disc dins del domini observacional suportat; model de reflectància separat (Hapke, amb Lommel-Seeliger com a fallback mínim) per aparença espacial i extrapolació marcada fora del domini.
- Fons nocturn: `NaturalNightSkyModel` independent amb airglow, llum zodiacal i llum estel·lar integrada no resolta; Via Làctia difusa continua sent responsabilitat del Pas 10.
- Descart radiatiu: només amb **cotes superiors conservadores** i pressupost acumulat d'error; defaults inicials 0,1 % individual i 0,5 % acumulat, configurables.
- Núvols: `CloudOpticalState` compartit (`τ, ω0, g, cover, base, top` per banda); el skyglow i el cel astral tenen integradors separats.
- Scheduler: revisions monotòniques, `latest-wins`, una revisió efectiva pendent i cap resultat obsolet publicable.
- Referència científica: Bruneton espectral/CPU + path tracer Hillaire + oracles específics (ROLO, referències externes de fons natural i núvols).
- Rendiment: perfil inicial `desktop-60` mesurat, sense degradar automàticament la configuració científica ni seleccionar N per rendiment.

Vegeu la [matriu de decisions tancades](05-decisions-tancades.md).

## Documentació

1. [Arquitectura, responsabilitats i modes](01-arquitectura-i-modes.md).
2. [Física solar/lunar, fons nocturn, altura i limbe](02-fisica-altura-limbe.md).
3. [Llicències comercials i procedència](03-llicencies.md).
4. [Contractes, pressupostos, validació i SLO](04-contractes-validacio.md).
5. [Decisions 2–8 tancades i criteris de revisió](05-decisions-tancades.md).
6. [Dossier de contaminació lumínica artificial](../skyglow/README.md).

## Dependències compartides

Reutilitzar efemèrides del Pas 8, eclipsis del Pas 9, terreny/horitzó dels Passos 15/16, il·luminació del Pas 8.7 i estat òptic atmosfèric versionat. Compartir **dades físiques i ports**, no integradors incompatibles, caches radiatives ni una segona font de temps.

## Condició legal

Només s'incorporen codi i dades amb ús comercial/redistribució compatible amb la política del projecte i obligacions documentades. El codi MIT de l'exemple Hillaire no concedeix llicència general sobre Unreal Engine. Vegeu [auditoria de llicències](03-llicencies.md).
