# Pas 7.13 — Camp angular i DomeProfile sobre ruta directa

> **Estat:** pendent. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** candidat offline implementat; criteri de sortida bloquejat per FAIL angular i domini COESA angular incomplet. Cap avanç a7.14.

## Descripció funcional

Hi ha mostreig angular pel mateix kernel de7.12, suma lineal de fonts, perfils PCHIP_LOG Python/TypeScript i gràfics científics reproduïbles S/C realista/kelvins. El candidat de8azimuts ×9elevacions no està homologat: el transport passa els controls, però la reconstrucció falla. [Informe](../../evidencies/pas7.13/validacio-camp-angular.md).

## Fonts a consultar

- [Pla canònic](../../skyglow/19-pla-executable-codex.md), [algorismes §10](../../skyglow/01-especificacio-algorismes.md), [pipeline](../../skyglow/03-pipeline-python-typescript-threejs.md), [ADR PCHIP](../../skyglow/adrs/ADR-003-pchip-log.md): consultats el2026-10-19.
- [Gate7.12 i domini](../../evidencies/pas7.12/validacio-gate-transport.md): conservar criteri, 75km optatius i cua condicionada no nul·la.
- [SciPy PchipInterpolator](https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.PchipInterpolator.html): consulta oficial del2026-10-19; derivades PCHIP i oracle independent per als golden. Cap runtime extern copiat.

## Objectiu

Estendre l'operador homologat del zenit a direccions0,5–90° sense acceleracions de fonts. Separar error de transport, reconstrucció vertical, interpolació azimutal i truncament atmosfèric. Preregistre propi angular0,01mag, independent del pressupost espectral0,01mag, sense reajustar llindars després dels residuals.

## Dependències

**Depèn de:**
- [7.12 — Gate numèric en domini condicionat](../completat/pas7.12-zenith-transport-gate.md).

**En depenen:**
- [7.14 — Projeccions fotomètriques](pas7.14-photometric-projections.md), pendent i no iniciat.

## Codi existent a reutilitzar

- **Repositori actual — REUSE:** [PropagationKernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), SourceModel, ECEF/ENU, OpticalField, DEM, SG-REF i provider75km, sense modificar-los.
- **NEW:** [DomeProfile](../../../backend/src/terralab3d/domain/light_pollution/dome_profile.py), [mostreig d'aplicació](../../../backend/src/terralab3d/application/dome_sampling.py), [PCHIP TypeScript](../../../frontend/src/domain/skyglow/domeProfile.ts), [campanya](../../../tools/validate_angular_step7_13.py), [gràfics](../../../tools/plot_dome_step7_13.py).
- **Projectes de referència autoritzats:** cap checkout o motor TerraLab necessari; aquesta capacitat física és nova. SciPy ja és una dependència existent i només actua d'oracle numèric.

## Flux tècnic

PropagationRequest amb sostre explícit → DirectionSet absolut → mateix kernel, també a90° → suma de totes les fonts en radiància lineal → perfils verticals PCHIP sobre log(B+ε) → interpolació periòdica lineal en radiància entre azimuts → DTO diagnòstic amb unitats, signatura, revisió i procedència. ε=min(positius)·10⁻¹⁵; es rebutja ε>min(positius)·10⁻¹². Els nusos es retornen exactament, incloent zero.

Mostres inicials canòniques:0,5/2/5/10/20/30/45/60/90°. Azimuts inicials cada45°. Oracle: dos talls verticals a pas d'1° més0,5° i64punts intermedis;300direccions úniques per escenari. No és una validació uniforme de tota la semiesfera.

COESA conserva75km, P/T i O3 prescrits, precisions de7.12. La cambra homogènia finita75km és un control numèric addicional, no substitueix l'atmosfera estàndard ni assumeix cua nul·la. Les fonts C reals de7.5.1 es traslladen explícitament a una geometria puntual sintètica a5km, mantenint amplitud, SPD, escala i procedència.

## Errors, cancel·lació i recursos

Entrades no finites, extrapolació, nusos repetits, ε excessiu i B0 com a radiància es rebutgen. Cancel·lació i revisió obsoleta es transmeten al kernel; no es publica un camp parcial. Intervals amb zeros/barreres requereixen transport directe, amb None/null, mai transparència o sòl radiomètric. Amb DEM el camp només lliura nusos calculats: no presumeix continuïtat entre LOS. Cobertura absent propaga TerrainCoverageError.

Pilot abans de malles: COESA181,73s/runtime i15,49s/3referències per LOS; projecció orientativa70h per1272direccions, per sobre del límit prospectiu7200s. Malla estàndard no executada. Fonts extenses75km: es preserven els609s/LOS de7.12; cap malla extensa, cache, índex espacial ni degradació de precisió. Buffers locals offline, cap recurs GPU o flux per frame nou.

## Tasques

- [x] Implementar mostreig directe, mateix kernel i suma lineal S/C.
- [x] Construir PCHIP_LOG Python/TypeScript amb golden compartit i oracle SciPy.
- [x] Verificar wrap, positivitat, zenit, zeros, barreres, cancel·lació i errors de cobertura.
- [x] Preregistrar criteris i cost abans de comparar candidats; conservar versions originals.
- [x] Comparar900direccions de cambra i52controls COESA/terreny amb SG-REF independent.
- [x] Separar error de transport i compressió; generar mapes S/C realista/kelvins amb escala explícita.
- [ ] Corregir/refinar reconstrucció vertical i azimutal fins a demostrar0,01mag sense relaxar-lo.
- [ ] Demostrar camp angular COESA75km i domini DEM necessari amb campanya proporcionada i criteri prospectiu.
- [ ] Acreditar sortida angular per a fonts extenses; conservar regressions mentre no hi hagi evidència nova.

## Criteri de sortida

DomeProfile ha de reproduir zenit i camp angular directe dins el pressupost aplicable, amb compressió quantificada independentment. **No demostrat:** PCHIP vertical màxim0,02446982mag; reconstrucció angular màxima2,68860726mag davant0,01mag. Transport952/952PASS en els controls finits, sense homologar una malla COESA completa ni H. El gate bloqueja el tancament de7.13 i l'inici de7.14.

## Proves i evidències obligatòries

- [x] [474proves backend](../../evidencies/pas7.13/pytest-backend-final.txt),30noves; suite frontend,621comprovacions PCHIP compartides, build i typecheck.
- [x] [Regressions](../../evidencies/pas7.13/regressions.json): B0 i4columnes exactes, mateix multiconjunt Pyright global67errors/3avisos heretats; controls afectats nets.
- [x] [Evidències reproduïbles](../../evidencies/pas7.13/README.md), tres figures revisades i202fitxers històrics intactes per hash.
- [x] README/inventari/manual/normes i punt de represa coherents amb resultat parcial.
- [x] Cap acceleració espacial, cache, Three.js definitiu o7.14 anticipats.
- [ ] PASS angular i cobertura completa del domini de sortida.

**Resultats verificats:**2026-10-19, Windows/Python3.13; [veredicte](../../evidencies/pas7.13/gate-angular-final.json). Skill plan aplicada; terralab-manel-style continua absent, s'apliquen les normes locals. Cap commit automàtic.

## Fora d'abast

Projeccions SQM/TESS, factors de calibratge, homologació observacional C/H, watershed/quadtree, acceleració de fases, caches, scheduler o integració Three.js. No convertir una cambra finita en atmosfera terrestre ni adoptar10km com sostre físic.

## Instrucció per a Codex

Continuar exclusivament7.13 des d'aquest FAIL. Preservar els preregistres i els resultats d'aquesta campanya. Abans d'una nova comparació decisòria, versionar el candidat i preregistrar malla/refinament, cobertura, punts independents i cost; mantenir0,01mag angular i el pressupost espectral separat. No copiar nodes d'oracle com a nova malla i reutilitzar-los com si fossin validació independent. No declarar PASS general perquè el transport directe passa. No començar7.14.

## Treball pendent

- [ ] Resoldre densitat vertical prop d'1° i resolució azimutal al voltant de la font, mantenint el mateix operador.
- [ ] Cobrir discontinuïtats/zeros amb segments físicament justificats o ruta directa explícita; no suavitzar-los.
- [ ] Justificar una campanya COESA75km i fonts extenses assequible sense acceleracions prematures ni pèrdua arbitrària de precisió.
- [ ] Completar el gate i només llavors moure aquest document a completat i avançar el punter.
