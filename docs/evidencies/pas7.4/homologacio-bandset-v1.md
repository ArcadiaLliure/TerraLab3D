# Pas 7.4 — Homologació numèrica espectral del domini tabulat v1

Data: 2026-10-18. **Criteri aprovat i congelat abans de la comparació de candidats.**

## Requisit i procedència

TerraLab3D ha aprovat explícitament un màxim de **0,01 magnituds equivalents** per integral radiomètrica positiva contra l'oracle espectral fi. Per definició de magnitud, el quocient de radiàncies queda entre `10^(-0,01/2,5)` i `10^(+0,01/2,5)` (desviacions aproximades −0,917 % i +0,925 %). És un **pressupost d'error numèric del producte**, no una precisió absoluta del skyglow ni una dada NASA.

El registre [TL3D-SKY-V3-SPECTRAL-001 v1](criteri-preregistrat-v1.json), amb mètrica, règim de senyal gairebé nul, domini, responsable TerraLab3D, versió i data `2026-10-18T11:59:32Z`, es va desar **abans d'executar l'avaluació de candidats**. SHA-256 del registre congelat: `0e6bcee3e33a66b2fcbf8adc0dcce67abbd995dff89c7674d5c9a4c2f2cd3c6a`. El [JSON d'avaluació](avaluacio-bandset-v1.json) conté la mateixa suma i el [script](../../../tools/evaluate_spectral_bandset_step7_4.py) refusa executar-se si el registre no declara aquest estat de congelació.

La [publicació de Bará, Tapia i Zamorano (2019)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6470928/) dona `σ=0,06 mag_AB/arcsec²` per al punt zero calibrat dels TESS-W i SQM-LU-DL estudiats (taules 1 i 2). Motiva que TerraLab3D exigeixi una discretització molt menor que aquesta escala instrumental, **sense extrapolar l'estudi a VIIRS** ni usar `0,06` com a tolerància del model físic.

## Domini i tractament del zero

La prova cobreix les nou SPD LED CIE, cinc HP, L41, dues mescles sintètiques d'àrea visible igual, quatre línies triangulars estretes amb nusos explícits i una SPD nul·la; cadascuna es combina amb V(λ), XYZ X/Y/Z i les cinc RSR DNB històriques disponibles. També hi ha casos cúbics `SPD × V(λ) × RSR` per LED, HP, mescles i línies estretes. Són **238 integrals individuals** en la intersecció de suport de cada corba amb 380–780 nm: 226 positives resoltes i 12 sota la regla absoluta. Les taules CIE i les RSR s'han verificat pels manifests i checksums de [CIE](cie-asset-manifest.json) i [7.3](../pas7.3/revisio-multisatel-lit.md). Les RSR SNPP 2013 i J1/J2 de prelanzament romanen **diagnòstiques**; no existeix aquí una RSR Black Marble 2026 homologada.

Per a integrals positives prou separades del soroll numèric, la mètrica és `|2,5·log10(I_c/I_ref)| ≤ 0,01`. L'escala `η=10^(0,01/2,5)−1` deriva únicament del requisit aprovat. Si `0 ≤ I_ref ≤ u_ref/η`, inclòs zero exacte, es comprova `|I_c−I_ref| ≤ u_ref` en unitats de la integral, sense dividir per una referència gairebé nul·la. `u_ref` està definit **abans** de les comparacions al registre com el màxim de les diferències de quadratura Q8/Q16/Q32, el contrast Q32 amb una integral analítica Decimal de 50 xifres i `N·ulp(A)`, on `A` és una escala física superior de la integral ponderada. No s'ha ajustat aquest règim després de veure els candidats.

## Oracle, candidats i resultat

L'[oracle fi](../../../backend/src/terralab3d/domain/light_pollution/spectral_oracle.py) usa Gauss–Legendre per interval amb tots els nusos. Una segona ruta independent integra analíticament cada polinomi interpolat en aritmètica Decimal de 50 xifres. La discrepància relativa màxima observada entre Q8 i D50 en les integrals positives resoltes és `2,19·10⁻¹¹`, molt inferior a `η≈9,25·10⁻³`. L'estimador conservador `u_ref/I_ref` arriba a `1,51·10⁻³` en un senyal DNB diagnòstic molt feble; aquesta cota de salvaguarda és separada de la discrepància observada i no és una incertesa instrumental. L'error de quadratura, l'error de discretització de cada candidat i la incertesa RSR (`null`, no quantificada) apareixen en camps diferents del [registre per cas](avaluacio-bandset-v1.json).

| Representació candidata | Casos PASS | Casos FAIL | Màxim error de magnitud positiva |
|---|---:|---:|---:|
| Simpson uniforme de 5 nm | 183/238 | 55 | 0,554622 mag |
| Simpson uniforme d'1 nm | 194/238 | 44 | 1,870559 mag |
| **Unió adaptativa de nusos + Simpson** | **238/238** | **0** | **1,55·10⁻¹¹ mag** |

Les graelles uniformes perden línies subgraella; una mitjana d'errors ocultaria els FAIL. La representació escollida és [`tl3d-sky-v1-knot-union-simpson-1`](../../../backend/src/terralab3d/domain/light_pollution/spectral_bandset.py): crea una banda a cada interval dels nusos de SPD i resposta i usa Simpson amb límits interns al suport. El nombre de bandes varia amb les dades (`26–1051` en aquesta matriu), **sense selecció per temps**. Amb una SPD lineal a trossos i com a màxim dues respostes també lineals, l'integrand és un polinomi de grau màxim 3 a cada interval; Simpson és exacte matemàticament en aquest domini. Això inclou mescles convexes si conserven els nusos i línies estretes **ja tabulades**. Les proves contrasten l'implementació amb l'oracle independent i amb una integral analítica, incloent casos aleatoris deterministes.

`bandSetId` inclou versió de l'algorisme i SHA-256 dels límits de banda; `inputSignature` inclou identitat, valors i longituds d'ona de totes les corbes. Canviar bandes canvia el primer; canviar una RSR o SPD sense moure els nusos canvia el segon. Una cache ha d'usar **tots dos** i rehomologar una nova versió de l'algorisme o nous assets. Hi ha proves golden d'identitat i d'invalidació. Això no suposa que el futur kernel ja implementi aquesta cache.

## Límits i revalidacions

La homologació és **numèrica sobre corbes tabulades i fixtures declarades**. La interpolació CIE/RSR no reconstrueix estructura subgraella desconeguda ni aporta la incertesa instrumental de la RSR. No valida l'operador de font Black Marble nocturn de 2026, la inferència L3→SPD/angular, l'absorció gasosa, la dispersió espectral atmosfèrica ni SQM/TESS. El Pas **7.10** ha de repetir el gate de discretització sobre transport amb gasos i dispersió; el **7.14**, sobre les projeccions fotomètriques. Si en un domini nou se supera `0,01 mag`, cal revisar i versionar el `SpectralBandSet` i tornar-lo a homologar; **no** relaxar retrospectivament el criteri congelat. Les toleràncies específiques de transport i validació empírica continuen als gates 7.12/7.17.

Reproducció, amb la biblioteca de dades TerraLab configurada:

```powershell
python tools/evaluate_spectral_bandset_step7_4.py --output docs/evidencies/pas7.4/avaluacio-bandset-v1.json
python -m pytest backend/tests/test_spectral_oracle_step7_4.py backend/tests/test_spectral_bandset_step7_4.py -q
```
