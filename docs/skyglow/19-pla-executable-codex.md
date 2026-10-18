# Pla executable canònic del skyglow per a Codex

> Estat: pendent d’implementació. Aquest document substitueix l’ordre executable anterior de 7.1–7.28. La numeració es conserva per compatibilitat amb la vertical 7.51+, **no** per preservar la descomposició antiga.

## Regla d’execució

Codex executa un únic pas cada vegada. No pot començar el següent fins que el criteri de sortida de l’actual estigui verificat amb proves/evidències i l’estat/documentació s’hagi actualitzat. Si una dada o decisió científica imprescindible no es pot justificar amb una font autoritativa o evidència reproduïble, el pas passa a `bloquejat` i la seqüència s’atura.

No s’accepta cap d’aquests patrons:
- implementar una optimització abans del baseline directe que ha de validar;
- usar el mateix algoritme aproximat com a únic oracle;
- “resoldre” una decisió oberta amb una constant de conveniència;
- ajustar llindars PASS/FAIL després de veure els resultats;
- fer que VNP46/VJ146/VJ246 impliquin Lambert, flux hemisfèric o skyglow directament;
- executar integrals radiatives al render loop.

`V1` és una [política preregistrada](skyglow-v1-profile.json), congelada a 7.1: cap llindar PASS/FAIL es pot ajustar després de veure el resultat del candidat a validar. Cada llindar exigeix mètrica, valor, unitat, domini, categoria d'origen, referència verificable, justificació, propietari, moment de congelació i revisió. L'origen ha de ser literatura o font metrològica, incertesa demostrada d'un oracle, requisit de producte aprovat o convergència justificada científicament. Constants «raonables» sense procedència estan prohibides. La manca d'un llindar bloqueja el **primer pas que n'aplica el PASS/FAIL**, no els passos anteriors d'infraestructura o construcció d'oracles. Una revisió posterior és prospectiva i no requalifica el candidat ni el conjunt de validació ja observats.

| Primer gate que aplica el valor | Preregistre obligatori | Evidència necessària |
|---:|---|---|
| 7.4 | `0,01 mag` equivalents, requisit de producte TerraLab3D congelat abans d'avaluar candidats | [Criteri preregistrat](../evidencies/pas7.4/criteri-preregistrat-v1.json) i [homologació del domini tabulat](../evidencies/pas7.4/homologacio-bandset-v1.md); les RSR històriques només són diagnòstiques. |
| 7.12 | Tolerància runtime↔SG-REF abans de la comparació decisòria del candidat | Convergència i incertesa numèrica demostrades per SG-REF a 7.6, mai residuals del runtime candidat. |
| 7.17 | Criteris empírics abans d'avaluar el conjunt reservat `held-out` | Incerteses instrumental, de dades i del model; sense ajustar als residuals observats. |
| 7.22 | SLO de producte TerraLab3D abans de decidir si cal LUT/precomputació/FFT | Requisit de producte aprovat, plataforma i condicions de mesura; si falta, es bloqueja 7.22. |
| 7.28 | Cap valor nou: només consumir els criteris congelats | Evidències i versions dels gates previs. |

Els passos que necessitin un criteri addicional propi el preregistren abans de la seva primera aplicació amb la mateixa política; no traslladen un PASS/FAIL a 7.1 ni creen llindars a 7.28.

**Revisió de contracte 2026-10-18.** El [perfil v1](skyglow-v1-profile.json) i les evidències de 7.1/7.2 són històricament vàlids per a `VNP46A2.002`. El [perfil v2](skyglow-v2-profile.json) amplia la política a tres fonts candidates sense requalificar aquell lector: `VNP46A2.002`/Suomi-NPP, `VJ146A2.002`/NOAA-20 i `VJ246A2.002`/NOAA-21. La [revisió de la User Guide C2 §2.2 Eq. (1) i dos grànuls VJ146 reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) separa la integral instrumental TOA, la radiància Black Marble L3 corregida i la inferència L3→font. **7.3 tanca el contracte de mesura**, inclòs QA 0 real h18v04, mentre que l'homologació d'una RSR/SourceModel operatius de 2026 es resol per domini a 7.5, la incertesa a 7.16 i la validació empírica a 7.17. Cap font es considera homologada per al skyglow nocturn de 2026 només per aparèixer al catàleg o disposar d'una RSR de prelanzament.

El selector futur comprova **dia exacte + AOI + tile + producte/release + QA + model de mesura admissible**. Si hi ha diverses fonts admissibles, la prioritat necessita dades de disponibilitat Black Marble, qualitat, calibratge i cobertura; l'estat primari de NOAA-21 a la distribució general NOAA no decideix la prioritat de Black Marble. La selecció manual avançada conserva la identitat i les limitacions. Cap fallback temporal o entre sensors és silenciós; fonts superposades es retenen separades i no es sumen. Un SBAF requereix gate científic propi. La descoberta, autenticació i instal·lació de grànuls són del [Pas 24](../tasques/pendent/pas24-cataleg-recursos-descarregues.md), que ha de cobrir els tres productes amb un únic gestor.

## Ordre lineal

| Pas | Capacitat | Dependència |
|---:|---|---|
| 7.1 | Contracte científic v1, dades i política d'acceptació | 7, 22.5, 23 |
| 7.2 | Adaptador VNP46 d’observació, qualitat i procedència | 7.1 |
| 7.3 | Model de mesura VIIRS DNB multisatèl·lit, RSR TOA i transformació L3 | 7.1, 7.2 |
| 7.4 | Oracle espectral fi i homologació del SpectralBandSet v1 | 7.3 |
| 7.5 | SourceModel v1: SPD, emissió angular i incertesa | 7.3, 7.4 |
| 7.6 | SG-REF: oracle independent de transport i integració d’àrea | 7.5 |
| 7.7 | PropagationKernel geomètric i benchmark B0 | 7.6 |
| 7.8 | OpticalField tiled i atmosfera estàndard determinista | 7.7 |
| 7.9 | Rayleigh, aerosol de referència i benchmark B1 | 7.8 |
| 7.10 | Kernel espectral complet i absorció gasosa; revalidació de bandes | 7.9, 7.4 |
| 7.11 | Terreny, curvatura i visibilitat física | 7.10 |
| 7.12 | Gate zenital de transport radiomètric | 7.11 |
| 7.13 | Camp angular i DomeProfile sobre ruta directa | 7.12 |
| 7.14 | Projeccions fotomètriques i sensors SQM/TESS; revalidació de bandes | 7.13, 7.4 |
| 7.15 | Atmosfera real ERA5/CAMS i composició de camps | 7.14 |
| 7.16 | Incertesa quantitativa i provenance completa | 7.3, 7.5, 7.15 |
| 7.17 | Validació empírica clear-sky de SourceModel i transport | 7.3, 7.5, 7.16 |
| 7.18 | Watershed, EmissionRegion i quadtree com acceleració B5 | 7.17 |
| 7.19 | Compressió de PhaseFunction i benchmark B3 | 7.18 |
| 7.20 | Forward AD i RadiativeErrorBudget | 7.19 |
| 7.21 | Cache error-based, scheduler latest-wins i prefetch | 7.20 |
| 7.22 | Decisió i backend opcional LUT/precomputació/FFT | 7.21 |
| 7.23 | CloudOpticalState i núvols single-scattering B6 | 7.22 |
| 7.24 | Validació empírica final clear/cloudy i congelació de model | 7.23 |
| 7.25 | Bridge Python→TypeScript i SkyglowRuntime | 7.24 |
| 7.26 | Renderer Three.js lineal i modes diagnòstics | 7.25 |
| 7.27 | Composició lineal del cel i estats reference/instantaneous | 7.26 |
| 7.28 | B7 FULL, SLO i homologació del skyglow artificial | 7.1–7.27 |

## Fases

**A — Contracte científic i inferència (7.1–7.6).** Tanca producte/dades, DNB, espectre, SourceModel i oracle. Quan acaba, la pregunta “què és la font i contra què validem?” ja no està oberta.

**B — Transport directe i gates (7.7–7.17).** Implementa la física sense acceleracions, supera el zenit, construeix all-sky/projeccions i la contrasta amb observacions clear-sky.

**C — Acceleracions homologades (7.18–7.22).** Només ara entren quadtree, fase comprimida, AD, cache i un backend LUT/FFT opcional. Tots es comparen contra la ruta directa.

**D — Núvols i validació final (7.23–7.24).** Amplia el domini atmosfèric i congela què és realment homologable.

**E — Integració i tancament (7.25–7.28).** Bridge, renderer, composició i B7. La UI no decideix física.

## Detall dels gates

### 7.1 — Contracte científic v1, dades i política d'acceptació

**Finalitat.** Convertir les decisions que bloquegen la implementació en un perfil v1 explícit abans d’escriure física de producció.

**Gate de sortida.** Producte i polítiques de dades, `S1`, `F5`, `F7` i abast `F6` permeten iniciar 7.2 i 7.3; `V1` congela política, procedència admissible i distribució dels gates. No exigeix valors numèrics que depenen d'oracles, conjunts de validació o requisits de producte posteriors. **Estat: completat documentalment**; el skyglow físic no està implementat.

**Fitxer executable:** [pas7.1-contracte-cientific-v1.md](../tasques/completat/pas7.1-contracte-cientific-v1.md)

### 7.2 — Adaptador VNP46 d’observació, qualitat i procedència

**Finalitat.** Ingerir la font operativa exacta congelada a 7.1 sense confondre radiància observada amb emissió hemisfèrica.

**Gate de sortida.** Un fixture VNP46 i un grànul real es poden llegir i serialitzar preservant unitats, quality, temps i provenance; cap transformació converteix encara l’observació en SPD o emissió angular. **Estat: completat** amb contrast real de mostres de diagnòstic i fill; QA 0 queda coberta per fixtures.

**Fitxer executable:** [pas7.2-vnp46-observation-adapter.md](../tasques/completat/pas7.2-vnp46-observation-adapter.md)

### 7.3 — Model de mesura VIIRS DNB, RSR real i BAND_INTEGRATED

**Finalitat.** Modelar la resposta DNB per plataforma/producte/release/data i verificar tres contractes diferents: integral espectral SPD/TOA→DNB amb RSR versionada; interpretació de la radiància Black Marble L3 corregida segons la guia NASA; inferència L3→SPD i emissió angular, que correspon a 7.5/7.16/7.17.

La verificació científica amb un grànul J1/J2 real pot emprar una fixture local aportada o obtinguda per recerca offline, amb SHA-256 i procedència, tal com 7.2 va fer amb VNP46. Això permet completar 7.3 sense avançar el wizard del Pas 24; l'adquisició ordinària dels tres productes continua allà.

**Gate de sortida.** Integral TOA, unitats, identitat i repositori RSR reproduïbles; transformació TOA→L3 explícitament documentada per NASA; capa, unitat, QA i procedència L3 contrastades amb dades reals; estats d'homologació RSR explícits per sensor/període. **Estat: completat per al contracte de mesura.** La [User Guide C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) i els [grànuls VJ146 h00v01/h18v04](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md), inclòs QA 0 urbà, satisfan el contracte L3. La RSR efectiva de 2026 i la inferència espectral/angular física no estan homologades; 7.5, 7.16 i 7.17 n'assumeixen els gates.

**Fitxer executable:** [pas7.3-dnb-rsr-measurement.md](../tasques/completat/pas7.3-dnb-rsr-measurement.md)

### 7.4 — Oracle espectral fi i homologació del SpectralBandSet v1

**Finalitat.** Tancar `V3` abans que el nombre de bandes entri al kernel de producció.

**Gate de sortida.** Abans d'avaluar candidats es va congelar el [requisit de producte de 0,01 mag equivalents](../evidencies/pas7.4/criteri-preregistrat-v1.json), amb mètrica, domini, responsable i regla absoluta prop de zero. L'oracle Gauss–Legendre es contrasta amb una integral analítica Decimal de 50 xifres; quadratura, discretització i incertesa RSR consten per separat. **Estat 2026-10-18: completat només per al domini tabulat declarat.** El `SpectralBandSet` adaptatiu d'unió de nusos i Simpson supera [238/238 casos](../evidencies/pas7.4/homologacio-bandset-v1.md), sense triar bandes per rendiment. Les RSR històriques mantenen estat diagnòstic; aquest PASS no homologa cap resposta Black Marble nocturna de 2026 ni el transport atmosfèric. `V3` es revalida en ampliar el domini a 7.10 i 7.14; un error superior al pressupost obliga a versionar les bandes, sense relaxar el criteri.

**Fitxer executable:** [pas7.4-spectral-bandset-validation.md](../tasques/completat/pas7.4-spectral-bandset-validation.md)

### 7.5 — SourceModel v1: SPD, emissió angular i incertesa

**Finalitat.** Tancar `F1` i transformar observacions DNB en una distribució de font explícita, versionada i falsable.

**Gate de sortida.** `F1` queda resolta per al domini d'almenys una font admesa o el pas queda `bloquejat`. Cal acreditar la RSR efectiva/família, mapping de guany i vincle producte/període de la font escollida; una observació L3 tipada produeix `SourceModel` amb priors/ensembles SPD, emissió angular i incertesa estructural justificada, sense aplicar directament la integral TOA al valor L3. Les fonts no acreditades resten indisponibles per a inferència. El lector VNP46 de 7.2 segueix vàlid com a cas concret.

**Fitxer executable:** [pas7.5-source-model-v1.md](../tasques/pendent/pas7.5-source-model-v1.md)

### 7.6 — SG-REF: oracle independent de transport i integració d’àrea

**Finalitat.** Crear una veritat numèrica offline més estricta que el runtime i independent de les seves aproximacions.

**Gate de sortida.** `S1` és executable: SG-REF demostra convergència, quantifica la seva incertesa numèrica i pot comparar radiància espectral per direcció i fonts extenses sense quadtree, cache ni LUT de runtime. Aquesta evidència pot fonamentar la tolerància de 7.12, que no es fixa aquí mirant el runtime.

**Fitxer executable:** [pas7.6-sg-ref-reference-solver.md](../tasques/pendent/pas7.6-sg-ref-reference-solver.md)

### 7.7 — PropagationKernel geomètric i benchmark B0

**Finalitat.** Construir la frontera única de propagació i la instrumentació abans d’afegir scattering.

**Gate de sortida.** B0 és reproduïble i el kernel retorna resultats geomètrics/unitaris sense NaN; zenit és només una direcció del mateix operador.

**Fitxer executable:** [pas7.7-kernel-geometry-b0.md](../tasques/pendent/pas7.7-kernel-geometry-b0.md)

### 7.8 — OpticalField tiled i atmosfera estàndard determinista

**Finalitat.** Donar al kernel un estat atmosfèric offline, versionat i espacialment segmentable abans de connectar reanàlisi.

**Gate de sortida.** El kernel pot recórrer un camp òptic determinista i registrar exactament quins tiles/versions ha utilitzat.

**Fitxer executable:** [pas7.8-optical-field-standard.md](../tasques/pendent/pas7.8-optical-field-standard.md)

### 7.9 — Rayleigh, aerosol de referència i benchmark B1

**Finalitat.** Introduir la primera física de scattering sobre la ruta directa i auditable.

**Gate de sortida.** B1 implementa Rayleigh/aerosol d'una banda amb invariants físics i comparació diagnòstica reproduïble contra SG-REF. El PASS/FAIL numèric runtime↔SG-REF es reserva a 7.12.

**Fitxer executable:** [pas7.9-rayleigh-aerosol-b1.md](../tasques/pendent/pas7.9-rayleigh-aerosol-b1.md)

### 7.10 — Kernel espectral complet i absorció gasosa

**Finalitat.** Passar del B1 monocromàtic a transport espectral v1 complet amb absorció.

**Gate de sortida.** La ruta directa clear-sky espectral supera invariants de banda, unitats i absorció, amb comparació diagnòstica reproduïble contra SG-REF i l'oracle espectral; cap absorció es tracta com zero per conveniència. També revalida el pressupost de discretització `0,01 mag` de 7.4 amb absorció gasosa i dispersió espectral. Si falla, revisa i versiona el `SpectralBandSet` i repeteix la validació sense relaxar el criteri. El PASS/FAIL numèric de transport és 7.12.

**Fitxer executable:** [pas7.10-gas-spectral-kernel.md](../tasques/pendent/pas7.10-gas-spectral-kernel.md)

### 7.11 — Terreny, curvatura i visibilitat física

**Finalitat.** Afegir l’oclusió i la geometria terrestre a la ruta directa abans del gate zenital.

**Gate de sortida.** Els casos sintètics de terreny/curvatura verifiquen topologia i oclusió, comparen diagnòsticament amb SG-REF i detecten els flips com a discontinuïtats. El PASS/FAIL numèric de transport és 7.12.

**Fitxer executable:** [pas7.11-terrain-curvature.md](../tasques/pendent/pas7.11-terrain-curvature.md)

### 7.12 — Gate zenital de transport radiomètric

**Finalitat.** Validar el transport complet abans de cúpules, compressions o caches.

**Gate de sortida.** Abans de comparar el candidat, es preregistra la tolerància runtime↔SG-REF amb origen justificat, que pot usar la convergència/incertesa de SG-REF demostrades a 7.6 però mai els residuals del runtime candidat. Sense tolerància justificada, 7.12 es bloqueja. El mateix `PropagationKernel` supera el gate al zenit sense calibratge arbitrari; el PASS valida transport donat un SourceModel, no la inferència d'emissió.

**Fitxer executable:** [pas7.12-zenith-transport-gate.md](../tasques/pendent/pas7.12-zenith-transport-gate.md)

### 7.13 — Camp angular i DomeProfile sobre ruta directa

**Finalitat.** Estendre el mateix operador homologat del zenit a direccions arbitràries sense acceleracions de fonts.

**Gate de sortida.** `DomeProfile` reprodueix zenit i camp angular directe dins el pressupost V1 aplicable; si cal una mètrica angular nova, el seu valor justificat es preregistra abans de comparar el candidat a 7.13. La compressió angular té error quantificat independent.

**Fitxer executable:** [pas7.13-dome-profile-direct.md](../tasques/pendent/pas7.13-dome-profile-direct.md)

### 7.14 — Projeccions fotomètriques i sensors SQM/TESS

**Finalitat.** Projectar radiància espectral física a magnituds/instruments sense retroalimentar el kernel.

**Gate de sortida.** SQM/TESS/CIE coincideixen amb oracles de projecció dins toleràncies justificades i preregistrades a 7.14 abans de comparar el candidat; sense justificació, 7.14 es bloqueja. Revalida també el pressupost de discretització `0,01 mag` de 7.4 per a les projeccions reals; si falla, versiona i rehomologa el `SpectralBandSet` sense relaxar el criteri. Cap projecció modifica la radiància física.

**Fitxer executable:** [pas7.14-photometric-projections.md](../tasques/pendent/pas7.14-photometric-projections.md)

### 7.15 — Atmosfera real ERA5/CAMS i composició de camps

**Finalitat.** Substituir el provider estàndard per dades reals sense canviar la física del kernel.

**Gate de sortida.** El mateix kernel pot executar atmosfera estàndard o real amb contracte idèntic i provenance completa; fixtures reanàlisi són reproduïbles.

**Fitxer executable:** [pas7.15-atmos-era5-cams.md](../tasques/pendent/pas7.15-atmos-era5-cams.md)

### 7.16 — Incertesa quantitativa i provenance completa

**Finalitat.** Construir intervals i components d’error després que font, atmosfera i transport ja tinguin models concrets.

**Gate de sortida.** Cada resultat físic separa incertesa RSR i mapping de guany, correcció Black Marble L3, prior SPD/angular, radiometria, atmosfera, model estructural i error numèric, amb correlacions i domini per sensor. Una incertesa no quantificada queda explícita i impedeix l'homologació que en depèn; no hi ha sigmes fictícies.

**Fitxer executable:** [pas7.16-uncertainty-provenance.md](../tasques/pendent/pas7.16-uncertainty-provenance.md)

### 7.17 — Validació empírica clear-sky de SourceModel i transport

**Finalitat.** Contrastar el sistema físic directe amb observacions externes abans de qualsevol acceleració espacial o cache.

**Gate de sortida.** Els criteris empírics, amb incerteses instrumental, de dades i del model, es preregistren abans de mirar el conjunt reservat `held-out`; inclouen estrats per plataforma/producte/release quan s'hagin admès. Sense criteris justificats, 7.17 es bloqueja. Existeix una validació clear-sky reproduïble; si el SourceModel no compleix el domini declarat, el pas falla i torna a 7.5, sense calibratge compensatori del kernel ni ajust als residuals observats.

**Fitxer executable:** [pas7.17-clear-sky-ground-truth.md](../tasques/pendent/pas7.17-clear-sky-ground-truth.md)

### 7.18 — Watershed, EmissionRegion i quadtree com acceleració B5

**Finalitat.** Comprimir fonts només després de disposar d’una integració directa d’àrea validada.

**Gate de sortida.** La ruta comprimida és una acceleració demostrablement equivalent dins pressupost al baseline directe; punt vs àrea queda validat en camp proper.

**Fitxer executable:** [pas7.18-source-spatial-acceleration.md](../tasques/pendent/pas7.18-source-spatial-acceleration.md)

### 7.19 — Compressió de PhaseFunction i benchmark B3

**Finalitat.** Aproximar la fase només contra la representació de referència ja validada.

**Gate de sortida.** La fase accelerada té domini i error explícits i compleix V1; si cap candidat ho fa, el runtime conserva la fase de referència.

**Fitxer executable:** [pas7.19-phase-acceleration-b3.md](../tasques/pendent/pas7.19-phase-acceleration-b3.md)

### 7.20 — Forward AD i RadiativeErrorBudget

**Finalitat.** Crear cotes conservadores per reutilització/pruning sense convertir l’AD en part de la física autoritativa.

**Gate de sortida.** Existeix una cota d’error auditable per moviments/pertorbacions suaus i una regla explícita per discontinuïtats. El contracte és reutilitzable pel cel físic 7.62.

**Fitxer executable:** [pas7.20-ad-error-budget.md](../tasques/pendent/pas7.20-ad-error-budget.md)

### 7.21 — Cache error-based, scheduler latest-wins i prefetch

**Finalitat.** Fer interactiu el runtime sense alterar el resultat físic.

**Gate de sortida.** Cap integral s’executa per frame; teleports i flips d’oclusió fan miss; small-motion només hit dins `RadiativeErrorBudget`; no hi ha stale swap.

**Fitxer executable:** [pas7.21-cache-scheduler.md](../tasques/pendent/pas7.21-cache-scheduler.md)

### 7.22 — Decisió i backend opcional LUT/precomputació/FFT

**Finalitat.** Afegir una acceleració global només si la ruta directa+cache no compleix els SLO de producte TerraLab3D aprovats.

**Gate de sortida.** Abans d'usar-los per decidir LUT/precomputació/FFT, els SLO de producte es fixen amb aprovació, plataforma i condicions de mesura; no són constants científiques. Si manca el requisit aprovat, 7.22 queda bloquejat. Després, o bé hi ha evidència que no cal backend addicional, o bé existeix un backend accelerat homologat contra la ruta directa amb domini/error/fallback explícits.

**Fitxer executable:** [pas7.22-optional-runtime-acceleration.md](../tasques/pendent/pas7.22-optional-runtime-acceleration.md)

### 7.23 — CloudOpticalState i núvols single-scattering B6

**Finalitat.** Incorporar núvols com a estat òptic físic i no com un multiplicador arbitrari.

**Gate de sortida.** B6 és incremental, reproduïble i compleix el pressupost del domini cloud declarat; `CloudOpticalState` no conté lògica específica del skyglow.

**Fitxer executable:** [pas7.23-clouds-b6.md](../tasques/pendent/pas7.23-clouds-b6.md)

### 7.24 — Validació empírica final clear/cloudy i congelació de model

**Finalitat.** Repetir la validació del sistema ja optimitzat i amb núvols abans d’integrar-lo al renderer.

**Gate de sortida.** Existeix un informe empíric final per plataforma/producte/release i domini homologable; superposicions entre sensors es contrasten sense sumar ni aplicar SBAF per defecte. Si només clear-sky és defensable, el domini de producció queda explícitament limitat i cloud no es declara homologat.

**Fitxer executable:** [pas7.24-full-ground-truth.md](../tasques/pendent/pas7.24-full-ground-truth.md)

### 7.25 — Bridge Python→TypeScript i SkyglowRuntime

**Finalitat.** Transportar resultats físics ja homologats sense portar integració radiativa al frontend.

**Gate de sortida.** TypeScript pot rebre/validar/swap resultats de skyglow amb revisió monotònica i sense executar física de propagació.

**Fitxer executable:** [pas7.25-bridge-runtime.md](../tasques/pendent/pas7.25-bridge-runtime.md)

### 7.26 — Renderer Three.js lineal i modes diagnòstics

**Finalitat.** Renderitzar radiància artificial lineal amb doble buffer i fer-la inspeccionable sense alterar-la.

**Gate de sortida.** El renderer mostra el camp artificial sense càlcul radiatiu per frame, descarta resultats tardans i els modes debug OFF no alteren física ni rendiment materialment.

**Fitxer executable:** [pas7.26-three-renderer-debug.md](../tasques/pendent/pas7.26-three-renderer-debug.md)

### 7.27 — Composició lineal del cel i estats reference/instantaneous

**Finalitat.** Integrar el canal artificial amb la resta del cel sense doble comptatge ni calibratge creuat.

**Gate de sortida.** El skyglow artificial conserva identitat i provenance dins la composició; la Lluna/crepuscle no canvien la inferència artificial i `reference` és invariant als components instantanis.

**Fitxer executable:** [pas7.27-sky-composition.md](../tasques/pendent/pas7.27-sky-composition.md)

### 7.28 — B7 FULL, SLO i homologació del skyglow artificial

**Finalitat.** Tancar la vertical només després que ciència, rendiment i integració hagin passat gates independents.

**Regla d'homologació.** 7.28 només consumeix els criteris congelats als gates previs i les seves versions; no crea ni modifica cap llindar PASS/FAIL.

**Gate de sortida.** La vertical queda `completat` només si no hi ha decisions bloquejants ocultes, tots els gates preregistrats passen i el domini científic homologat inclou explícitament plataforma/producte/release/període/QA. Una altra plataforma pot continuar pendent sense falsificar l'abast completat. En cas contrari roman parcial/bloquejada amb fallback legacy.

**Fitxer executable:** [pas7.28-b7-homologacio-skyglow.md](../tasques/pendent/pas7.28-b7-homologacio-skyglow.md)

## Canvis respecte del pla substituït

El gate zenital deixa de dependre de cache, AD, ERA5/CAMS, quadtree o d’un oracle futur del cel solar/lunar. Ara es valida aviat amb atmosfera estàndard, fonts directes i `SG-REF`. La validació empírica clear-sky també passa abans de les acceleracions.

`EmissionRegion`/watershed/quadtree, Legendre, AD/cache i LUT/FFT deixen de ser peces prèvies a la veritat física i passen a ser **backends d’optimització**. Aquesta és la diferència essencial per a una execució segura pas a pas per Codex.

## Relació amb 7.51+

El cel solar/lunar 7.51+ continua separat. Comparteix contractes neutrals quan té sentit (`RadiativeErrorBudget`, `CloudOpticalState`, estat geodèsic/òptic), però no integradors. El skyglow ja no depèn del reference solver 7.65: `SG-REF` és propi de 7.6.
