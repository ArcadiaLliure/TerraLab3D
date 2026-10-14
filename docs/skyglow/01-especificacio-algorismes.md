# Especificació d'algorismes

## 1. Magnitud física canònica

La sortida autoritativa del sistema és radiància espectral o radiància integrada per banda en direcció d'observació. No es calcula directament una classe Bortle. Les conversions a luminància, resposta SQM/TESS, magnituds per segon d'arc quadrat i Bortle orientatiu són adaptadors de presentació/diagnòstic.

Per a una direcció unitària `ω` des de l'observador `O`, el punt de quadratura és `P(s)=O+sω`. El límit és `s_max=min(s_TOA,s_terrain)`. La intersecció amb terreny trunca la integral; no es representa com una transparència artificial.

## 2. Font radiomètrica VIIRS

Un producte VIIRS/VNL no és skyglow des de terra. És una observació de radiància ascendent en la geometria i processament del producte. El pipeline obligatori és:

`VIIRS product → ViirsSourceObservation → SourceModel → EmissionRegion → RadiancePatch`.

VNL V2 publica radiància mitjana/mediana en `nW cm⁻² sr⁻¹` a 15 arcsec; Black Marble diferencia VNP46A1 (radiància TOA a sensor) i VNP46A2/A3/A4 amb correccions atmosfèriques/lunars/BRDF. El producte escollit s'ha de registrar perquè la transformació inversa cap a emissió de font depèn del processament.

## 3. Segmentació radiomètrica

Pipeline inicial:

~~~text
radiance raster
  → valid mask / quality mask
  → log-radiance
  → denoise lleu, radiomètricament conservador
  → background threshold
  → local maxima + prominence
  → watershed
  → merge de conques insignificants
  → EmissionRegion[]
  → quadtree adaptatiu intern
  → RadiancePatch[]
~~~

El watershed respon quines fonts diferenciades existeixen. El quadtree només controla la resolució interna. Cap node del quadtree pot creuar una frontera d'`EmissionRegion`.

El refinament d'un patch compara la substitució del conjunt de fills pel pare. S'ha de refinar si l'error estimat en `I_up/r² × T × V` supera `ε_patch`. `V` és binari per raig. Una visibilitat parcial de regió només emergeix de la suma de patches visibles i ocults.

## 4. Geometria angular

Per font compacta: `W≈2 atan(R/d)`. Per font extensa, es projecten els patches/polígon a coordenades topocèntriques i es calcula l'arc azimutal visible. `W_physical` cobreix la regió visible; `W_effective` és l'arc mínim que conté una fracció candidata del 95% de radiància projectada. Cal tractar circularitat azimutal, escorç i regions que travessen 0°/360°.

## 5. Base espectral i normalització DNB

Cada base `Φ_f(λ)` compleix `∫[400,900] Φ_f(λ)dλ=1`, amb unitats `nm⁻¹`. Una font normalitzada és `S_j(λ)=Σ_f c_j,f Φ_f(λ)`, `Σ_f c_j,f=1`.

Amb la RSR real `R_DNB(λ)`:

`A_j = L_DNB,j / ∫ S_j(λ) R_DNB(λ)dλ`

`L_j,k,f = A_j c_j,f ∫_{Δλ_k} Φ_f(λ)dλ`.

`A_j` és escala; `c_j,f` és composició; `L_j,k,f` és entrada radiomètrica de banda/base. No es poden multiplicar dues vegades.

El DNB no identifica unívocament l'SPD. La zona blava queda sobretot governada pel prior, però l'escala global també pot quedar esbiaixada si el prior és erroni dins la zona sensible del DNB. Per això el resultat porta `priorId`, `priorConfidence`, ensemble i separació `DIRECT_DNB`/`INDIRECT_PRIOR`.

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

`Γ_k,f(P,θ)=β_R,k P_R(θ)+β_sca,aer,k P_aer(θ)+β_sca,cloud,k P_cloud(θ)`.

`dB_j,k,f=E_j,k,f(P) Γ_k,f(P,θ) T_PO,k,f ds`.

`B_j,k,f(O,ω)=∫_0^smax dB_j,k,f`.

No hi ha un segon `1/r_PO²`: la radiància que viatja de P a O conserva la seva geometria i només pateix extinció. La v1 és single-scattering per decisió de TerraLab3D; Cinzano–Falchi 2012 és explícitament més general i tracta dispersió múltiple.

## 8.1. Gate zenital radiomètric absolut

El primer resultat científic que es promou fora de fixtures és la direcció `ω_zenith` (elevació 90°) avaluada pel **mateix** `PropagationKernel`. No és un solver separat ni una aproximació especial.

El gate exigeix cadena d'unitats completa, cap `calibrationFactor` opac, convergència contra el reference solver, comprovacions de linealitat/positivitat/transmissió i benchmark cold/warm. El resultat de 90° queda com a invariant: qualsevol `DomeProfile` posterior ha de reproduir-lo dins el pressupost d'error declarat.

## 9. Integració numèrica

Cada direcció és una integral LOS. Les 100 fonts × 9 elevacions són aproximadament 900 integrals, no 900 operacions. El LOS es parteix als límits d'`OpticalTile`, capes i discontinuïtats. Per cada segment s'aplica Gauss–Kronrod 7/15 adaptatiu; l'estimador inicial és `|Q15-Q7|`, amb subdivisió fins al pressupost local.

El tall anticipat només és admissible si existeix una cota conservadora `B_remaining_max < ε_B`. No s'atura perquè `T<ε` sense cota de la font i de la dispersió restant.

## 10. Cúpules direccionals

Mostres inicials d'elevació: `[0.5,2,5,10,20,30,45,60,90]°`. El zenit és la mostra de 90° del mateix kernel. El perfil vertical es reconstrueix amb PCHIP sobre `log(B+ε_log)`. PCHIP s'usa per preservar forma/monotonia local i evitar overshoot de splines cúbiques genèriques. `ε_log` és només estabilitzador numèric i ha de quedar molt per sota del sòl radiomètric rellevant.

Fonts diferents se sumen abans de qualsevol logaritme o transformació perceptual: `B_total(ω)=Σ_j B_j(ω)`.

## 10.1. Projeccions fotomètriques i instrumentals

El kernel retorna radiància física. Les magnituds perceptuals o instrumentals són adaptadors posteriors i **no poden retroalimentar la física**.

Per luminància fotòpica, quan hi ha radiància espectral suficient: `L_v = K_cd ∫ V(λ) L_e,λ dλ`, amb `K_cd = 683 lm W⁻¹` i la funció d'eficiència lluminosa CIE declarada/versionada.

Per SQM, TESS-W o un sensor futur s'aplica la seva resposta espectral i el seu FOV/calibratge: `S_sensor = ∫∫ R_sensor(λ,ω) L_e,λ(ω) dλ dΩ`. El zero point i la transformació final a `mag/arcsec²` formen part del model/calibratge de l'instrument. No hi ha una constant universal per convertir DNB o radiància genèrica a «SQM».

`BortleEquivalent` és una política de presentació versionada, no una sortida del kernel ni ground truth físic.

## 10.2. Composició física del cel

Els canals es mantenen separats fins a la composició lineal: `B_total = B_artificial + B_natural_moonless + B_moon + B_twilight`.

Es distingeix **reference sky** (nit de referència sense Lluna ni crepuscle, candidat per a `BortleEquivalent`) d'**instantaneous sky** (estat real a data/hora). La Lluna pot canviar el cel instantani, però no reclassifica per si sola la contaminació lumínica intrínseca del lloc.

## 11. Cache i derivades

Ordre d'invalidació: (1) canvi visible↔ocult; (2) canvi de topologia/quadtree/domini; (3) guardes geomètriques barates; (4) estimació contínua `ΔB_geometry+ΔB_atmosphere`; (5) pressupost d'error.

Dins una branca diferenciable, `B(q)=∫_0^{smax(q)}F(q,s)ds` i `∇B=∫∇F ds + F(q,smax)∇smax`. El candidat és forward-mode AD amb `(B,dB/dx,dB/dy,dB/dz)` en la mateixa quadratura. Oclusió, canvis discrets de quadtree i travesses topològiques invaliden; no es diferencien.

**Invariant de runtime:** el kernel no s'executa per frame. Els canvis ràpids d'observador es coalescen i les revisions obsoletes no es publiquen. La precàrrega predictiva és candidata de rendiment, no física: només s'activa si B7 demostra guany sense false hits ni augment de l'error.

S'han de precomputar les parts estàtiques o quasiestàtiques quan sigui possible (integrals RSR/basis, LUT gasosa, segmentació/quadtree, índexs de terreny i metadades de tiles). No es precomputa globalment un cel dependent de l'observador sense model d'error i invalidació.

## 12. Complexitat

Cost aproximat: `O(N_source_effective × N_direction × N_segment × N_node × N_band × N_basis × C_phase)`. Tots els multiplicadors s'han de mesurar separadament a B0–B7. La geometria LOS i la visita de tiles s'han de compartir entre bandes/bases sempre que sigui possible.

## 13. Fallback

Sense dades atmosfèriques reals: atmosfera estàndard versionada. Sense aerosol detallat: HG amb paràmetres explícits i confiança baixa. Sense prior SPD local: ensemble global documentat. Sense núvols fiables: cel clar declarat; mai inventar cobertura. Sense VIIRS: mantenir modes manuals existents com a fallback de producte, però no etiquetar-los com a simulació física.