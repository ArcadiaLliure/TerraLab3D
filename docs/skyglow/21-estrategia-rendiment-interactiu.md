# Estratègia de rendiment interactiu del skyglow físic

> **Decisió prospectiva (2026-10-19), encara no implementada ni homologada.** Complementa el [pla executable](19-pla-executable-codex.md), els [benchmarks](07-benchmark-b0-b7.md) i els passos [7.18](../tasques/pendent/pas7.18-source-spatial-acceleration.md)–[7.22](../tasques/pendent/pas7.22-optional-runtime-acceleration.md). **No modifica el punt de represa 7.13**, el seu FAIL angular, els gates científics ni els resultats històrics.

## Objectiu de producte i naturalesa dels temps

TerraLab3D ha d'aspirar a una **simulació del skyglow físicament fonamentada i interactiva**: el renderer manté la seva cadència amb un camp radiomètric retingut i el backend n'actualitza el contingut quan canvien les dades. **60 FPS de renderització no vol dir 60 integrals radiatives per segon**; cap integral al render loop.

Hipòtesis de disseny **orientatives, NO SLO aprovats, congelats ni verificats**:
- Visualització fluida orientativa: **60 FPS** al dispositiu de referència que s'aprovi.
- Primera resposta física útil després d'un canvi, orientativament **1–3 s**, amb precisió/domini explícits i indicador de refinament.
- Refinament científic més costós, orientativament **10–30 s**, si el producte ho requereix.

El Pas **7.22** ha de proposar i obtenir aprovació formal de SLO amb responsable, maquinari/plataforma, conjunt de dades, dimensió de cúpula, perfil atmosfèric, fonts, modes, llindars P50/P95/P99, memòria, criteris de precisió i moment de congelació **abans** de decidir PASS/FAIL d'acceleració. Si no hi ha aprovació, aplicar el bloqueig ja previst a 7.22. No declarar que s'han assolit les xifres orientatives.

## Escenaris diferenciats

Mesurar separadament: canvi de **kelvins/SPD** a geometria i atmosfera invariants; canvi de **mescla d'enllumenat**; canvi de **posició** petit/continu i teleport; canvi d'**atmosfera/tile**; canvi de **DEM/oclusió**; inicialització freda i nova solució sense cache. Reportar **temps fins a primera solució vàlida**, temps fins al refinament final, rendiment de presentació i latència entre acció i acceptació, sense confondre'ls.

Quan canvia la SPD poden ser reutilitzables geometria i propietats atmosfèriques; la **radiància no és reutilitzable sense verificar les dependències espectrals**, la normalització i l'error. Canvis d'oclusió i de cobertura obliguen a nova comprovació topològica. Resultats provisionals només amb domini/precisió declarats; mai un cel fictici o filtre RGB com a substitut.

## Fases executables

**7.18 — vectorització i paral·lelisme al costat de l'agrupació espacial.** Auditar els bucles costosos B4/COESA i sobretot fonts extenses amb relleu; provar reutilització exacta i vectorització NumPy/SIMD i, quan sigui pertinent, backend compilat (p. ex. Numba o natiu) sense fixar-ne l'elecció abans dels perfils. Prototipar paral·lelisme de LOS/fonts/bases independents amb fils **només si el codi allibera el GIL** o processos CPU amb costos IPC, serialització, còpies i memòria explícits. Comparar configuracions **1/2/4/6 nuclis** en una màquina de sis nuclis quan hi hagi recursos disponibles; registrar maquinari real i no afirmar escalat lineal. El benchmark ha de cobrir punts i àrees amb oclusions i un camp atmosfèric variable, a més de B5. El guany només compta si l'error radiomètric/angular es manté dins del pressupost científic aplicable.

**7.19 — fase.** Investigar vectorització/codi compilat de l'avaluació de fases i la seva interacció amb els kernels espectrals; comparar representacions accelerades amb taula/oracle i cost de crides. No confondre compressió de fase amb paral·lelització.

**7.20 — AD i cotes.** Comprovar la consistència de sensibilitats i de l'acumulació numèrica entre particions i workers, i invalidar el reuse en discontinuïtats d'oclusió. Cap ordre de reducció no pot canviar el veredicte sense comptabilitzar l'error.

**7.21 — scheduler i workers persistents.** Integrar la capacitat paral·lela homologada al runtime amb cua acotada, cancel·lació realista, descart de revisions, control de pressió de memòria, warm pools, coalescing i prefetch; cap càlcul científic al fil de render. Mesurar throughput **i latència d'interacció**, inclosos canvis ràpids de K i teleports.

**7.22 — decisió SLO / backend avançat.** Després de mesurar ruta directa, 7.18–7.21 i cache, decidir sobre GPU/compute, codi compilat addicional, LUT, precomputació o FFT **només** amb els SLO aprovats, domini matemàtic, equivalència contra ruta directa i fallback. No pressupostar que una GPU millorarà quadratures adaptatives/DEM sense benchmark; incloure temps de transferència, precisió numèrica, memòria i sincronització.

## Protocol transversal de benchmark

- Preservar B0/B1/B2/B4 i els casos extrems del 7.11–7.13 com a **baselines**, sense reinterpretar-los com SLO: aproximadament **29,49 s P50 per 900 LOS B4 homogènies** a 7.10; **~609 s/LOS** per una àrea amb atmosfera variable a 7.12; la projecció **~70 h/1.272 direccions** a 7.13 és una extrapolació, **no** una execució mesurada.
- Warm-up i repeticions segons el protocol vigent; pilots de cost abans de campanyes desproporcionades. Mesurar P50/P95/P99 només amb mida mostral apropiada i informar quan els percentils són exploratoris.
- Comparar serial, vectoritzat, multiprocés/fils justificats i eventual backend compilat/GPU amb **mateixos inputs, fonts, atmosfera, DEM, bandes i política de precisió**. Separar cost d'inici del pool, transferència, computació, recombinació, CPU vs wall, RAM/RSS i càrrega GPU.
- Verificar suma determinista o acotar explícitament l'error de reducció paral·lela, versions/signatures, cancel·lació i absència de resultats obsolets. Guardar comptadors de treball i errors; no atribuir speedup a menys radiància calculada, a més oclusió o a una fixture més senzilla.
- Les toleràncies científiques de 7.4/7.12/7.13/7.17 continuen independents dels SLO de latència. No reduir la precisió per complir un objectiu temporal; només aprovar aproximacions dins dominis i pressupostos justificats.

**Resultat previst:** donar al Pas 7.22 evidència suficient per decidir quina arquitectura permet interactivitat sense alterar el significat del model. No s'exigeix temps real a SG-REF; la ruta directa es conserva com a referència.
