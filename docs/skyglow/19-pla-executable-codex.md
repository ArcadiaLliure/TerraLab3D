# Pla executable canònic del skyglow per a Codex

> Estat: pendent d’implementació. Aquest document substitueix l’ordre executable anterior de 7.1–7.28. La numeració es conserva per compatibilitat amb la vertical 7.51+, **no** per preservar la descomposició antiga.

## Regla d’execució

Codex executa un únic pas cada vegada. No pot començar el següent fins que el criteri de sortida de l’actual estigui verificat amb proves/evidències i l’estat/documentació s’hagi actualitzat. Si una dada o decisió científica imprescindible **per al domini de sortida del pas** no es pot justificar amb una font autoritativa o evidència reproduïble, el pas passa a `bloquejat` i la seqüència s’atura. La manca d'una RSR instrumental de 2026 limita H; C admet referència documentada del mateix sensor.

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
| 7.17 | Criteris empírics abans d'avaluar el conjunt reservat `held-out` |Incerteses instrumental, de dades i del model; sense ajustar als residuals observats., 7.5.1 |
| 7.22 | SLO de producte TerraLab3D abans de decidir si cal LUT/precomputació/FFT | Requisit de producte aprovat, plataforma i condicions de mesura; si falta, es bloqueja 7.22. |
| 7.28 | Cap valor nou: només consumir els criteris congelats |Evidències i versions dels gates previs., 7.5.1 |

Els passos que necessitin un criteri addicional propi el preregistren abans de la seva primera aplicació amb la mateixa política; no traslladen un PASS/FAIL a 7.1 ni creen llindars a 7.28.

**Revisió de contracte 2026-10-18.** El [perfil v1](skyglow-v1-profile.json) i les evidències de 7.1/7.2 són històricament vàlids per a `VNP46A2.002`. El [perfil v2](skyglow-v2-profile.json) amplia la política a tres fonts candidates sense requalificar aquell lector: `VNP46A2.002`/Suomi-NPP, `VJ146A2.002`/NOAA-20 i `VJ246A2.002`/NOAA-21. La [revisió de la User Guide C2 §2.2 Eq. (1) i dos grànuls VJ146 reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) separa la integral instrumental TOA, la radiància Black Marble L3 corregida i la inferència L3→font. **7.3 tanca el contracte de mesura**, inclòs QA 0 real h18v04. **7.5 completa una font definida S sense observació VIIRS**; 7.5.1 implementa C relatiu amb RSR pública de referència; incertesa propagada i homologació H es tracten a 7.16–7.24. Cap font urbana es considera homologada per aparèixer al catàleg o disposar d'una RSR de prelanzament.

El selector futur comprova **dia exacte + AOI + tile + producte/release + QA + model de mesura admissible**. Si hi ha diverses fonts admissibles, la prioritat necessita dades de disponibilitat Black Marble, qualitat, calibratge i cobertura; l'estat primari de NOAA-21 a la distribució general NOAA no decideix la prioritat de Black Marble. La selecció manual avançada conserva la identitat i les limitacions. Cap fallback temporal o entre sensors és silenciós; fonts superposades es retenen separades i no es sumen. Un SBAF requereix gate científic propi. La descoberta, autenticació i instal·lació de grànuls són del [Pas 24](../tasques/pendent/pas24-cataleg-recursos-descarregues.md), que ha de cobrir els tres productes amb un únic gestor.

## Revisió prospectiva: fonts S, escenaris C i homologació H

La [nova política RSR/dominis](20-politica-rsr-i-validacio-per-dominis.md) elimina l'obligació de RSR exacta 2026 a 7.5. **S** construeix una font física independent; C relatiu s’incorpora a 7.5.1 i ambdós alimenten 7.6–7.15; **C** assaja Black Marble amb hipòtesis SPD/angular i RSR pública de referència, no invertible de forma única; **H** només es declara després de validació independent. NOAA-20/VJ146A2.002 és la **primera parella experimental** amb RSR prelanzament, no una certificació nocturna 2026. 7.5.1 implementa C abans de SG-REF; 7.16 en propagarà les incerteses, 7.17 separarà gate numèric S/C de gate empíric H, i 7.24/7.28 mantindran estats per domini. Cap resultats ni llindars de 7.1–7.4 no es requalifiquen.

## Ordre lineal

| Pas | Capacitat | Dependència |
|---:|---|---|
| 7.1 | Contracte científic v1, dades i política d'acceptació | 7, 22.5, 23 |
| 7.2 | Adaptador VNP46 d’observació, qualitat i procedència | 7.1 |
| 7.3 | Model de mesura VIIRS DNB multisatèl·lit, RSR TOA i transformació L3 | 7.1, 7.2 |
| 7.4 | Oracle espectral fi i homologació del SpectralBandSet v1 | 7.3 |
| 7.5 | SourceModel S independent; admissibilitat L3 separada | 7.3, 7.4 |
| 7.5.1 | Black Marble real, biblioteca CIE, modalitats K/realista i UI científica | 7.5 |
| 7.6 | SG-REF compartit per S i C, oracle independent i integració d’àrea | 7.5, 7.5.1 |
| 7.7 | PropagationKernel geomètric i benchmark B0 | 7.6 |
| 7.8 | OpticalField tiled i atmosfera estàndard determinista | 7.7 |
| 7.9 | Rayleigh, aerosol de referència i benchmark B1 | 7.8 |
| 7.10 | Kernel espectral complet i absorció gasosa; revalidació de bandes | 7.9, 7.4, 7.5.1 |
| 7.11 | Terreny, curvatura i visibilitat física | 7.10 |
| 7.12 | Gate zenital de transport radiomètric | 7.11 |
| 7.13 | Camp angular i DomeProfile sobre ruta directa | 7.12 |
| 7.14 | Projeccions fotomètriques i sensors SQM/TESS; revalidació de bandes | 7.13, 7.4, 7.5.1 |
| 7.15 | Atmosfera real ERA5/CAMS i composició de camps | 7.14 |
| 7.16 | Incertesa S/C i propagació de sensibilitat espectral/angular | 7.3, 7.5, 7.5.1, 7.15 |
| 7.17 | Gate de transport S; validació empírica C/H separada | 7.3, 7.5(S), 7.16, 7.5.1 |
| 7.18 | Watershed, EmissionRegion i quadtree com acceleració B5 | 7.17 |
| 7.19 | Compressió de PhaseFunction i benchmark B3 | 7.18 |
| 7.20 | Forward AD i RadiativeErrorBudget | 7.19 |
| 7.21 | Cache error-based, scheduler latest-wins i prefetch | 7.20 |
| 7.22 | Decisió i backend opcional LUT/precomputació/FFT | 7.21 |
| 7.23 | CloudOpticalState i núvols single-scattering B6 | 7.22 |
| 7.24 | Validació empírica final clear/cloudy i congelació de model | 7.23, 7.5.1 |
| 7.25 | Bridge Python→TypeScript i SkyglowRuntime | 7.24, 7.5.1 |
| 7.26 | Renderer Three.js lineal i modes diagnòstics | 7.25, 7.5.1 |
| 7.27 | Composició lineal del cel i estats reference/instantaneous | 7.26, 7.5.1 |
| 7.28 | B7 FULL, SLO i homologació del skyglow artificial | 7.1–7.27, 7.5.1 |

## Fases

**A — Contracte científic i font física definida (7.1–7.6).** Conserva dades/DNB i discretització; tanca un SourceModel S de SPD, emissió angular i escala definides, i crea l'oracle SG-REF. Inclou escenaris C relatius des de L3 a 7.5.1, sense reconstrucció única ni homologació H.

**B — Transport directe i gates per domini (7.7–7.17).** Implementa el transport compartit S/C sense acceleracions, supera el zenit, construeix all-sky/projeccions i valida el transport amb un oracle independent. La comparació empírica Black Marble C/H és un gate separat i només s'aplica si hi ha observacions i criteris justificats.

**C — Acceleracions homologades per domini (7.18–7.22).** Només ara entren quadtree, fase comprimida, AD, cache i un backend LUT/FFT opcional. Es comparen contra la ruta directa dels dominis S/C verificats; no hereten una homologació C/H absent.

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

**Finalitat.** Modelar la resposta DNB per plataforma/producte/release/data i verificar tres contractes diferents: integral espectral SPD/TOA→DNB amb RSR versionada; interpretació de la radiància Black Marble L3 corregida segons la guia NASA; inferència L3→SPD i emissió angular, que correspon a C/H de 7.16–7.24. La font definida S independent correspon a 7.5.

La verificació científica amb un grànul J1/J2 real pot emprar una fixture local aportada o obtinguda per recerca offline, amb SHA-256 i procedència, tal com 7.2 va fer amb VNP46. Això permet completar 7.3 sense avançar el wizard del Pas 24; l'adquisició ordinària dels tres productes continua allà.

**Gate de sortida.** Integral TOA, unitats, identitat i repositori RSR reproduïbles; transformació TOA→L3 explícitament documentada per NASA; capa, unitat, QA i procedència L3 contrastades amb dades reals; estats d'homologació RSR explícits per sensor/període. **Estat: completat per al contracte de mesura.** La [User Guide C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) i els [grànuls VJ146 h00v01/h18v04](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md), inclòs QA 0 urbà, satisfan el contracte L3. La RSR efectiva de 2026 i la inferència espectral/angular observacional no estan homologades; 7.16–7.24 n'assumeixen els gates C/H.

**Fitxer executable:** [pas7.3-dnb-rsr-measurement.md](../tasques/completat/pas7.3-dnb-rsr-measurement.md)

### 7.4 — Oracle espectral fi i homologació del SpectralBandSet v1

**Finalitat.** Tancar `V3` abans que el nombre de bandes entri al kernel de producció.

**Gate de sortida.** Abans d'avaluar candidats es va congelar el [requisit de producte de 0,01 mag equivalents](../evidencies/pas7.4/criteri-preregistrat-v1.json), amb mètrica, domini, responsable i regla absoluta prop de zero. L'oracle Gauss–Legendre es contrasta amb una integral analítica Decimal de 50 xifres; quadratura, discretització i incertesa RSR consten per separat. **Estat 2026-10-18: completat només per al domini tabulat declarat.** El `SpectralBandSet` adaptatiu d'unió de nusos i Simpson supera [238/238 casos](../evidencies/pas7.4/homologacio-bandset-v1.md), sense triar bandes per rendiment. Les RSR històriques mantenen estat diagnòstic; aquest PASS no homologa cap resposta Black Marble nocturna de 2026 ni el transport atmosfèric. `V3` es revalida en ampliar el domini a 7.10 i 7.14; un error superior al pressupost obliga a versionar les bandes, sense relaxar el criteri.

**Fitxer executable:** [pas7.4-spectral-bandset-validation.md](../tasques/completat/pas7.4-spectral-bandset-validation.md)

### 7.5 — SourceModel físic independent (S)

**Finalitat.** Definir SPD, geometria, emissió angular i amplitud física explícita d'una font sense satèl·lit. L'admissibilitat Black Marble és una branca C/H separada.

**Gate de sortida.** Constructor `SourceModel` S versionat, normalització, unitats, fixtures, conservació i tests independents; **no** cal RSR operativa 2026 ni inferència L3. **Estat: completat en el domini S declarat** amb [SPD CIE verificades, geometries i proves de conservació](../evidencies/pas7.5/validacio-source-model-s-v1.md). El gate L3 continua separat i sense font H admissible.

**Fitxer executable:** [pas7.5-source-model-v1.md](../tasques/completat/pas7.5-source-model-v1.md)

### 7.5.1 — Black Marble i configuració espectral executable

**Finalitat i estat.** Biblioteca CIE, RSR pública de referència NOAA-20, ancoratge L3 relatiu, ensembles deterministes i intervencions K amb magnitud conservada. Controls a «Contaminació lumínica» connectats a Python; completat en el domini relatiu declarat.

**UI obligatòria.** Selector «Simulació realista» / «Simulació per kelvins»; etiqueta superior «Temperatura de color», lliscant horitzontal, mínim 2.800 K a l’esquerra, màxim 6.500 K a la dreta, valor actual visible i etiqueta inferior «Exemple: ...». Família LED CIE estable i font visibles. Teclat, ratolí i tacte; exemple informatiu sense canvi silenciós de tecnologia.

**Gate de sortida.** El mateix grànul NOAA-20 amb QA 0 alimenta ambdues modalitats i retorna `SourceModel` C amb unitats relatives, SPD, angles, procedència i normalització coherent. Cap resultat atmosfèric inventat. La connexió a radiància/render continua obligatòria a 7.25–7.27.

**Fitxer executable:** [pas7.5.1-black-marble-spectral-simulation.md](../tasques/completat/pas7.5.1-black-marble-spectral-simulation.md).

### 7.6 — SG-REF: oracle independent de transport i integració d’àrea

**Finalitat.** Crear una veritat numèrica offline més estricta que el runtime i independent de les seves aproximacions, utilitzant fonts S definides i C relatives de 7.5.1 amb el mateix contracte de transport; S no requereix RSR i C conserva la seva referència/hipòtesis.

**Gate de sortida.** `S1` és executable: SG-REF demostra convergència, quantifica la seva incertesa numèrica i pot comparar radiància espectral per direcció i fonts extenses sense quadtree, cache ni LUT de runtime. Aquesta evidència pot fonamentar la tolerància de 7.12, que no es fixa aquí mirant el runtime.

**Estat verificat:** completat offline en el slab espectral homogeni pla: integració d’àrea/raster, 401 nusos CIE, fases fines, contrast F5 Monte Carlo i 18 alternatives C reals. [Convergència, errors i límits](../evidencies/pas7.6/validacio-sg-ref.md). Els nous medis/geometries de 7.8–7.11 requeriran ampliar i revalidar la referència abans dels seus contrasts; cap gate runtime/H anticipat.

**Fitxer executable:** [pas7.6-sg-ref-reference-solver.md](../tasques/completat/pas7.6-sg-ref-reference-solver.md)

### 7.7 — PropagationKernel geomètric i benchmark B0

**Finalitat.** Construir la frontera única de propagació i la instrumentació abans d’afegir scattering.

**Gate de sortida.** B0 és reproduïble i el kernel retorna resultats geomètrics/unitaris sense NaN; zenit és només una direcció del mateix operador.

**Estat verificat:** completat geomètricament, amb esfera ECEF/ENU, segmentació, GK7/15 propi i guard de revisions; 48 proves noves, 330 proves backend i 180 passades B0. [Resultats i límits](../evidencies/pas7.7/validacio-b0.md). No calcula encara radiància ni implementa OpticalField.

**Fitxer executable:** [pas7.7-kernel-geometry-b0.md](../tasques/completat/pas7.7-kernel-geometry-b0.md)

### 7.8 — OpticalField tiled i atmosfera estàndard determinista

**Finalitat.** Donar al kernel un estat atmosfèric offline, versionat i espacialment segmentable abans de connectar reanàlisi.

**Gate de sortida.** El kernel pot recórrer un camp òptic determinista i registrar exactament quins tiles/versions ha utilitzat.

**Estat verificat:** completat per a camp COESA sec P/T/n, interpolació, dependències exactes i fixtures 1/2/8 tiles. 33 proves noves, 363 proves backend, B0 idèntic i oracle GK21 independent de columnes; sense dispersió ni radiància. [Resultats i límits](../evidencies/pas7.8/validacio-optical-field.md).

**Fitxer executable:** [pas7.8-optical-field-standard.md](../tasques/completat/pas7.8-optical-field-standard.md)

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

### 7.16 — Incertesa i escenaris Black Marble condicionats C

**Finalitat.** Construir el ledger físic/numèric de S/C i propagar incertesa dels escenaris de 7.5.1 amb hipòtesis SPD/angular i referències RSR identificades. NOAA-20 VJ146A2.002 és la primera parella experimental, no una cadena calibrada 2026.

**Gate de sortida.** Per S, provenance i incerteses numèriques/físiques o absències explícites; per C, escenaris condicionats amb incerteses declarades o indisponibilitat de calibratge absolut. L'absència d'evidència H no bloqueja el ledger S. Cap sigma fictícia.

**Fitxer executable:** [pas7.16-uncertainty-provenance.md](../tasques/pendent/pas7.16-uncertainty-provenance.md)

### 7.17 — Gate de transport S/C preacceleracions; empírica C/H separada

**Finalitat.** Verificar transport de fonts S/C contra SG-REF i altres oracles independents abans d'accelerar; si hi ha dades adequades, validar empíricament C/H per separat.

**Gate de sortida.** Criteri numèric S científicament justificat i preregistrat, sense ajustar-lo als residuals del candidat; superar-lo habilita acceleracions dels dominis de transport S/C verificats. El gate observacional de C/H exigeix `held-out`, criteris preregistrats, incerteses i observacions independents; si no existeixen, `not_evaluated`, mai PASS empíric. La manca de RSR exacta 2026 no bloqueja les acceleracions dels dominis de transport S/C verificats.

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

### 7.24 — Validació final clear/cloudy per dominis S/C/H

**Finalitat.** Reexecutar gates S del transport optimitzat i núvols; publicar C/H només si hi ha validació observacional independent.

**Gate de sortida.** Informes reproduïbles amb S validat en el seu domini i C/H `conditional`, `not_evaluated` o `validated` segons proves específiques. Permetre integració etiquetada de S sense presentar el skyglow derivat de L3 com a predicció absoluta calibrada.

**Fitxer executable:** [pas7.24-full-ground-truth.md](../tasques/pendent/pas7.24-full-ground-truth.md)

### 7.25 — Bridge Python→TypeScript i SkyglowRuntime

**Finalitat.** Transportar resultats físics versionats i qualificats S/C/H, sense portar integració radiativa al frontend ni representar un escenari C com una predicció H.

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

**Gate de sortida.** El motor S es pot completar com a simulació física amb els seus gates; C només es pot presentar com a condicional; H exigeix validació observacional per plataforma/producte/release/període/QA amb incertesa i preregistre. No confondre un PASS numèric S amb skyglow urbà absolut real homologat.

**Fitxer executable:** [pas7.28-b7-homologacio-skyglow.md](../tasques/pendent/pas7.28-b7-homologacio-skyglow.md)

## Canvis respecte del pla substituït

El gate zenital deixa de dependre de cache, AD, ERA5/CAMS, quadtree o d’un oracle futur del cel solar/lunar. Ara es valida aviat amb atmosfera estàndard, fonts directes i `SG-REF`. La validació empírica clear-sky també passa abans de les acceleracions.

`EmissionRegion`/watershed/quadtree, Legendre, AD/cache i LUT/FFT deixen de ser peces prèvies a la veritat física i passen a ser **backends d’optimització**. Aquesta és la diferència essencial per a una execució segura pas a pas per Codex.

## Relació amb 7.51+

El cel solar/lunar 7.51+ continua separat. Comparteix contractes neutrals quan té sentit (`RadiativeErrorBudget`, `CloudOpticalState`, estat geodèsic/òptic), però no integradors. El skyglow ja no depèn del reference solver 7.65: `SG-REF` és propi de 7.6.
