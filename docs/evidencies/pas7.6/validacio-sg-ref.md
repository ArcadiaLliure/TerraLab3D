# Validació SG-REF — Pas 7.6

Executat el 2026-10-18 a Windows, Python 3.13.7, NumPy 2.3.3 i SciPy 1.16.2. Codi base de la tasca: `455ecd3`; canvis de 7.6 al working tree, sense commit automàtic. [Pas completat](../../tasques/completat/pas7.6-sg-ref-reference-solver.md), [dades completes](resultats-sg-ref-v1.json) i [criteri congelat](criteri-oracle-v1.json).

## Què s’ha verificat

SG-REF calcula radiància espectral d’una o diverses fonts físiques S/C donades, per direcció. La integral LOS adaptativa GK21 de SciPy és independent del futur GK7/15 del runtime. Cada rectangle s’integra amb Gauss–Legendre tensorial sobre tota l’àrea; un raster és una suma explícita de rectangles amb potències pròpies. Cap quadtree, aproximació al centre, LUT ni cache de propagació. La normalització SPD/angular de SourceModel es comparteix com a definició d’entrada, no com a aproximació de transport.

El domini verificat és **pla tangent local cartesià, slab espectral homogeni, terra negre, cel clar escalar**, elevacions 0,5–90° i fonts puntuals no singulars o rectangles uniformes. Les altures són coordenades del slab definit. No inclou geodèsia ECEF global, DEM, curvatura, capes verticals/tiled, Mie, polarització, reflexió de terra ni núvols. La direcció 90° usa la mateixa integral que les altres. La quadratura segmenta explícitament els límits del suport emissor i les regions de màxima proximitat de fonts puntuals; una prova independent cobreix una capa emissora de només 1 mm prop del sostre, que es podria perdre amb mostreig adaptatiu sense segmentació.

La referència més rica F5 és un segon solver propi de Monte Carlo invers. Comparteix els contractes de font i la definició física del slab, però no geometria nodal, LOS, quadratura ni canvi de variable. No es presenta com a LPTRAN ni com una reproducció completa de Cinzano–Falchi.

## Controls prospectius i significat de l’error

Abans de la primera avaluació es van congelar `epsrel_LOS=10⁻⁸`, `epsabs=10⁻²⁰` en la unitat de radiància, tolerància espacial relativa `10⁻⁶`, ordres d’àrea 8/16/32/64/128 i dues refinacions consecutives. L’elecció són controls estrictes de construcció de l’oracle; la convergència i els contrasts independents següents en demostren la precisió en aquests casos. **No són un llindar de producte**. SHA-256 del criteri: `444e19b2458c5714858a59b4753750bcf359724fce3a974d9fc66a77ffa636a9`.

`numerical_error_estimate` suma l’estimació GK en norma màxima i la diferència de l’últim refinament espacial, amb errors LOS d’ambdós refinaments. La norma màxima es reporta conservadorament a cada canal. És una estimació numèrica, **no aritmètica d’intervals ni una garantia**: cancel·lació, singularitat o manca de convergència produeixen una excepció. La discretització de fase tabulada es contrasta separadament i no s’amaga dins l’error LOS. La incertesa física/urbana continua `not_quantified`.

## Contrasts analítics i convergència espacial

Font puntual definida sota un observador a 100 m, direcció zenital, slab de 10 km i fase isòtropa. L’integral independent és:

```text
J = exp(κh) [exp(-2κh)/h - exp(-2κb)/b + 2κ(E1(2κb)-E1(2κh))]
Bλ = Pλ · a(0) · βsca · phase(-1) · J
h = z_observador - z_font; b = z_superior - z_font
```

La comprovació addicional integra directament en `s` amb GL32 compost en 256 segments, sense el canvi `sinh` ni GK. Radiància a 550 nm: `2,696e-08 W m^-2 sr^-1 nm^-1`; error LOS estimat `1,339e-21`. Els contrasts E1 i GL compost coincideixen a la precisió mostrada del `float64`; això no significa error físic zero. Les proves repeteixen E1 amb tres extincions i tres fases analítiques.

El rectangle de 2×2 km, centre a 3 km est, observat a azimut 30°/elevació 60°, equival a quatre cel·les de 1×1 km amb potència dividida per quatre. Diferència relativa: `9,951e-13`. La radiància és `5,364e-10 W m^-2 sr^-1 nm^-1`. Els sweeps espacials 10⁻⁴/10⁻⁶/10⁻⁸ conserven el resultat a la precisió mostrada. Proves addicionals roten el raster a 0°, 37° i 90°.

El benchmark F5 extens de 20×20 km requereix més refinament: en el cas isòtrop τ=0,1, la radiància passa de `8,240620811·10⁻¹²` (ordre 8) a `8,241165968·10⁻¹²` (16), `8,241166063·10⁻¹²` (32) i el mateix valor a 64. La primera diferència és `6,62·10⁻⁵` relativa: l’oracle no l’accepta com a convergit i exigeix les dues refinacions posteriors.

## Ruta espectral i fase fina

SPD Kelvin 4.000 K derivada de les taules CIE verificades, **401 nusos (380–780 nm)**. Dispersió definida `10⁻⁵(550/λ)⁴ m⁻¹` i absorció constant `10⁻⁵ m⁻¹`; són una fixture espectral, no el model Bodhaine ni una atmosfera urbana calibrada. La ruta no usa SpectralBandSet. Fase HG g=0,6 analítica contra taules normalitzades sobre cosinus:

| Mostres | Màxim desajust relatiu de radiància als 401 nusos |
|---:|---:|
| 4,097 | 1,047e-06 |
| 8,193 | 2,625e-07 |
| 16,385 | 6,559e-08 |

El refinament redueix el desajust aproximadament per quatre en duplicar la resolució. Les fases isòtropa, Rayleigh escalar i HG també integren a la unitat sobre l’esfera en un contrast GL independent. No s’ha implementat una biblioteca aerosol Mie ni la compressió Legendre del runtime.

## F5: dispersions múltiples independents

Rectangle definit de 20×20 km al terra, centre 15 km est del detector, potència 1.000 W amb SPD plana 400–700 nm i perfil angular lineal 0–90° que acaba exactament a zero. Observador al terra, vista zenital, slab 10 km, albedo `ω=0,8`, profunditats òptiques 0,1/0,3/1. A 550 nm: **262.144 trajectòries iid per cas**, generador PCG64, llavor 7601, màxim 128 dispersions.

Es mostreja una longitud lliure exponencial amb extinció κ i una nova direcció segons la fase recíproca. Una trajectòria que arriba al rectangle aporta radiància de frontera `Lλ·ωⁿ`; terra exterior i cel són negres. La mitjana de trajectòries de primer ordre es contrasta amb SG-REF determinista. `higher_orders` és un estimador aparellat, separat del primer ordre; la ràtio F5 usa la mateixa parella i conserva la covariància.

Regla diagnòstica congelada: diferència del primer ordre ≤6 errors estàndard empírics + error determinista estimat. És un contrast prospectiu d’un estimador iid limitat, **no una certificació probabilística a 6σ ni un interval físic**. Tots nou casos passen; els ordres superiors són detectats amb més de 6 errors estàndard. El biaix és `1 - single/all_orders` (infraestimació respecte del total de referència); ± correspon a **un error estàndard empíric de la ràtio pel mètode delta**, no un interval de confiança.

| Fase | τ | Biaix F5 (%) ± 1 SE | Primer ordre: diferència/SE | Ordres superiors/SE | Cota cua / total estimat |
|---|---:|---:|---:|---:|---:|
| Isòtropa | 0,1 | 13,931 ± 0,889 | 0.039 | 14.76 | 1,200e-10 |
| Isòtropa | 0,3 | 34,198 ± 0,755 | 0.909 | 38.40 | 4,511e-11 |
| Isòtropa | 1,0 | 68,162 ± 0,525 | 1.123 | 84.47 | 2,167e-11 |
| Rayleigh escalar | 0,1 | 12,427 ± 0,867 | 0.675 | 13.61 | 1,265e-10 |
| Rayleigh escalar | 0,3 | 31,303 ± 0,762 | 0.372 | 35.61 | 4,854e-11 |
| Rayleigh escalar | 1,0 | 66,450 ± 0,552 | 0.989 | 80.82 | 2,343e-11 |
| HG g=0,6 | 0,1 | 19,809 ± 2,118 | 1.832 | 8.55 | 5,099e-10 |
| HG g=0,6 | 0,3 | 43,311 ± 1,454 | 0.426 | 23.74 | 1,522e-10 |
| HG g=0,6 | 1,0 | 81,365 ± 0,687 | 1.037 | 60.61 | 5,153e-11 |

La cota de truncament és independent de l’error mostral: radiància de frontera limitada `Lmax`, multiplicada per `ω^(129)`. Qualsevol trajectòria restant pesa com a màxim aquesta quantitat; la probabilitat restant és ≤1. `Lmax` s’acota amb `cosθ≥2(π/2−θ)/π` i el màxim als nusos del perfil lineal. Màxima cua/total estimat de la matriu: `5,099e-10`. Aquesta ràtio usa un total mostral; la cota absoluta reportada és la que té justificació analítica.

**Límit material:** el rang de biaix és propi d’aquests benchmarks i de les seves fases/òptiques/fonts. No és una cota universal de la v1 urbana, no és una correcció per a Barcelona i no homologa C/H. F5 queda quantificat en aquest domini de referència; qualsevol nou domini necessita contrast propi abans d’afirmar-ne l’error estructural. El CLI rebutja F5 amb font puntual, perfil angular superficial no limitat o albedo fora de (0,1).

![Dispersió múltiple i convergència de fase en els benchmarks definits](convergencia-i-biaix-f5.png)

## Fonts C reals: realista i Kelvin

Lectura efectiva de `I:\TerraLab\data\earth\light-pollution\vj146a2\2026\256\VJ146A2.A2026256.h18v04.002.2026264085938.h5`, SHA-256 `2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762`. NOAA-20, Collection 002, data 2026-09-13, fila 2067/columna 520, QA 0, radiància L3 original 139,34158325195312 nW cm⁻² sr⁻¹. Manifest RSR instal·lat: `I:\TerraLab\data\earth\light-pollution\viirs-rsr\research\noaa-multisat\prepared\noaa-20-diagnostic-rsr.json`, MGS de referència, sense ampliar-ne la validesa instrumental fins a 2026.

Tres configuracions (realista, Kelvin 3.000, Kelvin 6.500), cadascuna amb tres mescles base i dos patrons angulars: **18 alternatives propagades individualment**, normalització `constant_photopic_flux`. Observador a la mateixa latitud del píxel i 0,03° a l’oest; direcció 90°/60°, slab definit amb fase Rayleigh i radiància a 450/550/650 nm. Tots els resultats conserven `CONDITIONAL_L3`, `relative m^-2 sr^-1 nm^-1`, configuració, observació, QA, RSR, SPD, hipòtesis i signatura.

Exemple de sensibilitat, mateixa alternativa LED dominant/uniforme: substituir 3.000 per 6.500 K multiplica la radiància relativa a 450 nm per `3.0225` i a 650 nm per `0.4714`. És una intervenció sota hipòtesis, no un canvi urbà observat. Els perfils uniformes usen 189 avaluacions LOS totals; els cosinus tabulats en necessiten 91.329, tots convergits als ordres espacials 8/16/32. L’eina és offline i no té objectiu de latència interactiva.

El context de 7.5.1 conserva `skyRadiance=null/transport_pending` per al producte UI. L’embolcall de 7.6 té `calculationStatus=offline_reference_complete` i `referenceRadiance` propi: no es presenta com un frame de producte ni modifica el cel històric.

## Reproducció

Amb dependències del backend instal·lades, des de l’arrel:

```powershell
python -X utf8 tools/run_sg_ref_step7_6.py --output .runtime-sgref-resultats.json --with-real-black-marble --data-root I:\TerraLab
python -m pytest backend/tests -q -p no:cacheprovider --basetemp=.runtime-sgref-regressio --tb=short
python -m ruff check backend/src/terralab3d/domain/light_pollution/reference_transport.py backend/src/terralab3d/domain/light_pollution/reference_multiple_scattering.py backend/tests/test_reference_transport_step7_6.py tools/run_sg_ref_step7_6.py
python -m pyright backend/src/terralab3d/domain/light_pollution/reference_transport.py backend/src/terralab3d/domain/light_pollution/reference_multiple_scattering.py tools/run_sg_ref_step7_6.py
python -X utf8 tools/validate_docs.py
python -X utf8 tools/check_doc_links.py
```

Sense `--with-real-black-marble` es poden executar tots els contrasts S/F5 i la ruta CIE empaquetada sense assets externs. Amb l’opció, la manca o incompatibilitat del grànul/RSR és un error; no es fabrica una observació ni es canvia de sensor/dia. La sortida JSON només substitueix el fitxer final després dels contrasts; Ctrl+C o una excepció no publiquen resultats parcials. L’API Python també admet callbacks de cancel·lació cooperativa.

Les fixtures estan al [CLI](../../../tools/run_sg_ref_step7_6.py) i als [tests independents](../../../backend/tests/test_reference_transport_step7_6.py); el JSON inclou les entrades, revisions i signatures necessàries per a futurs gates. Les SPD CIE reproduïdes són dades/derivats amb atribució CIE i CC BY-SA 4.0, segons el [manifest empaquetat](../../../backend/src/terralab3d/infrastructure/catalogs/spectra/manifest.json). El codi no adopta aquesta llicència de dades.

## Regressions, documentació i límits del tancament

**35 proves noves i 282 proves backend superades.** [Sortida pytest](proves-backend.txt) i [comprovacions estàtiques](comprovacions-codi.txt). Ruff i Pyright dels mòduls nous i CLI: zero errors/avisos. La comprovació `pyright backend/src` conserva els mateixos 67 errors/3 avisos preexistents de 7.5.1; [comparació de diagnòstics](pyright-backend-comparacio.json), sense diagnòstics nous. No es presenta com a verda. No s’ha modificat el frontend ni s’ha repetit la verificació visual de 7.5.1: les seves captures són històriques del control, no de radiància calculada.

Auditoria documental proporcional: referències de 7.6 traslladades a `completat/`, dependència entrant 7.7 normalitzada sense executar-la; README, inventari, manual, contractes, decisions S1/F5 i perfil v2 coherents. El perfil v1 i l’evidència de 0,01 mag/238 casos de 7.4 es conserven. [Sortida del validador](auditoria-documental.txt): 558 incidències mecàniques heretades inicials i 546 finals, cap enllaç local trencat després del tancament ni incidència dels passos executables 7.6/7.7. La skill `plan` ha estat accessible i aplicada; `terralab-manel-style`, esmentada a les normes, no està disponible en els roots inspeccionats i no s’ha pogut aplicar.

**7.6 completat en el domini declarat; punt de represa 7.7, encara no executat.** Atmosfera variable de 7.8–7.10 i terreny/curvatura de 7.11 exigiran ampliar i revalidar l’oracle abans de comparar aquests dominis. 7.12 haurà de preregistrar la tolerància runtime↔SG-REF amb evidència del mateix domini; 7.16–7.24 continuen responsables d’incertesa física i H. La connexió gràfica física dels controls continua a 7.25–7.27.

## Fonts consultades

- [SciPy `quad_vec`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad_vec.html), 2026-10-18: algorisme adaptatiu vectorial i norma d’error. Llicència BSD-3-Clause comprovada a les metadades de la distribució SciPy 1.16.2 instal·lada.
- [Cinzano i Falchi (2012)](https://arxiv.org/abs/1209.2031), 2026-10-18: model més ric amb dispersions múltiples i altres processos; cap còpia de codi LPTRAN ni equivalència completa declarada.
- [Whitney (2011)](https://arxiv.org/abs/1104.4990) i [NASA (2019)](https://ntrs.nasa.gov/api/citations/20190026727/downloads/20190026727.pdf), 2026-10-18: referències metodològiques Monte Carlo i traçat invers. La cota específica de cua i el contrast E1 són derivacions explícites d’aquest benchmark.
