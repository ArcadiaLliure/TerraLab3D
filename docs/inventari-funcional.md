# Inventari funcional verificat

Aquest inventari separa tres realitats que abans es barrejaven:

- **observable**: la capacitat està connectada a l'entrypoint real, produeix comportament visible i té proves/evidències;
- **parcial**: existeix una vertical útil, però no cobreix encara el resultat funcional consolidat;
- **esquelet**: hi ha models, càlculs, ports o interfícies de renderer, però no una experiència executable de punta a punta.

La font de veritat de l'ordre i del tancament és el [pla de millores](README.md). L'existència d'un directori sota [`domain/`](../backend/src/terralab3d/domain/) no certifica implementació.

## Capacitats observables

| Capacitat | Evidència principal | Abast verificat |
|---|---|---|
| Entorn, càmera, bridge, observador i temps | [Passos 1–4](README.md#passos-completats) | Entrada real, escena, càmera, ubicació, temps i HUD. |
| Gaia, picking i selecció | [Passos 5–6 i 12–13](README.md#passos-completats) | Catàleg real/fallback declarat, buffers retinguts, cerca, picking i inspecció. |
| Cel, atmosfera i contaminació lumínica | [Pas 7](tasques/completat/pas7.md) | Dia/nit/crepuscle, Bortle i magnitud límit; meteorologia real queda fora. |
| Sistema Solar i il·luminació | [Passos 8, 8.5, 8.6 i 8.7](README.md#passos-completats) | Posicions/aparença, Lluna, actius planetaris i il·luminació física. |
| Eclipsis i trajectòries solars | [Pas 9](tasques/completat/pas9.md) | Cerca SPICE, separacions i trajectòries aparents de cossos suportats. |
| Via Làctia i cel profund | [Passos 10–11](README.md#passos-completats) | Planck/galàctic i catàleg OpenNGC renderitzats. |
| Traces circumpolars | [Pas 14](tasques/completat/pas14.md) | Exposició temporal i renderer incremental. |
| Horitzó i terreny | [Passos 15–16](README.md#passos-completats) | DEM local, perfil/oclusió, malla retinguda, tiles, LOD i picking. |
| Òptica i observació instrumental | [`ObservationModeController.ts`](../frontend/src/application/ObservationModeController.ts), [`observation_coordinator.py`](../backend/src/terralab3d/application/observation_coordinator.py) i [Pas 19](tasques/completat/pas19-modes-optics.md) | Modes `eye/camera/telescope`, overlays retinguts, fotometria V1, perfils persistents, GoTo i Gaia profunda cancel·lable. |
| Eines de mesura esfèrica | [Pas 21](tasques/completat/pas21-eines-mesura.md) | Quatre eines esfèriques editables (regla, quadrat, rectangle, cercle), historial undo/redo, batches retinguts, labels projectats i persistència versionada. |
| Trajectòries i visibilitat sobre l'horitzó real | [Pas 22](tasques/completat/pas22-trajectories-visibilitat.md) | Trajectòries temporals d'objectes observables (cossos solars, satèl·lits, estrelles, cel profund, coordenades), classificació contra relleu real (DEM) i astronòmic, creuaments refinats, marcadors temporals, homologació visual en navegador i evidències. |
| Constel·lacions IAU, figures pròpies i estil d'overlays | [Pas 23](tasques/completat/pas23-constellacions.md) | Catàleg immutable de 88 constel·lacions IAU, Serpens desconnectada, cerca i seguiment del centre amb el Pas 22, snapping i edició d'usuari (16 px CSS), persistència atòmica `constellations.v1.json` i estil compartit `OverlayLineStyle` de nucli definit i halo subtil per a constel·lacions, mesures, NGC i trajectòries. |

## Capacitats parcials

| Capacitat | Implementació observable actual | Què no s'ha de donar per fet | Pla |
|---|---|---|---|
| Superfície categòrica | [`land_cover_coordinator.py`](../backend/src/terralab3d/application/land_cover_coordinator.py), adaptadors raster i [`LandCoverTextureManager.ts`](../frontend/src/view/three/terrain/LandCoverTextureManager.ts) | El refinament visual/semàntic avançat queda consolidat al Pas 29. | [17](tasques/completat/pas17-superficie-progressiva.md), [29](tasques/pendent/pas29-superficie-semantica.md) |
| Catàleg de recursos i descàrregues | Catàleg de manifests i descàrregues bàsiques | Gestor de capes integrat i selecció interactiva d'AOI | [24](tasques/pendent/pas24-cataleg-recursos-descarregues.md) |
| Recursos del Sistema Solar | Posicions i textures planetàries bàsiques | Gestor unificat de recursos i textures d'alta resolució | [26](tasques/pendent/pas26-recursos-sistema-solar.md) |
| Recursos d'espai profund | Catàleg OpenNGC i pols Planck carregats | Carta d'espai profund interactiva i descàrrega progressiva | [27](tasques/pendent/pas27-recursos-espai-profund.md) |
| DEM multiproveïdor | Carregador DEM local i tiling retingut | Descobriment automàtic de proveïdors i mosaic dinàmic | [28](tasques/pendent/pas28-dem-multiproveidor.md) |
| Superfície semàntica i TLST | Superfície categòrica base (Pas 17) | TLST, ontologia i arbre de refinament semàntic | [29](tasques/pendent/pas29-superficie-semantica.md) |
| Motor general d'efemèrides | Càlculs puntuals SPICE i DE440 | Motor generalitzat per a qualsevol cos i rang temporal | [32](tasques/pendent/pas32-motor-efemerides.md) |
| Cercador d'objectes i efemèrides | Cerca bàsica d'estrelles i cel profund | Cercador multipestanya amb efemèrides integrades | [33](tasques/pendent/pas33-cercador-objectes-efemerides.md) |
| Pestanya d'eclipsis | Cerca d'eclipsis puntuals SPICE | Pestanya interactiva d'eclipsis amb circumstàncies locals | [35](tasques/pendent/pas35-pestanya-eclipsis.md) |
| Esdeveniments de planetes i Lluna | Esdeveniments bàsics solars | Esdeveniments propis per cos amb visualització | [36](tasques/pendent/pas36-esdeveniments-objectes.md) |

## Capacitats en esquelet o pendents

| Capacitat | Estat actual | Pla |
|---|---|---|
| Skyglow físic Black Marble multisatèl·lit → model DNB/SourceModel → propagació espectral → zenit/cúpules → SQM/TESS/BortleEquivalent | **No implementat com a producte.** El Pas 7.1 conserva el contracte i la política V1; el [perfil v2](skyglow/skyglow-v2-profile.json) registra VNP46, VJ146 i VJ246 com a candidats independents. El Pas 7.2 verifica el lector local VNP46. El [Pas 7.3](tasques/completat/pas7.3-dnb-rsr-measurement.md) verifica l'operador DNB TOA, el lector RSR i la interpretació L3 amb [dos VJ146 reals](evidencies/pas7.3/contrast-granuls-black-marble-c2.md). El [Pas 7.4](tasques/completat/pas7.4-spectral-bandset-validation.md) homologa **només** la discretització tabulada amb `0,01 mag` i [238/238 casos PASS](evidencies/pas7.4/homologacio-bandset-v1.md). El [Pas 7.5](tasques/completat/pas7.5-source-model-v1.md) verifica un **SourceModel S offline** amb SPD, geometria, potència definida o paramètrica i emissió angular, independent de VIIRS. 7.5.1 implementa adaptador NOAA-20 amb QA, 42 SPD CIE, fonts C relatives amb referència RSR i controls realista/K connectats al bridge. 7.6 implementa SG-REF offline en un slab homogeni pla: radiància espectral S/C, àrea/raster directa i contrast de dispersió múltiple F5 amb incerteses numèriques separades. 7.7 incorpora el kernel geomètric ECEF/ENU esfèric, GK7/15 i revisions, verificat amb B0. 7.8 implementa el provider estàndard sec COESA, OpticalField immutable P/T/n, travesses 1/2/8 tiles, dependències per capa i oracle independent de columnes. 7.9 afegeix radiància espectral de dispersió simple a 550 nm, Rayleigh/aerosol prescrits, transmissió dels dos trajectes, fases normalitzades i integració directa de rectangles. 7.10 implementa transport espectral directe S/C amb dispersió, O3 prescrit, columnes compartides i pressupost 0,01 mag revalidat; altres absorbidors i aire terrestre complet no acreditats. 7.11 afegeix terreny opac, curvatura i fonts parcialment ocultes amb SG-REF independent. No hi ha escala absoluta urbana, H ni radiància connectada al producte. | [Dossier skyglow](skyglow/README.md), [Passos 7.1](tasques/completat/pas7.1-contracte-cientific-v1.md), [7.2](tasques/completat/pas7.2-vnp46-observation-adapter.md), [7.3](tasques/completat/pas7.3-dnb-rsr-measurement.md), [7.4](tasques/completat/pas7.4-spectral-bandset-validation.md), [7.5](tasques/completat/pas7.5-source-model-v1.md) i [7.6](tasques/completat/pas7.6-sg-ref-reference-solver.md); [7.7 completat geomètricament](tasques/completat/pas7.7-kernel-geometry-b0.md), [7.8 completat per a camp/columnes](tasques/completat/pas7.8-optical-field-standard.md), [7.9 completat monocromàtic](tasques/completat/pas7.9-rayleigh-aerosol-b1.md), [7.10 completat offline](tasques/completat/pas7.10-gas-spectral-kernel.md), [7.11 completat offline](tasques/completat/pas7.11-terrain-curvature.md), [7.12–7.28 pendents](tasques/pendent/pas7.12-zenith-transport-gate.md) |
| Cel físic solar/lunar amb selector simulat/real, ROLO lunar, fons natural, SkyView LUT RGB, nubes, altura i limbe terrestre | **Pendent; especificació documental, no implementat.** El Pas 7 actual manté el shader/paleta visuals. Les decisions 2–8 estan tancades documentalment, però encara no hi ha transport Hillaire, ROLO, fons natural, error budget, scheduler o limbe físic homologats. | [Dossier cel físic](cel-fisic/README.md), [Pas 7.51](tasques/pendent/pas7.51-llicencies-i-recursos.md)–[7.68](tasques/pendent/pas7.68-homologacio-cel-fisic.md) |
| Gestor de capes Cel/Terra | Pendent d'implementació | [Pas 25](tasques/pendent/pas25-gestor-capes.md) |
| Plate solving i comparador foto/simulació | Pendent d'implementació | [Pas 30](tasques/pendent/pas30-plate-solving.md) |
| “El millor d'aquesta nit” i planificador | Pendent d'implementació | [Pas 31](tasques/pendent/pas31-millor-nit-planificador.md) |
| Miniatures i animacions d'efemèrides | Pendent d'implementació | [Pas 34](tasques/pendent/pas34-previsualitzacions-efemerides.md) |
| Nomenclàtor GeoNames empaquetat | Pendent d'implementació | [Pas 37](tasques/pendent/pas37-geonames-empaquetat.md) |
| Homologació final, recuperació i rendiment | Pendent d'implementació | [Pas 38](tasques/pendent/pas38-homologacio-final.md) |

## Regla d'actualització

El [Pas 7.4](tasques/completat/pas7.4-spectral-bandset-validation.md) deixa un oracle i `SpectralBandSet` numèric verificats [dins el domini tabulat declarat](evidencies/pas7.4/homologacio-bandset-v1.md). Encara no hi ha connexió a l'entrypoint ni skyglow físic observable; la capacitat roman en aquesta secció.

El [Pas 7.5 S](tasques/completat/pas7.5-source-model-v1.md) ofereix un model físic definit offline per a fonts puntuals i àrees rectangulars uniformes; [SPD CIE verificades i fixtures analítiques](evidencies/pas7.5/validacio-source-model-s-v1.md) proven normalització, unitats i conservació. El gate L3/RSR i el [contrast observacional real](evidencies/pas7.5/estat-inferencia-font-2026.md) continuen sense acreditar cap font urbana Black Marble de 2026. 7.5.1 afegeix el selector realista/K i control de kelvins a la UI, amb estat científic Python i transport pendent; 7.6 ja transporta S/C per CLI en un domini de referència acotat; 7.7 verifica la infraestructura geomètrica i 7.8 el camp estàndard amb dependències/columnes; 7.9 verifica dispersió monocromàtica i B1; 7.10 verifica espectre/O3 i 7.11 incorpora terreny/visibilitat offline; el punt de represa és 7.12 pendent, sense executar. La UI continua sense radiància física de producte.

Quan es completa un pas, aquest inventari s'ha d'actualitzar amb l'enllaç a la implementació observable i a les proves. No es promociona una fila perquè s'hagin creat carpetes, protocols, DTOs o renderers de només interfície.


| Capacitat nova | Estat verificat | Traçabilitat |
|---|---|---|
| Biblioteca CIE, simulació per kelvins i realista NOAA-20 → SourceModel C | Observable en configuració i executable offline en escala relativa; sense radiància del cel | [7.5.1](tasques/completat/pas7.5.1-black-marble-spectral-simulation.md) i [validació](evidencies/pas7.5.1/validacio-simulacio-condicionada.md) |
| SG-REF: radiància espectral S/C, àrea/raster i contrast F5 | Executable offline; slab homogeni pla verificat, fases fines i error numèric estimat. Sense validació empírica H ni runtime. | [7.6](tasques/completat/pas7.6-sg-ref-reference-solver.md) i [validació](evidencies/pas7.6/validacio-sg-ref.md) |
| PropagationKernel geomètric i campanya B0 | Observable per API/CLI: esfera ECEF/ENU, LOS segmentada, GK7/15, revisions/cancel·lació; integral en metres, sense radiància | [7.7](tasques/completat/pas7.7-kernel-geometry-b0.md) i [B0](evidencies/pas7.7/validacio-b0.md) |

### Transport espectral del Pas 7.10

[Observable offline](evidencies/pas7.10/validacio-espectral-i-gasos.md): schema 4, SourceModel S/C, unió de nusos/Simpson, Ångström prescrit, GasAbsorptionModel O3 203–293 K i T_eff, errors explícits fora de cobertura i signatures d'invalidació. 405 proves backend, 111.168 casos espectrals i 326.040 T_eff il·luminats. Cost de geometria/mostreig/transmissions/quadratura/espectre separat; 48 casos de sostre, sense assumir contribució nul·la per damunt de 10 ni 50 km. Cap H ni producte gràfic; l'ampliació de terreny és al pas 7.11 següent.

### Terreny i visibilitat física del Pas 7.11

[Observable offline](evidencies/pas7.11/validacio-terreny-i-visibilitat.md): DEM existent → superfície triangular amb altura explícita → ECEF/ENU compartit; truncament de LOS, màscares binàries de font puntual i àrea visible retallada geomètricament. Schema 5 opcional, sense canviar esquemes anteriors sense terreny. 427 proves, SG-REF amb algorismes independents, perfils de cost i dades reals de nou nusos. La discretització DEM i el datum vertical no queden homologats universalment; el sostre de 10 km continua ometent 22,45% en la fixture B4 zenital de 7.10. Cap gate 7.12 ni acceleració posterior executats.
