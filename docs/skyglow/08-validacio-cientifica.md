# Pla de validació científica

## 1. Validació numèrica

Objectiu: demostrar que discretització i integració convergeixen abans de comparar amb el món real. Casos: atmosfera homogènia amb solució/alta precisió de referència, integrands suaus, discontinuïtats a límits de tile, oclusió, trajectes rasants i fonts puntuals/extenses.

Proves: convergència GK; comparació amb quadratura d'ordre alt; invariància sota partició equivalent de tiles; linealitat en intensitat; suma de patches igual a font no agregada dins tolerància; positivitat de radiància; absència de NaN/Inf a 0,5°.

## 1.1. Gate zenital absolut

Abans de validar cúpules, la direcció 90° ha de superar un gate amb la mateixa implementació del kernel: unitats, convergència, extinció/oclusió i comparació amb un oracle independent.

El gate valida **propagació donat un model de font**. Runtime i oracle consumeixen la mateixa hipòtesi de `SourceModel`; un PASS no valida la inferència VNP46→SPD ni VNP46→emissió angular. Aquesta validació necessita dades externes separades.

L'oracle concret és la decisió S1. La quantificació del biaix single-scattering exigeix un oracle amb multiple scattering segons F5.

## 2. Validació espectral

Cada `SpectralBandSet` actiu es compara contra un espectre de referència prou fi per demostrar convergència de radiància propagada i de les projeccions actives (fotòpica, SQM, TESS-W, XYZ quan apliqui).

No es fan sweeps de rendiment per escollir N. `V3` ha tancat a 7.4 **només** el domini de corbes tabulades amb el [pressupost de producte de 0,01 mag preregistrat](../evidencies/pas7.4/criteri-preregistrat-v1.json) i [238 integrals verificades](../evidencies/pas7.4/homologacio-bandset-v1.md). El pressupost es reaplica a 7.10 amb absorció/dispersió i a 7.14 amb projeccions fotomètriques, versionant bandes si falla.

La normalització DNB usa `BAND_INTEGRATED` al **sensor TOA**; la [unitat integrada DNB](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf#page=38) està verificada. La [User Guide C2 §2.2 Eq. (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) documenta la correcció TOA→radiància L3 de superfície i els [grànuls VJ146](../evidencies/pas7.3/contrast-granuls-black-marble-c2.md) en confirmen capa/QA/unitats; el valor L3 no s'equipara a la integral TOA. La [RSR anual SNPP](../evidencies/pas7.3/recerca-rsr-2026.md) continua pendent i les [corbes J1/J2 de prelanzament](../evidencies/pas7.3/revisio-multisatel-lit.md) permeten referències C condicionades a 7.5.1, sense certificació H. El [Pas 7.5](../evidencies/pas7.5/validacio-source-model-s-v1.md) només acredita fonts definides S; 7.5.1 implementa C relatiu amb tests científics independents; 7.16–7.24 han de propagar incertesa i acreditar H per plataforma. Les superposicions entre sensors es comparen, no se sumen; no s'aplica SBAF per defecte.

## 3. Validació atmosfèrica

Separar components. Rayleigh: contrast contra formulació Bodhaine/King. Gasos: LUT contra càlcul espectral fi HITRAN/LOWTRAN-like. Aerosols: HG/Legendre contra taules Mie/mesurades. Humitat: casos secs/humits si la biblioteca aerosol la modela. Núvols: només single-scattering v1 contra casos òpticament prims/moderats.

## 4. Validació all-sky

Construir `B_full(az,el)` amb solver de referència i `B_compressed` amb mostres de cúpula. Comparar abans de tone mapping.

`Δm=|-2.5 log10(B_compressed/B_full)|`.

Mètriques mínimes: MAE hemisferi ponderat per angle sòlid, MAE 0–20°, P95 `|Δm|`, relació d'energia `∫B_compressed dΩ/∫B_full dΩ`, `Δaz_peak`, `ΔB_peak`, `ΔW`. Escombrar si cal la mostra a 1° i el percentatge de `W_effective`.

## 5. Ground truth

La comparació amb el reference solver valida implementació i aproximacions numèriques; no substitueix la validació física externa.

Fonts prioritàries: TESS-W i SQM amb resposta espectral coneguda i all-sky fotomètric calibrat quan estigui disponible. La simulació del sensor usa resposta espectral, FOV i calibratge i propaga la incertesa del prior espectral.

La validació **empírica C/H** del `SourceModel` és separada: calen dades independents capaces de restringir l'emissió angular/espectral. Una observació VNP46 quasi-nadir no valida per si sola la distribució hemisfèrica. La conservació numèrica de S no substitueix aquesta prova.

Si no hi ha dataset extern suficient, l'estat màxim és numèricament validat però no empíricament homologat; la manca de dades no es converteix en PASS.

### Baixa radiància

Les fixtures inclouen valors febles, prop de zero i negatius quan el producte ho permeti, sense clipping silenciós. També cobreixen sèries que travessen 2017. LOW-RAD determina si aquestes mostres s'exclouen o es propaguen amb incertesa.

## 6. Disseny estadístic

Separar calibratge i validació. Si s'ajusten priors o paràmetres d'emissió amb llocs mesurats, fer leave-one-site-out i una validació geogràfica externa. No utilitzar el mateix conjunt per ajustar emissió i reportar precisió final. El nombre de bandes no es selecciona amb una campanya comparativa.

Reportar errors amb intervals/quantils i estratificar per distància a fonts, brillantor, aerosol, relleu, elevació i tipus d'il·luminació.

## 7. Bortle

Bortle és una escala observacional qualitativa. Només es pot mostrar com `BortleEquivalent` orientatiu derivat de condicions de referència, mai com ground truth físic primari. La política té `bortlePolicyId` i està separada de SQM. El `BortleEquivalent` intrínsec del lloc s'avalua sense Lluna ni crepuscle; aquests components només alteren el diagnòstic instantani. Les conversions actuals del Pas 7 es mantenen com a legacy fins que una política nova sigui validada.

## 8. Criteris d'acceptació

Cada gate de producció necessita un perfil d'acceptació congelat **abans** de la comparació que decidirà PASS/FAIL. Cada llindar indica origen: referència publicada, requisit de producte o error/convergència numèrica.

Un llindar modificat després de veure els resultats només pot crear una nova versió prospectiva i no reescriu l'avaluació anterior ni revalida el mateix candidat/conjunt observat. El [perfil v1](skyglow-v1-profile.json) registra les decisions de dades i la política `V1` preregistrada al Pas 7.1, completat documentalment. **7.4 ja ha preregistrat i verificat** l'error espectral de `0,01 mag` en el domini tabulat declarat. 7.12 preregistra runtime↔SG-REF abans del PASS/FAIL, amb l'evidència de convergència/incertesa de 7.6; 7.17 preregistra criteris empírics amb incerteses instrumental, de dades i del model abans d'avaluar el conjunt `held-out`; 7.22 preregistra SLO de producte aprovats abans de decidir acceleracions. La manca d'un valor bloqueja aquell primer gate, no els passos precedents. 7.28 només consumeix els criteris ja congelats.

L'error estructural single-scattering es registra separat de l'error numèric. F5 no es pot tancar amb un oracle exclusivament single-scattering.

## 9. Evidència

Cada campanya genera manifest de datasets/checksums, configuració, commit, hardware, resultats raw CSV/JSON, plots i informe. Els resultats històrics no s'esborren; es marquen vigents/obsolets amb causa.

## Referència disponible després de 7.6

[SG-REF verificat](../evidencies/pas7.6/validacio-sg-ref.md) cobreix slab homogeni espectral, fonts puntuals no singulars i rectangles/raster en pla local. Contrasta E1 i GL compost, subdivisió i fases fines; F5 usa un segon transport Monte Carlo d'ordre superior sense compartir la quadratura. Les toleràncies de control de l’oracle i la regla diagnòstica de 6 errors estàndard són [prospectives](../evidencies/pas7.6/criteri-oracle-v1.json), no criteris de producte ni intervals garantits.

Els benchmarks F5 mesuren biaix dins els seus escenaris definits; no fixen una correcció urbana i no quantifiquen la incertesa SPD/angular/atmosfèrica de C/H. 7.8 amplia/revalida la referència només per columnes P/T/n en tiles i altura esfèrica, amb GK21/partició/interpolació independents del runtime. [Evidència](../evidencies/pas7.8/validacio-optical-field.md). 7.9 amplia/revalida radiància monocromàtica amb geometria esfèrica i transmissió variable, mitjançant GK21/GL i implementació independent de fases/mostreig/travessa. [Evidència B1](../evidencies/pas7.9/validacio-b1.md). 7.10 ja amplia la referència a espectre/O3 prescrit i columnes variables a 550 nm; 7.11 ja revalida la visibilitat triangular amb sistemes lineals NumPy i àrea per franges independents, amb refinament geomètric/àrea explícit i contrast radiomètric diagnòstic. 7.12 només pot usar evidència de convergència corresponent al mateix domini físic que valida.

## Estat verificat de 7.10 (2026-10-19)

7.10 revalida 111.168 integrals espectrals i 326.040 T_eff il·luminats amb 0,01 mag, separant error LUT, Simpson, oracle i dades físiques. SG-REF espectral homogeni i columnes variables a 550 nm amb partició T independent; el residual estret/monocromàtic inclou amplada de banda. Sensibilitat de 10/20/30/50 km mesurada, cua superior desconeguda. No és PASS/FAIL de transport (7.12), ni H, ni validació d'aire terrestre complet. [Evidències i límits](../evidencies/pas7.10/validacio-espectral-i-gasos.md).

## Estat verificat de 7.11 (2026-10-19)

Topologia sintètica, DEM configurat i fonts S/C realista/K verificats offline; 427 proves. Cap tolerància runtime↔SG-REF triada a partir dels residuals: en aquell tancament7.12 continuava pendent. [Informe i incerteses](../evidencies/pas7.11/validacio-terreny-i-visibilitat.md). Els errors de malla, àrea, espectre i sostre es documenten separadament; no s’ha declarat suficient el domini atmosfèric de 10 km.

## Estat verificat de7.12 (2026-10-19)

[Gate prospectiu](../evidencies/pas7.12/validacio-gate-transport.md):10⁻⁴ relatiu protegit amb u_ref/R≤10⁻⁶,9 fixtures S PASS,42 sostres i444 proves. Cota exterior >75km positiva i condicionada ≤0,000472296mag, sense exigir P(infinit)=0;0,01mag espectral mantingut. Els controls independents separen àrea/trajectes/espectre; DEM/P/T i física no s'absorbeixen dins el residual. El perfil v2 referencia el nou registre; el v1 històric no es reescriu. C realista/K continua relatiu, sense homologació observacional.7.13 no iniciat.
