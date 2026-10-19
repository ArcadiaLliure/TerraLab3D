# Pas 7.13 — Camp angular i DomeProfile sobre ruta directa

> **Estat:** completat. **Estat funcional:** observable offline en el domini numèric registrat. **Origen:** planificat. **Abast vigent:** reconstrucció adaptativa S/C acreditada en les fixtures i els punts independents declarats, control COESA limitat i ruta directa obligatòria fora de les garanties. Cap execució de 7.14.

## Descripció funcional

El mateix kernel de 7.12 calcula les direccions angulars, inclòs el zenit, suma fonts en radiància lineal i construeix perfils PCHIP log verticals irregulars i periòdics en azimut. La [v2 adaptativa](../../evidencies/pas7.13/adaptatiu-v2/validacio-adaptativa-v2.md) supera 0,01 mag sobre 900 direccions independents de tres fixtures S/C, amb controls COESA i fallbacks explícits. El [candidat v1 fallit](../../evidencies/pas7.13/validacio-camp-angular.md), els preregistres i les evidències originals es conserven íntegres.

## Fonts a consultar

- [Pla canònic](../../skyglow/19-pla-executable-codex.md), [algorismes §10](../../skyglow/01-especificacio-algorismes.md), [pipeline](../../skyglow/03-pipeline-python-typescript-threejs.md) i [ADR PCHIP](../../skyglow/adrs/ADR-003-pchip-log.md): consultats el 2026-10-19.
- [Estratègia de rendiment](../../skyglow/21-estrategia-rendiment-interactiu.md), contrastada amb GitHub al commit 83272b83686d26baa7540fec128165cc9775158e: acceleracions reservades a 7.18–7.22, sense alterar aquest planning.
- [Gate 7.12 i domini](../../evidencies/pas7.12/validacio-gate-transport.md) i [cota exterior](../../evidencies/pas7.12/domini-i-cota-exterior.md): 75 km optatius, contribució superior positiva i condicionada.
- [SciPy PchipInterpolator](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html): documentació oficial consultada el 2026-10-19; oracle numèric independent, sense copiar un runtime extern.

## Objectiu

Estendre el mateix operador a direccions 0,5–90° sense acceleracions de fonts. Quantificar independentment reconstrucció angular i transport. El llindar angular preregistrat de 0,01 mag es manté; el pressupost espectral de 0,01 mag i la cua condicionada de 0,001 mag són assignacions separades, no una promesa d’error físic total.

## Dependències

**Depèn de:**
- [7.12 — Gate numèric en domini condicionat](pas7.12-zenith-transport-gate.md).

**En depenen:**
- [7.14 — Projeccions fotomètriques](../pendent/pas7.14-photometric-projections.md), pendent i no iniciat.

## Codi existent a reutilitzar

- **REUSE:** [PropagationKernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), SourceModel S/C, ECEF/ENU, OpticalField, DEM, SG-REF i provider 75 km. Els 36 fitxers científics vinculats a 7.12 continuen idèntics.
- **REUSE del candidat v1 preservat:** [DomeProfile](../../../backend/src/terralab3d/domain/light_pollution/dome_profile.py), [mostreig directe](../../../backend/src/terralab3d/application/dome_sampling.py) i [PCHIP TypeScript](../../../frontend/src/domain/skyglow/domeProfile.ts).
- **NEW v2:** [refinador](../../../backend/src/terralab3d/domain/light_pollution/adaptive_dome.py), [cas d’ús](../../../backend/src/terralab3d/application/adaptive_dome_sampling.py), [presentació TypeScript](../../../frontend/src/domain/skyglow/adaptiveDome.ts), [campanya](../../../tools/validate_adaptive_dome_step7_13_v2.py), [auditoria](../../../tools/audit_adaptive_dome_step7_13_v2.py) i [figures](../../../tools/plot_adaptive_dome_step7_13_v2.py).
- **Projectes de referència autoritzats:** cap checkout TerraLab necessari. SciPy existent actua d’oracle PCHIP; SG-REF manté els seus algorismes independents.

## Flux tècnic

Petició completa amb sostre/precisió explícits → mateix kernel per node → suma lineal → refinament vertical i azimutal amb probes interns de 0,002 mag → camp congelat i hash → validació sobre punts independents de 0,01 mag. Els holdouts no s’envien al refinador. Un camp cru no rep PASS automàticament.

Inicialització de vuit azimuts i nou elevacions; probes a 1/4, 1/2 i 3/4. Cada interval que falla promou el punt o perfil mitjà; es tornen a comprovar les pendents veïnes. Nusos verticals irregulars, PCHIP log periòdic sobre quatre perfils azimutals; ε=min(positius)·10⁻¹⁵, amb límit relatiu 10⁻¹². El registre de nodes exactes és local a una construcció/revisió, sense cache entre peticions.

Domini acreditat: tres fonts puntuals S/C prescrites a 5 km, observador a 100 m, cambra homogènia finita de 75 km, elevacions 0,5–90°, 300 holdouts per escenari. C conserva SPD/amplitud/normalització de 7.5.1 i trasllada explícitament la geometria; és relatiu. El control COESA usa perfil d’1 km fins a 75 km, azimut 270,7° i interval 45–60°, quatre nodes de suport i tres holdouts; tres LOS COESA addicionals contrasten el transport, inclòs prop de l’horitzó. No és homologació uniforme de qualsevol atmosfera.

## Errors, cancel·lació i recursos

Entrades no finites, extrapolació, nusos repetits, ε excessiu i B0 com a radiància es rebutgen. Cancel·lació i revisió obsoleta es transmeten al kernel; no es publica un camp parcial. Límits preregistrats: 8.000 mostres, 128 perfils i 1.800 s per camp; 7.200 s de campanya científica. Exhaurir-los és error, no permís per rebaixar precisió.

DEM i fonts extenses exigeixen ruta directa, sense compressió acreditada. Zeros exactes es preserven; intervals sense garanties retornen None/null. Amb barreres azimutals desconegudes, l’ús acreditat és directOnly: no es validen pendents que travessin discontinuïtats. Cobertura absent propaga TerrainCoverageError. No hi ha transparències ni suavitzat físic.

Es preserven el sostre COESA de 75 km i les cotes positives >75 km, sota aire sec hidrostàtic/aerosol prescrit de 7.12. El 22,45% omès amb 10 km vs 50 km a B4 continua documentat. El pilot COESA de 7.13 projectava unes 70 h per 1.272 direccions; no s’ha executat aquesta malla ni la d’àrees d’uns 609 s/LOS. Buffers locals offline, sense nous recursos GPU ni treball per frame.

## Tasques

- [x] Mateix transport a qualsevol elevació, suma lineal i compatibilitat S/C realista/kelvins.
- [x] Refinament adaptatiu vertical i azimutal versionat i preregistrat, sense afinar amb els holdouts.
- [x] PCHIP Python/TypeScript i golden SciPy compartit, wrap i zenit coherent.
- [x] 900 holdouts angulars, 18 controls COESA/DEM/àrea i tres holdouts addicionals de perfil COESA.
- [x] Zeros, discontinuïtats, cobertura DEM, cancel·lació, revisions i exhauriment de pressupost amb ruta directa explícita.
- [x] Mapes científics, errors, mostres, diferències realista/K i costos reals reproduïbles.
- [x] Gates i evidències històriques preservats; planning i punt de represa actualitzats.

## Criteri de sortida

[PASS_REGISTERED_ANGULAR_DOMAIN](../../evidencies/pas7.13/adaptatiu-v2/gate-adaptatiu-v2.json): màxim protegit 0,001894297 mag en els 900 holdouts de cambra, i **0,004964471 mag** en els tres del perfil COESA, davant 0,01 mag. Els 921 contrasts de transport passen; la cua positiva compleix 0,001 mag. Els probes d’ajust sols no són el gate. El PASS és de les fixtures, les discretitzacions i els punts declarats, amb transport directe fora de les garanties; no exactitud observacional ni compressió general COESA/DEM/àrea.

## Proves i evidències obligatòries

- [x] [495 proves backend](../../evidencies/pas7.13/adaptatiu-v2/pytest-backend.txt), 21 noves, amb avisos com a errors.
- [x] [Suite frontend](../../evidencies/pas7.13/adaptatiu-v2/tests-frontend.txt), 768 comprovacions noves més les 621 històriques de PCHIP; typecheck i build.
- [x] Ruff/format i Pyright afectats nets; mateix multiconjunt global preexistent de 67 errors/3 avisos.
- [x] [Regressions exactes](../../evidencies/pas7.13/adaptatiu-v2/regressions-i-preservacio-v2.json): B0/900 LOS, quatre columnes, 36 fitxers científics de 7.12 i 247 evidències històriques.
- [x] [Registres i reproducció](../../evidencies/pas7.13/adaptatiu-v2/README.md), sis figures inspeccionades i manifest final.
- [x] Documents i enllaços coherents, sense executar 7.14 ni alterar 7.18–7.22.

**Resultats verificats:** 2026-10-19, Windows/Python 3.13. Skill plan aplicada; terralab-manel-style absent, normes locals aplicades. Cap commit automàtic.

## Fora d'abast

SQM/TESS, constant fotomètrica, calibratge arbitrari, homologació observacional C/H, reconstrucció COESA global o d’àrees/DEM sense garanties, watershed/quadtree, caches, vectorització addicional, multicore, scheduler i integració Three.js definitiva. No convertir la cambra en atmosfera real ni assumir nul·la la contribució superior a 75 km.

## Instrucció per a Codex

Aquest pas està tancat exclusivament en el domini declarat. Conserva el FAIL v1 i els preregistres v2, i no ampliïs una homologació amb els probes sols. Qualsevol nou domini o candidat necessita preregistre, punts independents i estimació de cost; cap relaxació retrospectiva de 0,01 mag. La següent execució autoritzada reprendrà 7.14 sense recalibrar el transport ni anticipar 7.18–7.22. No començar-lo dins d’aquesta execució.

## Treball pendent

Cap requisit pendent del domini de sortida registrat. La compressió angular COESA general, d’àrees i de DEM continua sense acreditació i sense ús permès com a resultat homologat; aquests casos disposen de transport directe. Una futura ampliació requerirà el seu gate prospectiu. Producte, SLO i C/H mantenen els seus passos canònics; no s’han declarat resolts.
