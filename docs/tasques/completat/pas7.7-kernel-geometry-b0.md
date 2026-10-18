# Pas 7.7 — PropagationKernel geomètric i benchmark B0

> **Estat:** completat. **Estat funcional:** observable per API/CLI. **Origen:** planificat. **Abast vigent:** geometria esfèrica ECEF/ENU, LOS segmentada, GK7/15 propi, revisions/cancel·lació i B0; sense transport radiomètric.

## Descripció funcional

`PropagationKernel` recorre les mateixes direccions, segments i nodes tant al zenit com a qualsevol elevació admesa. Amb l’integrand unitari retorna longituds en metres i comptadors reproduïbles. La campanya B0 mesura aquesta ruta directa amb 1/10/25/50/100/200 fonts, cinc passades de warm-up descartades i trenta passades mesurades per configuració.

## Fonts a consultar

- [Arquitectura](../../skyglow/02-arquitectura-integracio.md), [pipeline](../../skyglow/03-pipeline-python-typescript-threejs.md), [algorismes](../../skyglow/01-especificacio-algorismes.md) i [protocol B0–B7](../../skyglow/07-benchmark-b0-b7.md), consultats el 2026-10-18.
- [ESA Navipedia, ECEF/ENU](https://gssc.esa.int/navipedia/index.php/Transformations_between_ECEF_and_ENU_coordinates), consultada el 2026-10-18: convenció d’eixos i rotacions. B0 declara una esfera; no afirma conversió WGS84 el·lipsoïdal.
- [Netlib DQK15](https://www.netlib.org/quadpack/dqk15.f), consultat el 2026-10-18 per contrastar els coeficients matemàtics de la parella 7/15. Implementació Python pròpia; cap codi Fortran ni integrador SciPy incorporat.

## Objectiu

Construir una frontera geomètrica executable i mesurar-ne el cost abans d’afegir òptica, dispersió i acceleracions. Conservar la independència de SG-REF i evitar una ruta especial per a 90°.

## Dependències

**Depèn de:**

- [Pas 7.6 — SG-REF](pas7.6-sg-ref-reference-solver.md)

**En depenen:**

- [Pas 7.8 — OpticalField](pas7.8-optical-field-standard.md)

## Codi existent a reutilitzar

- **REUSE:** [SourceModel i GeodeticPosition](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), sense consumir radiància DNB ni modificar fonts S/C.
- **ADAPT:** convencions ENU ja verificades a [solar_system/calculations.py](../../../backend/src/terralab3d/domain/solar_system/calculations.py), contrastades amb ESA; geometria esfèrica B0 explícita, independent del pla de SG-REF.
- **NEW:** [geometria](../../../backend/src/terralab3d/domain/light_pollution/geometric_transport.py), [GK7/15](../../../backend/src/terralab3d/domain/light_pollution/gauss_kronrod.py), [kernel](../../../backend/src/terralab3d/domain/light_pollution/propagation_kernel.py), [guard de revisions](../../../backend/src/terralab3d/application/geometric_propagation.py), [CLI B0](../../../tools/benchmark_skyglow_b0.py) i [proves](../../../backend/tests/test_propagation_geometry_step7_7.py).
- **Projectes externs:** cap implementació ni dependència nova. SG-REF només és la referència independent dels passos físics posteriors; no se’n reutilitza quadratura ni projecció.

## Flux tècnic

`PropagationRequest(SourceModel[], observer, DirectionSet, PropagationOptions, revision)` → esfera ECEF de radi 6371008,8 m → ENU i LOS fins al sostre geomètric → talls de cel·les cartesianes ENU i altures esfèriques → parella GK7/15 adaptativa → longitud/integral de diagnòstic, error estimat, comptadors i signatura d’entrada.

Azimut des del nord cap a l’est; `DirectionSet` admet azimuts absoluts o offsets respecte del rumb de cada font. El rectangle només aporta un ancoratge per orientar B0: no es calcula ni s’aproxima la seva emissió al centre. La mostra 90° entra al mateix bucle, inclosa la quadratura de 15 nodes per segment.

L’error GK és `|Q15−Q7|` amb sòl d’arrodoniment `50·ε·∫|f|`; se sumen estimacions dels intervals i es refina el de més error fins al pressupost global. No és una cota rigorosa. Les discontinuïtats conegudes exigeixen segmentació explícita. Els límits de treball provoquen fallada de convergència, mai un resultat aparentment correcte.

La partició és geomètrica, ancorada a l’ENU de l’observador. Els identificadors de cel·la no són `OpticalTile` ni dependències de dades atmosfèriques. 7.8 hi connectarà el camp òptic; el present resultat porta `stage=geometry_B0_not_radiance` i unitat `m`.

## Errors, cancel·lació i recursos

Rebuig de direccions no finites, revisions/modelVersion incompatibles, fonts duplicades, particions invàlides, pressupostos esgotats i integrands no finits. Cancel·lació/revisió comprovades als nodes i abans de retornar/publicar; excepcions diferenciades i cap resultat parcial publicat. `GeometricPropagationSession` comprova la revisió també sota lock a la publicació; `close()` invalida treballs i allibera el resultat retingut.

Aquest guard no programa tasques ni implementa una cua, cache o prefetch de 7.21. Els buffers són locals al càlcul. El CLI és CPU/offline, admet Ctrl+C i substitueix cada fitxer final només després d’acabar la campanya; JSON i CSV comparteixen `runId`. Cap recurs GPU ni trànsit de bridge. RSS és working set i peak de vida del procés, no una mesura d’assignacions aïllada per iteració.

## Tasques

- [x] Definir PropagationKernel únic i DirectionSet absolut/per font.
- [x] Implementar esfera ECEF/ENU, LOS, partició geomètrica i GK7/15 amb integrand unitari.
- [x] Implementar cancel·lació cooperativa, revisions, descart de resultats obsolets i comptadors deterministes.
- [x] Executar B0 amb cinc warm-ups i trenta repeticions per configuració, ordre aleatoritzat amb seed canònica, JSON/CSV i metadades reals.
- [x] Provar que el zenit usa els mateixos segments/nodes/camins que dins del DirectionSet complet.

## Criteri de sortida

B0 reproduïble en sis mides, amb 900 LOS a la sèrie principal de 100 fonts; resultats geomètrics finits i unitats explícites. Resultats i comptadors idèntics a cada passada amb les mateixes entrades. Cap gate radiomètric ni SLO de producte declarat.

## Proves i evidències obligatòries

- [x] 48 proves noves: PROJ independent, rotacions, extrems de LOS, segments, polinomis 0–23, integral exponencial, adaptativitat, errors, zenit, S/C i revisions amb fil real.
- [x] 330 proves backend superades; Ruff i Pyright dels fitxers nous sense errors/avisos. Pyright global del backend conserva els mateixos 67 errors i 3 avisos preexistents.
- [x] [Protocol prospectiu](../../evidencies/pas7.7/protocol-b0-v1.json), [resultats](../../evidencies/pas7.7/resultats-b0-v1.json), [CSV de 180 passades](../../evidencies/pas7.7/passades-b0-v1.csv) i [informe/figura](../../evidencies/pas7.7/validacio-b0.md).
- [x] README/inventari/manual, perfils, contractes, dependències i punt de represa coherents.
- [x] Cap física ni capacitat dels passos posteriors marcada com a implementada.

**Resultats verificats:** 2026-10-18; sèrie principal: 900 LOS, 6.638 segments geomètrics, 99.570 nodes i zero subdivisions per a l’integrand constant. Les proves no trivials exerciten subdivisions i fallada de convergència. Vegeu l’informe per latència, memòria, maquinari, signatures i limitacions.

## Fora d'abast

OpticalField i providers, dispersió/extinció, emissió integrada d’àrea, DEM/visibilitat física de curvatura, WGS84 el·lipsoïdal, radiància/SQM/TESS, AD, cache/LUT/scheduler, bridge i renderer. Els altres escenaris B1–B7 i gràfics de fase/AD/cache no s’han executat; no s’inventen valors perquè B0 passi.

## Instrucció per a Codex

Pas completat. Reprendre 7.8 amb aquesta frontera geomètrica i mantenir SG-REF independent. Connectar estat òptic versionat i dependències reals sense confondre cel·les B0 amb dades atmosfèriques. El futur gate 7.12 exigeix el domini físic de referència corresponent i un llindar preregistrat; aquests temps no fixen un SLO.

## Treball pendent

Cap tasca oberta dins 7.7. 7.8 introdueix OpticalField; dispersió, terreny/curvatura, gates, acceleracions i connexió gràfica continuen als passos assignats.
