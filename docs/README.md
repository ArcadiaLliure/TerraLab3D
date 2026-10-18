# Pla de millores de TerraLab3D

Aquest és el punt d'entrada i la font de veritat del progrés. L'estat es basa en comportament observable, proves i evidències del repositori; l'existència d'un paquet, contracte o renderer buit no equival a una funcionalitat implementada.

Consulta també les [normes d'arquitectura i execució](normes-arquitectura.md) i l'[inventari funcional verificat](inventari-funcional.md).

## Punt de represa

> **Punt de represa: [Pas 7.6 — SG-REF](tasques/pendent/pas7.6-sg-ref-reference-solver.md).** El [Pas 7.5 — SourceModel físic S](tasques/completat/pas7.5-source-model-v1.md) ha verificat fonts definides amb SPD, geometria, amplitud i patró angular independents de VIIRS. La [política S/C/H](skyglow/20-politica-rsr-i-validacio-per-dominis.md) manté el gate L3/RSR observacional per a C/H. [7.4](tasques/completat/pas7.4-spectral-bandset-validation.md) conserva el criteri 0,01 mag i 238/238 PASS del seu domini tabulat. 7.6 encara no s'ha executat.
>
> Els subpassos **7.1–7.50** pertanyen a contaminació lumínica artificial: VNP46, VJ146 i VJ246 són fonts Black Marble candidates amb models de mesura propis; cap skyglow físic de producte no està implementat. Els **7.51+** són del cel físic solar/lunar. El Pas 7 històric conserva la visualització actual. Les verticals pendents es documenten a [`skyglow/`](skyglow/README.md) i [`cel-fisic/`](cel-fisic/README.md).

**Estat verificat del 2026-10-18:** [7.5 S](evidencies/pas7.5/validacio-source-model-s-v1.md) passa conservació espectral/angular i coherència dimensional amb fixtures analítiques i taules LED/HP CIE verificades. S'han superat 216 proves backend. La potència de les fixtures és definida o relativa, no estimada d'una ciutat. El [registre RSR observacional](evidencies/pas7.5/auditoria-rsr-2026.json) continua sense coincidència L3 operativa per al 2026-09-13; inferència i homologació C/H resten a 7.16–7.24. El 7.4 continua limitat al seu domini numèric.

Auditoria documental del 2026-10-17: els passos 7.1–7.3 no generaven incidències estructurals; en normalitzar 7.3, el recompte integral va passar de 720 a 708 incidències heretades d'altres passos. El 2026-10-18, després de completar 7.4 i 7.5 S amb les seccions obligatòries, el validador informa de **613 incidències mecàniques heretades**; cap enllaç trencat ni incidència nova del pas vigent. Les duplicitats d'identificador dels fitxers històrics `pas7.4-forward-ad-b1b.md` i `pas7.5-spectral-bandset-b2a.md` continuen sense corregir-se en aquesta vertical. La validació de 7.3 consta a les [evidències](evidencies/pas7.3/validacio-model-dnb.md); les incidències alienes no es corregeixen ara. Vegeu [7.1](evidencies/pas7.1/validacio-contracte.txt), [7.2](evidencies/pas7.2/validacio-adaptador.md), [7.3 — RSR](evidencies/pas7.3/recerca-rsr-2026.md), [7.3 — guia/grànuls](evidencies/pas7.3/contrast-granuls-black-marble-c2.md), [7.5 — observacional històric](evidencies/pas7.5/estat-inferencia-font-2026.md) i [7.5 — S verificat](evidencies/pas7.5/validacio-source-model-s-v1.md). El normalitzador antic no s'ha executat perquè utilitza un mapa de passos anterior al pla canònic actual.

La instrucció **«continua amb el pla de millores»** és suficient: Codex ha de començar en aquest README i executar **exactament un pas cada vegada**. Per a la vertical 7.1–7.28, l’ordre és una linealització científica deliberada: cap optimització pot precedir el seu baseline directe/oracle i cap decisió bloquejant es pot resoldre amb una constant implícita.

## Protocol perquè Codex continuï el pla

1. Llegir aquest README i les [normes d'arquitectura](normes-arquitectura.md).
2. Obrir el document assenyalat a **Punt de represa** i verificar de nou l'estat del codi; el repositori actual preval sobre la descripció.
3. Implementar **només el pas assenyalat** i els seus subtreballs interns. No començar cap pas posterior, encara que sembli independent, fins que el criteri de sortida actual estigui verificat.
4. Executar les proves del pas i les regressions afectades; recollir les evidències exigides i escriure al document els resultats reproduïbles.
5. Actualitzar caselles i estat. `parcial` només és vàlid si hi ha una part observable connectada; un esquelet continua `pendent`.
6. Quan totes les caselles i el criteri de sortida estiguin verificats, canviar l'estat a `completat`, moure el mateix document de `pendent/` a `completat/`, actualitzar les dues taules i avançar **Punt de represa** al número següent.
7. No començar un pas posterior per esquivar un criteri de sortida ni incorporar una [idea per madurar](tasques/idees-per-madurar/README.md) a la seqüència sense tancar abans les seves decisions obertes.

Estats admesos:

- `completat`: vertical executable amb criteri de sortida i evidències verificats.
- `parcial`: hi ha comportament observable reutilitzable, però falta part del resultat funcional.
- `pendent`: només hi ha especificació, contractes, esquelets o cap implementació útil.
- `bloquejat`: manca evidència imprescindible per al domini de sortida del pas; una RSR observacional absent C/H **no bloqueja** 7.5 S. Cap bloqueig no es resol inventant dades o saltant un gate real.
- `per madurar`: la idea encara té decisions funcionals o tècniques obertes i queda fora de l'ordre executable.

## Passos completats

| Pas | Capacitat | Estat |
|---:|---|---|
| 1 | [Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](tasques/completat/pas1.md) | `completat` |
| 2 | [Ubicació geogràfica de l'observador i orientació local](tasques/completat/pas2.md) | `completat` |
| 3 | [Rellotge de simulació, temps sideral i moviment visible](tasques/completat/pas3.md) | `completat` |
| 3.5 | [Càmera translacional, mode caminar i mode avió](tasques/completat/pas3.5.md) | `completat` |
| 4 | [Grid celeste, brúixola, etiquetes i HUD](tasques/completat/pas4.md) | `completat` |
| 5 | [Camp estel·lar Gaia real, fallback i buffers persistents](tasques/completat/pas5.md) | `completat` |
| 6 | [Picking estel·lar precís](tasques/completat/pas6.md) | `completat` |
| 7 | [Cel, atmosfera, contaminació lumínica i Bortle](tasques/completat/pas7.md) | `completat` |
| 7.1 | [Contracte científic v1, dades i política d'acceptació](tasques/completat/pas7.1-contracte-cientific-v1.md) | `completat` documentalment |
| 7.2 | [Adaptador VNP46 d’observació, qualitat i procedència](tasques/completat/pas7.2-vnp46-observation-adapter.md) | `completat` |
| 7.3 | [Model de mesura DNB multisatèl·lit](tasques/completat/pas7.3-dnb-rsr-measurement.md) | `completat` (contractes TOA i Black Marble L3; fonts físiques 2026 no homologades) |
| 7.4 | [Oracle espectral fi i SpectralBandSet tabulat v1](tasques/completat/pas7.4-spectral-bandset-validation.md) | `completat` (domini numèric acotat; 238/238 PASS) |
| 7.5 | [SourceModel físic S independent de VIIRS](tasques/completat/pas7.5-source-model-v1.md) | `completat` (fonts definides; C/H sense homologar) |
| 8 | [Sol, Lluna i planetes amb posicions i aparença reals](tasques/completat/pas8.md) | `completat` |
| 8.5 | [Superfície lunar LRO/LOLA, orientació i libració](tasques/completat/pas8.5.md) | `completat` |
| 8.6 | [Planetes, anells i satèl·lits naturals](tasques/completat/pas8.6.md) | `completat` |
| 8.7 | [Il·luminació física de l'escena](tasques/completat/pas8.7.md) | `completat` |
| 9 | [Eclipsis, ocultacions, separacions i trajectòries](tasques/completat/pas9.md) | `completat` |
| 10 | [Via Làctia i pols galàctica Planck](tasques/completat/pas10.md) | `completat` |
| 11 | [Cel profund NGC/IC](tasques/completat/pas11.md) | `completat` |
| 12 | [Cerca astronòmica, focus i seguiment](tasques/completat/pas12.md) | `completat` |
| 13 | [Picking real, hover, selecció i inspecció](tasques/completat/pas13.md) | `completat` |
| 14 | [Traces circumpolars i exposició temporal](tasques/completat/pas14.md) | `completat` |
| 15 | [Elevació real, perfil d'horitzó i oclusió](tasques/completat/pas15.md) | `completat` |
| 16 | [Terreny 3D retingut, tiles, LOD i picking](tasques/completat/pas16.md) | `completat` |
| 17 | [Superfície categòrica, estils i refinament visual](tasques/completat/pas17-superficie-progressiva.md) | `completat per ajust d'abast` |
| 19 | [Modes d'observació: ull nu, càmera fotogràfica i telescopi/Scope](tasques/completat/pas19-modes-optics.md) | `completat` |
| 21 | [Eines de mesura esfèrica](tasques/completat/pas21-eines-mesura.md) | `completat` |
| 22 | [Trajectòries i visibilitat sobre l'horitzó real](tasques/completat/pas22-trajectories-visibilitat.md) | `completat` |
| 22.5 | [Normalització de la documentació viva](tasques/completat/pas22.5-normalitzacio-documental.md) | `completat` |
| 23 | [Constel·lacions IAU, traçat de referència i documents d'usuari](tasques/completat/pas23-constellacions.md) | `completat` |

La numeració dels passos completats i del backlog 24–38 es preserva. **Excepció documentada:** el bloc planificat 23.50–23.74 s'ha traslladat íntegrament a **7.1–7.28** per separar la contaminació lumínica artificial (**7.1–7.50**, amb 7.29–7.50 reservats) del cel solar/lunar (**7.51+**). Les equivalències antigues consten a la documentació del dossier; el Pas 7 històric continua completat pel seu abast visual.

Els números 18 i 20 queden reservats com a traça històrica: meteorologia s'ha retirat de l'ordre executable i ara és un [dossier per madurar](tasques/idees-per-madurar/meteorologia.md); l'antic Pas 20 (simulació fotogràfica) ha estat absorbit pel Pas 19 (modes d'observació instrumental). La resta de passos conserven la numeració existent.

## Passos pendents

| Pas | Capacitat | Estat | Dependències |
|---:|---|---|---|
| 7.6 | [SG-REF: oracle independent de transport i integració d’àrea](tasques/pendent/pas7.6-sg-ref-reference-solver.md) | `pendent` | 7.5 |
| 7.7 | [PropagationKernel geomètric i benchmark B0](tasques/pendent/pas7.7-kernel-geometry-b0.md) | `pendent` | 7.6 |
| 7.8 | [OpticalField tiled i atmosfera estàndard determinista](tasques/pendent/pas7.8-optical-field-standard.md) | `pendent` | 7.7 |
| 7.9 | [Rayleigh, aerosol de referència i benchmark B1](tasques/pendent/pas7.9-rayleigh-aerosol-b1.md) | `pendent` | 7.8 |
| 7.10 | [Kernel espectral complet i absorció gasosa](tasques/pendent/pas7.10-gas-spectral-kernel.md) | `pendent` | 7.9, 7.4 (revalidació espectral) |
| 7.11 | [Terreny, curvatura i visibilitat física](tasques/pendent/pas7.11-terrain-curvature.md) | `pendent` | 7.10 |
| 7.12 | [Gate zenital de transport radiomètric](tasques/pendent/pas7.12-zenith-transport-gate.md) | `pendent` | 7.11 |
| 7.13 | [Camp angular i DomeProfile sobre ruta directa](tasques/pendent/pas7.13-dome-profile-direct.md) | `pendent` | 7.12 |
| 7.14 | [Projeccions fotomètriques i sensors SQM/TESS](tasques/pendent/pas7.14-photometric-projections.md) | `pendent` | 7.13, 7.4 (revalidació espectral) |
| 7.15 | [Atmosfera real ERA5/CAMS i composició de camps](tasques/pendent/pas7.15-atmos-era5-cams.md) | `pendent` | 7.14 |
| 7.16 | [Incertesa quantitativa i provenance completa](tasques/pendent/pas7.16-uncertainty-provenance.md) | `pendent` | 7.3, 7.5, 7.15 |
| 7.17 | [Validació empírica clear-sky de SourceModel i transport](tasques/pendent/pas7.17-clear-sky-ground-truth.md) | `pendent` | 7.3, 7.5, 7.16 |
| 7.18 | [Watershed, EmissionRegion i quadtree com acceleració B5](tasques/pendent/pas7.18-source-spatial-acceleration.md) | `pendent` | 7.17 |
| 7.19 | [Compressió de PhaseFunction i benchmark B3](tasques/pendent/pas7.19-phase-acceleration-b3.md) | `pendent` | 7.18 |
| 7.20 | [Forward AD i RadiativeErrorBudget](tasques/pendent/pas7.20-ad-error-budget.md) | `pendent` | 7.19 |
| 7.21 | [Cache error-based, scheduler latest-wins i prefetch](tasques/pendent/pas7.21-cache-scheduler.md) | `pendent` | 7.20 |
| 7.22 | [Decisió i backend opcional LUT/precomputació/FFT](tasques/pendent/pas7.22-optional-runtime-acceleration.md) | `pendent` | 7.21 |
| 7.23 | [CloudOpticalState i núvols single-scattering B6](tasques/pendent/pas7.23-clouds-b6.md) | `pendent` | 7.22 |
| 7.24 | [Validació empírica final clear/cloudy i congelació de model](tasques/pendent/pas7.24-full-ground-truth.md) | `pendent` | 7.23 |
| 7.25 | [Bridge Python→TypeScript i SkyglowRuntime](tasques/pendent/pas7.25-bridge-runtime.md) | `pendent` | 7.24 |
| 7.26 | [Renderer Three.js lineal i modes diagnòstics](tasques/pendent/pas7.26-three-renderer-debug.md) | `pendent` | 7.25 |
| 7.27 | [Composició lineal del cel i estats reference/instantaneous](tasques/pendent/pas7.27-sky-composition.md) | `pendent` | 7.26 |
| 7.28 | [B7 FULL, SLO i homologació del skyglow artificial](tasques/pendent/pas7.28-b7-homologacio-skyglow.md) | `pendent` | 7.1–7.27 |
| 7.51 | [Llicències comercials i recursos del cel físic](tasques/pendent/pas7.51-llicencies-i-recursos.md) | `pendent` | 7, 8, 8.7 |
| 7.52 | [Selector permanent cel simulat/real](tasques/pendent/pas7.52-selector-cel-simulat-real.md) | `pendent` | 7.51 |
| 7.53 | [Estat òptic, geodèsia i altura](tasques/pendent/pas7.53-optica-observador-altura.md) | `pendent` | 7.52 |
| 7.54 | [Font solar espectral](tasques/pendent/pas7.54-font-solar-espectral.md) | `pendent` | 7.53 |
| 7.55 | [Font lunar espectral i fase](tasques/pendent/pas7.55-font-lunar-espectral.md) | `pendent` | 7.54 |
| 7.56 | [Transport atmosfèric Hillaire](tasques/pendent/pas7.56-transport-atmosferic-hillaire.md) | `pendent` | 7.55 |
| 7.57 | [SkyView LUT RGB i fotometria espectral](tasques/pendent/pas7.57-skyview-lut-colorimetria.md) | `pendent` | 7.56 |
| 7.58 | [Limbe terrestre i altura orbital](tasques/pendent/pas7.58-limbe-terrestre-altura.md) | `pendent` | 7.57 |
| 7.59 | [Il·luminació solar/lunar i eclipsis](tasques/pendent/pas7.59-illuminacio-terreny-eclipsis.md) | `pendent` | 7.58 |
| 7.60 | [Integració bridge/Three.js](tasques/pendent/pas7.60-integracio-three-bridge.md) | `pendent` | 7.59 |
| 7.61 | [Fons natural nocturn: airglow, zodiacal i llum estel·lar integrada](tasques/pendent/pas7.61-natural-night-sky.md) | `pendent` | 7.60 |
| 7.62 | [Pressupost d'error i descarte radiatiu conservador](tasques/pendent/pas7.62-radiative-error-budget.md) | `pendent` | 7.61, 7.20 |
| 7.63 | [Núvols físics, horitzó, ombra planetària i terminador](tasques/pendent/pas7.63-clouds-horizon-terminator.md) | `pendent` | 7.62, 7.23 |
| 7.64 | [Scheduler latest-wins, invalidació i caches del cel físic](tasques/pendent/pas7.64-scheduler-cache-cel-fisic.md) | `pendent` | 7.63 |
| 7.65 | [Solver espectral de referència i oracles científics](tasques/pendent/pas7.65-reference-solver.md) | `pendent` | 7.64 |
| 7.66 | [Matriu de validació científica del cel físic](tasques/pendent/pas7.66-validacio-cel-fisic.md) | `pendent` | 7.65 |
| 7.67 | [SLO de rendiment, memòria i latència interactiva](tasques/pendent/pas7.67-slo-rendiment-cel-fisic.md) | `pendent` | 7.66 |
| 7.68 | [Homologació final del cel físic real/simulat](tasques/pendent/pas7.68-homologacio-cel-fisic.md) | `pendent` | 7.67 |
| 24 | [Catàleg de recursos i descàrregues persistents](tasques/pendent/pas24-cataleg-recursos-descarregues.md) | `parcial` | 7.3 (cas Black Marble), 8.6, 12 |
| 25 | [Gestor de capes Cel/Terra](tasques/pendent/pas25-gestor-capes.md) | `pendent` | 24 |
| 26 | [Vista de recursos del Sistema Solar](tasques/pendent/pas26-recursos-sistema-solar.md) | `parcial` | 24, 25 |
| 27 | [Carta de recursos d'espai profund](tasques/pendent/pas27-recursos-espai-profund.md) | `parcial` | 10, 11, 24, 25 |
| 28 | [Descobriment de DEM multiproveïdor](tasques/pendent/pas28-dem-multiproveidor.md) | `parcial` | 16, 24, 25 |
| 29 | [Superfície semàntica, TLST i refinament](tasques/pendent/pas29-superficie-semantica.md) | `parcial` | 17, 24, 25 |
| 30 | [Plate solving i comparador foto/simulació](tasques/pendent/pas30-plate-solving.md) | `pendent` | 5, 11, 19 |
| 31 | [“El millor d'aquesta nit” i planificador](tasques/pendent/pas31-millor-nit-planificador.md) | `pendent` | 22, 23 |
| 32 | [Motor general d'efemèrides](tasques/pendent/pas32-motor-efemerides.md) | `parcial` | 9, 22 |
| 33 | [Cercador d'objectes i efemèrides](tasques/pendent/pas33-cercador-objectes-efemerides.md) | `parcial` | 31, 32 |
| 34 | [Miniatures i animacions d'efemèrides](tasques/pendent/pas34-previsualitzacions-efemerides.md) | `pendent` | 32, 33 |
| 35 | [Pestanya d'eclipsis](tasques/pendent/pas35-pestanya-eclipsis.md) | `parcial` | 9, 33, 34 opcional |
| 36 | [Esdeveniments propis de planetes i Lluna](tasques/pendent/pas36-esdeveniments-objectes.md) | `parcial` | 32, 33 |
| 37 | [Nomenclàtor GeoNames empaquetat](tasques/pendent/pas37-geonames-empaquetat.md) | `pendent` | 19, 29 |
| 38 | [Homologació final, recuperació i rendiment](tasques/pendent/pas38-homologacio-final.md) | `pendent` | 1–17, 19–37, 7.28, 7.68 |

## Idees per madurar

Els tretze dossiers exclosos de la seqüència executable, la seva decisió pendent, condició de maduresa i relació amb el backlog són a l'[índex d'idees per madurar](tasques/idees-per-madurar/README.md). El seu estat és `per madurar`.

## Mapa històric de la consolidació

La taula registra la destinació actual de cadascun dels vuit pendents històrics i els vint-i-cinc dossiers madurs del brainstorming. Els números de “pendent” i “novetat” són els identificadors anteriors a la fusió; ja no són ordre executable.

| Destinació | Fonts absorbides | Decisió de fusió |
|---:|---|---|
| 17 | pendent 17 + novetat 37 | Superfície categòrica i refinament visual sobre els tiles ja completats; l'ortofoto queda descartada. |
| — | pendent 18 (còpia local provisional 30) | Meteorologia surt de l'ordre executable i es conserva com a [dossier per madurar](tasques/idees-per-madurar/meteorologia.md). |
| 19 | pendent 19 + antic pas 20 + novetats 25, 26 | Modes d'observació instrumental, enquadrament, geometria òptica, HUD, Gaia i previsualització fotogràfica integrada. |
| — | antic pas 20 | Reservat com a traça històrica; absorbit pel Pas 19. |
| 21 | pendent 21 | Mesures esfèriques editables. |
| 22 | novetat 28 | Trajectòries comunes i visibilitat contra l'horitzó real. |
| 23 | pendent 22 + novetat 29 | Constel·lacions oficials, observables, editables i persistents. |
| 24 | part de pendent 23 + novetat 42 | Catàleg i treballs de descàrrega. |
| 25 | resta de pendent 23 + novetat 39 | Capes, AOI, disponibilitat, visibilitat i preferències. |
| 26 | novetat 40 | Recursos del Sistema Solar. |
| 27 | novetat 41 | Recursos d'espai profund. |
| 28 | novetat 43 | DEM multiproveïdor. |
| 29 | novetats 44 + 45 + 46 | Superfície semàntica, TLST i refinament. |
| 30 | novetat 27 | Plate solving. |
| 31 | novetats 30 + 31 | Recomanacions i planificador com una experiència única. |
| 32 | novetat 32 | Motor general d'efemèrides. |
| 33 | novetat 33 | Cercador multipestanya. |
| 34 | novetat 34 | Previsualitzacions generades pel renderer. |
| 35 | novetat 35 | Pestanya d'eclipsis. |
| 36 | novetat 36 | Esdeveniments propis per cos. |
| 37 | novetats 47 + 48 + 49 | Assentaments, cims i dades base empaquetades. |
| 38 | pendent 24 + novetat 38 | Homologació i transicions llargues interactives; el vol físic queda immadur. |

## Procedència i criteri del brainstorming

La pluja d'idees va aportar 25 propostes prou tancades per fusionar amb el pla i 12 dossiers amb preguntes obertes. La reclassificació posterior de meteorologia eleva a 13 els dossiers actuals per madurar. Aquesta consolidació conserva decisions funcionals, elimina repeticions i instruccions de “crear des de zero”, i les vincula al codi real disponible. TerraLab és només oracle de comportament al [commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d); TerraLab3D no en depèn en execució.

## Evidències i dades de referència

- [`manifests/`](manifests/) conté manifests reproduïbles de recursos científics.
- [`reference-scenarios/`](reference-scenarios/) conté escenaris i captures de comparació visual.
