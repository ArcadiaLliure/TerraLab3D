# Especificació d'algorismes

## 1. Magnitud física canònica

La sortida autoritativa del sistema és radiància espectral o radiància integrada per banda en direcció d'observació. No es calcula directament una classe Bortle. Les conversions a luminància, resposta SQM/TESS, magnituds per segon d'arc quadrat i Bortle orientatiu són adaptadors de presentació/diagnòstic.

Per a una direcció unitària `ω` des de l'observador `O`, el punt de quadratura és `P(s)=O+sω`. El límit és `s_max=min(s_TOA,s_terrain)`. La intersecció amb terreny trunca la integral; no es representa com una transparència artificial.

## 2. Fonts candidates Black Marble i model de mesura VIIRS DNB

**NASA Black Marble Collection 2** aporta tres fonts candidates: VNP46A2/Suomi-NPP, VJ146A2/NOAA-20 i VJ246A2/NOAA-21, registrades al [perfil v2](skyglow-v2-profile.json). El [perfil v1 del Pas 7.1](skyglow-v1-profile.json) i el lector verificat de 7.2 conserven l'abast VNP46. Les unitats/QA VJ146 provenen de la seva especificació i de [dos grànuls J1 reals](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md); J2 real resta pendent. La [revisió multisatèl·lit](../evidencies/pas7.3/revisio-multisatel-lit.md) separa TOA/L3 i RSR; cap de les tres fonts no és encara homologada per a skyglow físic. Els valors PASS/FAIL es congelen als primers gates que els apliquen.

VNP46 no és skyglow a nivell de terra ni flux hemisfèric d'una font. VIIRS DNB continua definint la semàntica espectral de la mesura.

Pipeline C relatiu implementat a [7.5.1](../tasques/completat/pas7.5.1-black-marble-spectral-simulation.md); transport i homologació H pendents:

`{VNP46,VJ146,VJ246} → adaptador específic → observació tipada → model DNB/RSR TOA + correcció L3 per producte → SourceModel → EmissionRegion → RadiancePatch`.

Es mantenen separades `radiancia_observada` i `radiancia_artificial_estimada`. No s'aplica silenciosament `max(0, radiancia_observada)`. Valors negatius, nuls o febles conserven qualitat i incertesa fins que la política de baixa radiància decideixi com tractar-los.

Les correccions pròpies del producte, inclosa stray light, són **a confirmar segons producte/release**. TerraLab3D no aplica una correcció si el producte ja l'ha incorporada.

Les sèries de baixa radiància que travessen el canvi de punt zero documentat per Coesfeld et al. (2020, §2.3.1) no es consideren directament homogènies abans/després de 2017 sense una política explícita de producte. La correcció concreta d'aquell treball no es converteix en una constant universal.

### 2.1. SourceModel S definit i branca observacional C/H

El [SourceModel S implementat a 7.5](../evidencies/pas7.5/validacio-source-model-s-v1.md) defineix `s(λ)` amb integral unitària per nm, patró angular `a(θ,φ)` amb integral hemisfèrica unitària, geometria puntual o rectangle i amplitud `P` en watts definits o escala relativa paramètrica. Retorna `Pλ=P·s(λ)` i `Iλ=P·s(λ)·a(θ,φ)` amb unitats explícites, independentment de VIIRS. Per a rectangle uniforme, `Mλ=Pλ/A` i `Lλ=Mλ·a/cosθ` quan `cosθ>0`. No equival a una font urbana mesurada.

VNP46 no determina unívocament ni l'SPD ni la distribució angular hemisfèrica. La branca C de 7.5.1 conserva separats prior/ensemble espectral, normalització condicionada, model angular, correcció L3 i incertesa; no hereta watts d'una fixture S.

El `PropagationKernel` no rep directament una radiància DNB com si fos intensitat. Rebrà intensitat radiant direccional `I↑(direccio_font_punt)` produïda pel `SourceModel`, amb unitats de potència per estereoradiant. No es fixa una llei lambertiana per defecte; F1 observacional continua oberta.

## 3. Segmentació radiomètrica

La segmentació futura de C/H s'aplicarà a un camp d'emissió artificial interpretat, no a valors Black Marble crus forçats a ser positius. Una font S definida no necessita segmentació satel·lital.

~~~text
VNP46 observation
  → quality/nodata/product semantics
  → SourceModel
  → artificial-radiance estimate + uncertainty
  → valid-for-segmentation mask
  → log-radiance només sobre valors físicament admissibles
  → denoise radiomètricament conservador
  → background threshold
  → local maxima + prominence
  → watershed + merge
  → EmissionRegion[]
  → quadtree adaptatiu intern
  → RadiancePatch[]
~~~

El watershed respon quines fonts diferenciades existeixen. El quadtree només controla la resolució interna. Cap node pot creuar una frontera d'`EmissionRegion`.

L'aproximació puntual d'un patch és una acceleració. La seva validació ha de comparar-la contra integració/submostreig d'àrea independent; no és suficient comparar pare i fills que reutilitzen la mateixa fórmula puntual. No es fixa ara un quocient universal distància/mida: el criteri és el pressupost d'error geomètric.

## 4. Geometria angular

Per font compacta: `W≈2 atan(R/d)`. Per font extensa, es projecten els patches/polígon a coordenades topocèntriques i es calcula l'arc azimutal visible. `W_physical` cobreix la regió visible; `W_effective` és l'arc mínim que conté una fracció candidata del 95% de radiància projectada. Cal tractar circularitat azimutal, escorç i regions que travessen 0°/360°.

## 5. Base espectral i operador DNB

Cada base `Φ_f(λ)` compleix integral unitària sobre el rang declarat. Una font normalitzada és `S_j(λ)=Σ_f c_j,f Φ_f(λ)`, amb pesos que sumen 1.

La RSR operativa H conserva sensor, guany, release i dates. Per C, 7.5.1 resol la millor referència pública del mateix sensor/mode, sense allargar-ne validesa. No se selecciona la més nova d’una altra plataforma.

Per la vertical actual:

`measurementOperatorId = BAND_INTEGRATED`.

La normalització conserva la fórmula:

`A_j = L_DNB,j / ∫ S_j(λ) R_DNB(λ)dλ`.

Aquí `L_DNB,j` ha de ser una restricció de banda **físicament compatible amb la RSR seleccionada**. El valor cru de `DNB_BRDF-Corrected_NTL` de VNP46A2 és L3 corregit i no es pot inserir automàticament en aquesta equació com si fos una radiància TOA del sensor. La [User Guide C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta la transformació TOA→L3 i tanca la seva interpretació al Pas 7.3; cap escala absoluta operativa es deriva sense acreditar H; l’ancoratge relatiu de 7.5.1 es defineix amb hipòtesis explícites.

No es divideix `R_DNB` per `∫R_DNB dλ` per defecte. Si un producte defineix radiància espectral mitjana o un operador diferent, ha d'usar un `measurementOperatorId` propi.

**Unitat de `L_DNB,j` verificada a TOA:** l'[ATBD VIIRS SDR](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf) identifica DNB com a radiància integrada `W·cm⁻²·sr⁻¹` i RSR energètica amb `λ` ja incorporat. El model de 7.3 integra radiància espectral al sensor en `nW·cm⁻²·sr⁻¹·nm⁻¹`; la sortida és `nW·cm⁻²·sr⁻¹`. Black Marble L3 comparteix unitat però no necessàriament operador directe. La [RSR SNPP anual](../evidencies/pas7.3/recerca-rsr-2026.md) i la [correspondència J1/J2 L3](../evidencies/pas7.3/revisio-multisatel-lit.md) resten pendents.

`L_j,k,f = A_j c_j,f ∫_{Δλ_k} Φ_f(λ)dλ`.

VNP46 continua essent una observació panchromàtica: no justifica col·lapsar el transport atmosfèric a un únic flux. `spectralBandCount` i `bandSetId` continuen definint la propagació.

El [gate observacional històric](../evidencies/pas7.5/estat-inferencia-font-2026.md) només comprova si la base QA/RSR/guany/L3 d'una observació és admissible. Encara no hi ha una RSR operativa de 2026 ni un operador que converteixi la radiància L3 corregida en normalització, priors SPD i emissió angular de ciutat. Els perfils angulars definits S no es dedueixen de L3. La normalització relativa de 7.5.1 s’executa sobre un grànul real amb SPD/angularitat definides; les expressions absolutes d’aquesta secció no acrediten H.

## 6. Extinció i transmissió

`τ_k(A,B)=∫_A^B β_ext,k(s) ds` i `T_k(A,B)=exp(-τ_k(A,B))`.

Es mantenen separats `β_ext`, `β_sca`, `β_abs`; per aerosols i núvols `β_sca=ω0 β_ext`. Rayleigh contribueix principalment a dispersió; gasos contribueixen a absorció; aerosols i núvols poden fer ambdues coses.

Per absorció gasosa ampla no s'accepta `exp(-mean(τ))`. Com que `exp(-x)` és convexa, `E[exp(-τ)] ≥ exp(-E[τ])`. La LUT ha de preservar transmitància integrada:

`T_eff,k,f = ∫ Φ_f(λ) exp(-τ_gas(λ)) dλ / ∫ Φ_f(λ)dλ`.

## 7. Funcions de fase

Convenció única: `∫_{4π}P(θ)dΩ=1`, unitats `sr⁻¹`.

Rayleigh no polaritzada amb despolarització `δ`:

`P_R(θ)=3/[16π(1+2δ)] · [(1+3δ)+(1-δ)cos²θ]`.

Per aerosols/núvols, interfície canònica Legendre:

`P(μ)=1/(4π) Σ_{l=0}^L (2l+1)a_l P_l(μ)`, amb `a_0=1`; en aquesta convenció `a_1` és l'asimetria `g`.

Recurrència: `P_0=1`, `P_1=μ`, `P_{l+1}=((2l+1)μP_l-lP_{l-1})/(l+1)`.

Fallback HG:

`P_HG=(1-g²)/(4π(1+g²-2g cosθ)^(3/2))`.

## 8. Kernel single-scattering v1

Per patch `j`, banda `k`, base `f` i node `P`:

`E_j,k,f(P)=I↑_j,k,f(direction_jP)/r_jP² · T_jP,k,f · V_jP`.

`I↑` és **intensitat radiant direccional produïda pel `SourceModel`**, no radiància VNP46. Així `I↑/r²` és irradiància incident al node.

`Γ_k,f(P,θ)=β_R,k P_R(θ)+β_sca,aer,k P_aer(θ)+β_sca,cloud,k P_cloud(θ)`.

`dB_j,k,f=E_j,k,f(P) Γ_k,f(P,θ) T_PO,k,f ds`.

`B_j,k,f(O,ω)=∫_0^smax dB_j,k,f`.

No hi ha un segon `1/r_PO²`: després de la dispersió es transporta radiància. La v1 candidata continua sent single-scattering; el biaix respecte de multiple scattering es valida segons F5 i no s'assumeix nul.

## 8.1. Gate zenital radiomètric absolut

El zenit és la mateixa avaluació del `PropagationKernel` a elevació 90°. No hi ha un solver zenital separat.

El gate valida la **propagació numèrica donat un model de font**. Runtime i oracle han de consumir la mateixa hipòtesi de `SourceModel`; per tant, un PASS no valida empíricament la inferència VNP46→SPD ni VNP46→emissió angular.

La validació del model d'emissió necessita dades externes independents. L'oracle concret del gate continua sent la decisió S1; la quantificació de single vs multiple scattering segueix F5.

La mostra de 90° d'un `DomeProfile` és un test de regressió/cablejat contra el zenit homologat, no un oracle físic independent.

## 9. Integració numèrica

Cada direcció és una integral LOS. Les 100 fonts × 9 elevacions són aproximadament 900 integrals, no 900 operacions. El LOS es parteix als límits d'`OpticalTile`, capes i discontinuïtats. Per cada segment s'aplica Gauss–Kronrod 7/15 adaptatiu; l'estimador inicial és `|Q15-Q7|`, amb subdivisió fins al pressupost local.

El tall anticipat només és admissible si existeix una cota conservadora `B_remaining_max < ε_B`. No s'atura perquè `T<ε` sense cota de la font i de la dispersió restant.

El radi màxim de fonts és la decisió F7: no es fixa per intuïció mentre no hi hagi una cota d'error o un perfil de producte justificat.

## 10. Cúpules direccionals

Mostres inicials d'elevació: `[0.5,2,5,10,20,30,45,60,90]°`. El zenit és la mostra de 90° del mateix kernel. El perfil vertical es reconstrueix amb PCHIP sobre `log(B+ε_log)`. PCHIP s'usa per preservar forma/monotonia local i evitar overshoot de splines cúbiques genèriques. `ε_log` és només estabilitzador numèric i ha de quedar molt per sota del sòl radiomètric rellevant.

Fonts diferents se sumen abans de qualsevol logaritme o transformació perceptual: `B_total(ω)=Σ_j B_j(ω)`.

La [represa adaptativa v2 de 7.13](../evidencies/pas7.13/adaptatiu-v2/validacio-adaptativa-v2.md) conserva aquestes elevacions com a inicialització, amb vuit azimuts inicials. Refina independentment els perfils verticals i els intervals azimutals mitjançant probes a 1/4, 1/2 i 3/4; promou punts/perfils mitjans i torna a comprovar les pendents veïnes. La reconstrucció azimutal v2 és PCHIP log periòdic sobre quatre perfils, amb nusos verticals irregulars. El marge intern preregistrat és 0,002 mag; el gate independent continua a 0,01 mag. La convergència interna no concedeix PASS a una petició arbitrària.

Els zeros i les barreres verticals separen els trams PCHIP; no es crea una radiància mínima física amb ε. El constructor adaptatiu rebutja DEM i àrees fins a acreditar-ne el domini angular: es manté transport directe. Per a topologia azimutal amb barreres no acreditades, el camp d’ús és `directOnly=true`; només lliura nodes exactes. No hi ha interpolació garantida a través de discontinuïtats ni fora de la cobertura. El sostre prové de la petició; COESA conserva 75 km i la cota exterior condicionada no nul·la de 7.12.

## 10.1. Projeccions fotomètriques i instrumentals

El kernel retorna radiància física. Les magnituds perceptuals o instrumentals són adaptadors posteriors i no retroalimenten la física.

Per luminància fotòpica s'utilitza `V(λ)` i la constant CIE declarada/versionada.

Per SQM, TESS-W o un sensor futur s'aplica la **resposta espectral real** de l'instrument, el seu FOV i calibratge; no es substitueix per una `V(λ)` genèrica. La projecció SQM propaga a `predictionUncertainty` la incertesa del prior/ensemble espectral, perquè la relació radiància→magnitud depèn de l'espectre assumit i de les condicions.

Una eventual magnitud de percepció nocturna humana és F6 i queda separada de SQM/TESS.

`BortleEquivalent` és una política de presentació versionada, no una sortida del kernel ni ground truth físic.

## 10.2. Composició física del cel

Els canals es mantenen separats fins a la composició lineal: `B_total = B_artificial + B_natural_moonless + B_moon + B_twilight`.

Es distingeix **reference sky** (nit de referència sense Lluna ni crepuscle, candidat per a `BortleEquivalent`) d'**instantaneous sky** (estat real a data/hora). La Lluna pot canviar el cel instantani, però no reclassifica per si sola la contaminació lumínica intrínseca del lloc.

## 10.3. Precomputació, LUT i FFT

La precomputació offline és una **estratègia d'acceleració del mateix operador físic**, no una física alternativa. LUT, kernels tabulats o FFT només són admissibles quan conserven les mateixes entrades/sortides, tenen domini de validesa explícit i es comparen contra la ruta directa/reference solver dins un pressupost d'error.

Una convolució FFT exigeix demostrar la invariància translacional necessària. Atmosfera espacialment variable, models de font locals, curvatura o terreny poden trencar aquesta hipòtesi. Fora del domini homologat s'utilitza una ruta més general. El transport continua sent espectral encara que es precalculi.

## 11. Cache i derivades

Ordre d'invalidació: (1) canvi visible↔ocult; (2) canvi de topologia/quadtree/domini; (3) guardes geomètriques barates; (4) estimació contínua `ΔB_geometry+ΔB_atmosphere`; (5) pressupost d'error.

Dins una branca diferenciable, `B(q)=∫_0^{smax(q)}F(q,s)ds` i `∇B=∫∇F ds + F(q,smax)∇smax`. El candidat és forward-mode AD amb `(B,dB/dx,dB/dy,dB/dz)` en la mateixa quadratura. Oclusió, canvis discrets de quadtree i travesses topològiques invaliden; no es diferencien.

**Invariant de runtime:** el kernel no s'executa per frame. Els canvis ràpids d'observador es coalescen i les revisions obsoletes no es publiquen. La precàrrega predictiva és candidata de rendiment, no física: només s'activa si B7 demostra guany sense false hits ni augment de l'error.

S'han de precomputar les parts estàtiques o quasiestàtiques quan sigui possible (integrals RSR/basis, LUT gasosa, segmentació/quadtree, índexs de terreny i metadades de tiles). No es precomputa globalment un cel dependent de l'observador sense model d'error i invalidació.

## 12. Complexitat

Cost aproximat: `O(N_source_effective × N_direction × N_segment × N_node × N_band × N_basis × C_phase)`. Els costos estructurals es mesuren a B0–B7 amb la configuració espectral activa; **no** es fan sweeps ni benchmarks per determinar el nombre de bandes. La geometria LOS i la visita de tiles s'han de compartir entre bandes/bases sempre que sigui possible.

## 13. Fallback

Sense dades atmosfèriques reals: atmosfera estàndard versionada. Sense aerosol detallat: HG amb paràmetres explícits i confiança baixa. Sense prior SPD local: ensemble global documentat. Sense núvols fiables: cel clar declarat; mai inventar cobertura. Sense VIIRS: mantenir modes manuals existents com a fallback de producte, però no etiquetar-los com a simulació física.
## Configuració espectral de la vertical 7.1–7.50

El nombre de bandes del kernel és un paràmetre de configuració (`spectralBandCount`) amb límits/ponderacions i `bandSetId` versionats. L'[operador offline verificat a 7.4](../evidencies/pas7.4/homologacio-bandset-v1.md) forma els intervals amb la unió dels nusos de la SPD i de les respostes tabulades i integra amb Simpson; la cardinalitat varia amb les corbes. La identitat de bandes i la signatura completa de les corbes han d'acompanyar qualsevol resultat reutilitzable. Aquest resultat numèric no autoritza encara cap partició fixa del kernel de transport: 7.10 i 7.14 revaliden el criteri en ampliar els operadors. No existeix un N fix ni un benchmark per triar-lo; es comproven unitats, integració i coherència de la configuració activa. El cel solar/lunar i el limbe terrestre són responsabilitat de la [vertical 7.51+](../cel-fisic/README.md), que comparteix òptica però no el `PropagationKernel` artificial.
