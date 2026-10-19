# Pas 7.10 — Validació del transport espectral i de l'absorció gasosa

Tancament del 2026-10-19. **Completat offline en el domini prescrit declarat.** 405 proves backend superades, 21 noves. No s'ha executat 7.11 ni el gate radiomètric de 7.12. Les evidències 7.1–7.9 es preserven.

## Operador i compartició de treball

`PropagationKernel` ofereix B2/B4 al mateix entrypoint que B0/B1. Reutilitza SourceModel S/C, geometria esfèrica, travessa, fases i provider COESA. `SpectralOperator` prepara una sola vegada cada SPD/resposta distinta per petició; cada node comparteix posició, distàncies, angles, interseccions, P/T i quadratura de columnes entre totes les λ. Rayleigh usa columna molecular; aerosol usa la seva columna de forma vertical i una llei d'Ångström explícita; gasos usen columnes de les bases lineals de temperatura, no una temperatura mitjana del trajecte.

La quadratura vectorial GK7/15 integra simultàniament aquestes columnes. Els creuaments dels nusos tèrmics de la LUT es parteixen exactament abans de quadrar; s'ometen només components exactament zero. Els coeficients homogenis es comparteixen dins de la LOS. No hi ha AD, reuse de moviment, cache entre peticions, quadtree, FFT, GPU ni transport aproximat/precomputat. S'avaluen els dos trajectes, l'emissió directa d'àrea i el mateix zenit que la resta de direccions; no hi ha un factor de calibratge ni invers del quadrat de distància a l'observador.

El bandset conserva unió de nusos + Simpson de 7.4. L'extensió té identitat `tl3d-sky-v1-transport-knot-union-simpson-1`: 400 intervals a B2 i 800 a la fixture B4; 800/802/803 en els casos espectrals, segons nusos reals de les entrades. No s'ha seleccionat N per rendiment. Es versiona també la signatura de les corbes, gasos, aerosols, unitats, camp i fonts. Esquema 4 amb `bandSetId`, suport en nm de buit i estat gasós explícit; B0 conserva esquema 1 i el seu golden exacte. B2 desactiva gasos amb estat diagnòstic obligatori.

## Dades i domini gasós

La [taula primària Serdyuchenko–Gorshelev](https://zenodo.org/records/5793207), DOI 10.5281/zenodo.5793207, té llicència CC BY 4.0 comprovada a les [metadades conservades](registre-zenodo-consultat.json) i checksum MD5 publicat verificat. La [fitxa de Bremen](https://www.iup.uni-bremen.de/gruppen/molspec/databases/referencespectra/o3spectra2011/index.html) documenta unitats i columnes. Gorshelev et al., AMT 7,609–624 (2014), i Serdyuchenko et al., AMT 7,625–636 (2014), en són les referències científiques.

S'empaqueta el retall original 380–780 nm a 0,01 nm, sense pèrdua, i una LUT de 0,5 nm; cm²/molècula es converteix a m²/molècula. La taula de 193 K té 69 valors negatius visibles i es va rebutjar abans d'avaluar candidats, preservant el protocol v1. V2 restringeix l'entrada a **203–293 K**, sense clipping ni extrapolació. La reproducció dels dos assets és exacta byte a byte; CSV canònic CRLF. [Manifest](../../../backend/src/terralab3d/infrastructure/catalogs/gases/manifest.json), [reproducció](reproduccio-assets.json) i [wheel verificat](assets-wheel.json).

`GasAbsorptionModel` exigeix LUT i perfil explícit per cada espècie/tile de la composició prescrita. Espècies desconegudes, cobertura absent, temperatures o λ fora de suport produeixen error. Aquest catàleg acredita **O3**: no acredita H2O/O2/NO2, dependència de pressió, aire terrestre complet, climatologia real ni H. La incertesa experimental de la taula no es resol amb el pressupost numèric de 0,01 mag. `OpticalField` P/T continua separat de la composició òptica prescrita; cap `None` es converteix en absorció nul·la.

## Pressupost espectral preregistrat

El [criteri original TL3D-SKY-V3-SPECTRAL-001](../pas7.4/criteri-preregistrat-v1.json) es conserva, amb màxim per cas de **0,01 mag**, sense relaxació. El [protocol de domini v3](protocol-gate-espectral-v3.json) congela les noves entrades abans d'avaluar-les. 42 SPD CIE + 5 interpolacions Kelvin + 4 mescles radiants/fotòpiques + 4 triangles estrets; 7 respostes X/Y/Z/V i productes amb V; cas nul separat. Operadors gas, Rayleigh, aerosol i combinat, µ=−1/0/1, α=0/1,3/2, T=223/288,15 K i columnes O3 0/10²²/10²³/10²⁴ m⁻².

L'oracle independent integra amb GL8/16/32 als nusos conjunts, incloent-hi les dades originals a 0,01 nm. La identitat analítica Decimal de 7.4 només correspon als productes polinòmics lineals tabulats; no es declara aplicable a exp(−τ). L'extensió no polinòmica usa convergència GL i terra de representació N·ulp(A), amb cas nul/baixa resolució separat. El camp `maximumOracleRelativeRefinement` del JSON és en realitat el màxim **u_ref/I_ref, inclòs el terra N·ulp(A)**, no només el canvi GL. El llindar de magnitud i el criteri absolut dels casos nuls no s'han canviat.

| Registre | Resultat |
|---|---:|
| Casos de l'espectre complet | 111168/111168 PASS |
| Error total màxim candidat/original | 0.000115210277906 mag |
| Error LUT màxim GL32(LUT)/GL32(original) | 0.000115210277912 mag |
| Error Simpson màxim candidat/GL32(LUT) | 3.45342059395e-10 mag |
| T_eff per banda il·luminada | 326040 casos, 0 errors |
| Error màxim T_eff per banda | 0.000333072654845 mag |
| Bandes buides excloses i comptades | 26040 |

Pitjor cas global: triangle-589.02 × X, combinat. [Resultats](pressupost-espectral.json), [tots els casos comprimits](casos-pressupost-espectral.csv.gz), [T_eff](teff-per-banda.json) i [casos per banda](casos-teff-per-banda.csv.gz). Les mescles Kelvin i radiants/fotòpiques són convexes amb coeficients positius; no impliquen dades urbanes mesurades ni reconstrucció subgraella.

La sanity de Jensen usa T_eff=Σw·exp(−τ)/Σw, mai exp(−Σwτ/Σw). Diferència mínima -3.331e-16, compatible amb arrodoniment float64 preregistrat 50ε; refinament GL màxim de T_eff 1.144e-14. Les bandes sense emissió tenen T_eff indefinit, no una transmissió fictícia u. La correcció final de serialització np.bool→bool preserva exactament tots els casos inicials descomprimits.

Una [cota analítica addicional](cota-lut-atmosfera-50km.json) cobreix l'error de la LUT O3 per a qualsevol T entre 203–293 K i pesos positius, dins de la geometria i composició de la fixture estàndard: |Δσ|max=1.66363600e-27 m², columna màxima conservadora de dos trajectes 4.33157603e+24 m⁻², inclòs el prefix radial descendent possible d'una àrea tangent. Límit de l'error de LUT **0.00782400 mag**, també inferior a 0,01. És una cota de LUT, separada de quadratura/discretització i d'incertesa física; no certifica gasos desconeguts ni cap cua superior a 50 km.

![Pressupost espectral i distribució dels errors](pressupost-espectral.png)

## Comparació B0/B1/B2/B4 i cost exclusiu

Ryzen 5 5600X, Windows 11, Python 3.13.7, NumPy 2.3.3; 100 fonts puntuals S, les mateixes posicions deterministes de B1, 9 elevacions i 900 LOS. B1 conserva la SPD de la fixture històrica; B2/B4 usen CIE LED-B3. Medi homogeni prescrit P/T, 10 km, aerosol HG. Les radiàncies monocromàtiques i les integrals espectrals no es comparen com si fossin la mateixa quantitat.

5 escalfaments/configuració i 10 mesures/configuració, 40 passades mesurades; excepció de més de 600 s congelada abans de la campanya, ordre aleatoritzat amb seed canònica. [Raw JSON](resultats-b0-b1-b2-b4.json), [CSV](passades-b0-b1-b2-b4.csv), [resum](resum-cost-etapes.json).

| Mode | p50 s | p95 s | p99 s |
|---|---:|---:|---:|
| B0 | 0.391040 | 0.416136 | 0.421944 |
| B1 | 21.003399 | 21.933868 | 21.942779 |
| B2 | 27.155274 | 27.488365 | 27.520441 |
| B4 | 29.492934 | 30.347557 | 30.531431 |

| Mode | Geometria s | Mostreig s | Transmissions/fases s | Quadratura/dispatch s | Espectral s | Resta s |
|---|---:|---:|---:|---:|---:|---:|
| B0 | 0.116 | 0.000 | 0.000 | 0.263 | 0.000 | 0.015 |
| B1 | 11.368 | 4.857 | 3.578 | 1.343 | 0.000 | 0.042 |
| B2 | 12.911 | 5.346 | 3.303 | 5.090 | 0.487 | 0.079 |
| B4 | 13.139 | 5.497 | 4.604 | 5.734 | 0.597 | 0.100 |

Els costos de la segona taula són mitjanes de temps wall-clock exclusiu: els fills es resten del pare. Quadratura inclou dispatch i bookkeeping fora dels fills instrumentats; B1 inclou l'aritmètica angular legacy a transmissions/fases. Preparació/interpolació espectral de la LUT entra a l'etapa espectral. Resta inclou signatures, construcció del resultat i comptabilitat dels temporitzadors. No s'atribueix CPU per etapa. RSS màxim de procés i RAM es conserven al raw, sense confondre peak acumulat amb assignacions per iteració. No hi ha SLO ni mesures tèrmiques exposades.

B1 té 120.765 nodes LOS; B2 i B4 en tenen 120.615, amb la mateixa segmentació de 2.833 intervals. La geometria no es repeteix per cada λ. Els **20,1933169 s** històrics de 7.9 es preserven com a campanya no aparellada. Una [repetició final](repeticio-900los-particio-termica.json), després de partir nusos T, confirma les mateixes signatures d'entrada de 900 LOS i els recomptes; és una sola passada, no nous percentils. B4 final: 28.476768 s. B1 sense instrumentació: 19.376479 s, radiàncies exactament idèntiques a la passada instrumentada. No s'infereix una acceleració física de les diferències entre campanyes.

![Cost per etapa i latència de les passades](cost-etapes-i-latencia.png)

## Sostre atmosfèric i cost del medi variable

48 casos: sostres 10/20/30/50 km × elevacions 0,5/5/30/90° × tres medis. El medi homogeni històric s'estén explícitament per quantificar-ne la sensibilitat matemàtica; no es presenta com a atmosfera real. Els altres dos usen COESA 0–50 km amb nusos d'1 km, aerosol H=1.200 m i, a B4, un perfil O3 prescrit amb capa estratosfèrica. [Dades completes](diagnostics-transport-i-sostre.json) i [protocol](protocol-diagnostics-v1.json).

Fracció de radiància de 50 km absent amb sostre de 10 km:

| Elevació | B1 homogeni estès | B1 estàndard | B4 estàndard + O3 |
|---|---:|---:|---:|
| 0.5° | 6.9948491e-09% | 4.5998829e-06% | 7.4488036e-06% |
| 5° | 0.0024860065% | 0.021682352% | 0.020855018% |
| 30° | 26.462384% | 19.122346% | 18.801438% |
| 90° | 51.084289% | 22.794126% | 22.448751% |

Les fraccions molt petites, especialment el B1 homogeni a 0,5°, poden ser inferiors a la resolució de la resta de dues integrals: s'han de llegir amb els errors GK guardats, que no són cotes rigoroses ni inclouen tota la columna. No s'interpreten com una demostració de contribució zero. Al zenit, les diferències de 51,08%, 22,79% i 22,45% són àmpliament superiors als errors numèrics registrats. La sensibilitat al sostre és un error d'abast físic separat dels 0,01 mag espectrals. **Per damunt de 50 km la contribució queda desconeguda; no s'ha fixat un sostre físic definitiu.**

El medi variable és molt més car que la fixture homogènia: a 50 km, B1 estàndard consumeix aproximadament 34–38 s per una LOS i B4 aproximadament 80–81 s, en aquesta diagnosi. Part dels temps diagnòstics es va coexecutar amb altres validacions; no són percentils aïllats de producte. S'han separat de la campanya principal. Els creuaments T explícits van reduir B4 a 0,5°/10 km de 26,86 a 5,63 s i a 20 km de 97,03 a 16,09 s, amb canvis relatius de radiància de l'ordre de 4·10⁻¹⁵. [Abans del canvi](diagnostics-abans-particio-termica.json), [protocol exacte](protocol-particio-termica-v2.json). Aquest cost pendent no es resol introduint les acceleracions de passos posteriors.

![Sensibilitat al sostre atmosfèric](sensibilitat-sostre-atmosferic.png)

## Referències independents i límits de precisió

SG-REF espectral homogeni usa geometria NumPy pròpia, GL espectral i d'àrea, GK21 LOS i fases independents. S puntual es contrasta amb l'O3 original a 0,01 nm; C realista/K de Barcelona conserva geometria, procedència i escala relatives de 7.5.1, amb la mateixa LUT i l'error de LUT separat. Àrea directa 8/12/16 i refinaments espectrals. Les proves impedeixen cridar sample/traverse/fases/integrand del runtime des de la referència.

| Cas | Residual relatiu runtime/SG-REF−1 | Màxim canvi successiu de referència |
|---|---:|---:|
| S_point_LED_B3 | 5.275329e-08 | 2.220e-16 |
| C_realistic_NOAA20 | -6.126954e-08 | 4.110e-13 |
| C_kelvin3000_NOAA20 | -6.162843e-08 | 4.228e-13 |

La columna variable amb gas també es contrasta a 550 nm i sostres 10/50 km, GL de trajectes 8/12/16 i partició tèrmica independent. Les estimacions internes i els canvis successius figuren al JSON. La comparació usa una banda estreta de 0,002 nm contra un punt monocromàtic: el residual inclou l'efecte d'amplada de banda, no s'etiqueta com error pur de transport. **Cap PASS/FAIL de transport abans de 7.12.** El solver espectral fi complet queda homologat aquí només per al seu domini homogeni; el medi variable té contrasts de components/550 nm i la cota O3 separada.

## Proves, regressions i manteniment

405 proves backend, 21 noves; Ruff i Pyright dels fitxers afectats passen. Pyright global conserva 67 errors/3 avisos heretats; la comparació normalitza únicament el doble UTF-8 històric abans de NBSP, sense reescriure l'evidència original. Golden B0 de 900 LOS i quatre resultats de columnes 7.8 revalidats exactament. Wheel construït i assets verificats. Tres figures renderitzades i inspeccionades visualment.

Es preserven els assajos inicials de cobertura 10 km i aerosol constant, la campanya anterior a la partició tèrmica, la primera serialització T_eff i les seves correccions documentades. Les conclusions usen els fitxers finals identificats, sense eliminar mesures ni relaxar criteris. La skill `plan` s'ha aplicat; `terralab-manel-style`, esmentada a les normes, continua absent als dos roots de skills, i s'ha mantingut l'estil/protocol local.

La UI, el renderer, H i els passos 7.11+ no s'han executat. El punt de represa passa a **7.11 pendent**, sense començar-lo. [Pas canònic completat](../../tasques/completat/pas7.10-gas-spectral-kernel.md).

## Auditoria documental i preservació final

389 incidències mecàniques heretades inicials i 387 finals, zero noves i zero enllaços locals trencats; només s’han reparat les dues metadades de dependència entrants de 7.11 i els enllaços de 7.10 traslladat. No s’ha executat 7.11. [Diferencial](auditoria-documental-resum.json). Les 83 evidències existents abans de començar conserven exactament els seus hashes; [comprovació](preservacio-historica.json). Golden B0 `21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e` i quatre columnes idèntics: [regressió](regressio-columnes-i-b0.json).
