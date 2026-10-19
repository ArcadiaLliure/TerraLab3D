# Pas 7.9 — Dispersió simple monocromàtica i B1

Validació del 2026-10-19, Europe/Madrid. Base `ee35393` més els canvis de B1, amb Python 3.13.7, NumPy 2.3.3 i SciPy 1.16.2. [Protocol prospectiu](protocol-b1-v1.json) congelat abans de la primera prova/mesura, sense modificar-lo segons els residuals.

## Domini i resultat científic

El mateix `PropagationKernel` integra ara radiància espectral de dispersió simple a una longitud d’ona identificada: **550 nm** a B1. Admet fonts puntuals S, rectangles uniformes integrats directament i amplituds relatives amb el contracte C. La fixture C d’aquesta campanya prova escala/unitats; no és una nova observació Black Marble ni una homologació urbana. El zenit passa pel mateix operador i integrador que 0,5–90°.

El medi és escalar, sec i prescrit. P/T/n provenen d’`OpticalField`; l’aerosol té extinció, albedo, fase, procedència i versió explícites per tile. L’estat aerosol no es dedueix de RH o del nom «standard». Absorció gasosa espectral, núvols, polarització, visibilitat DEM/globus i refracció no es calculen. La geometria esfèrica ECEF/ENU es reutilitza de B0; això no anticipa el model de visibilitat física de 7.11.

Les fixtures integren fins a 10 km, amb un sostre definit; no s’atribueix error nul a la contribució atmosfèrica exterior a aquest domini. Els perfils estàndard de 7.8 poden arribar a 50 km, però aquesta campanya no homologa una atmosfera completa ni estima el biaix del sostre.

El resultat és `W m^-2 sr^-1 nm^-1`, o `relative m^-2 sr^-1 nm^-1` per l’escala C. És una mostra monocromàtica; encara no és la integral d’una banda finita, el transport espectral complet de 7.10 ni la radiància del producte connectada a la UI. El gate runtime↔SG-REF és 7.12; H continua pendent.

## Rayleigh, aerosol i convenció angular

`PhaseFunction` comuna suporta isòtropa, Rayleigh escalar amb despolarització, HG etiquetat `hg_fallback` i taula lineal en cosinus. Totes tenen densitat en sr⁻¹ i integral 1 sobre 4π. La taula es normalitza amb la seva integral lineal exacta; no hi ha compressió Legendre. μ=1 és dispersió endavant. Les proves integren independentment normalització i primer moment HG, incloent g negatiu.

El model molecular usa l’ajust publicat de **Chance–Spurr 1997, equacions 2–7**, dins de 200–1000 nm. Calcula secció eficaç i despolarització coherents amb el mateix King factor. A 550 nm: σ=4,534059952918016·10⁻³¹ m² i δ=0,015517041791854239 en la convenció del dossier. La densitat molecular local n=P/(kBT) determina βR=nσ en m⁻¹; Rayleigh aporta la mateixa extinció que dispersió. Les proves comproven explícitament cm²→m² i cinc longituds d’ona dels límits/interior del model.

És una aproximació escalar quasi-elàstica agregada de dispersió molecular: no resol les línies Raman ni la polarització. Les constants històriques de la parametrització òptica tenen procedència separada del kB SI actual utilitzat per n. La còpia Bodhaine enllaçada al dossier no ha estat accessible en aquesta sessió; no s’afirma haver-ne implementat ni verificat el model complet.

L’aerosol principal és **prescrit**: extinció 10⁻⁵ m⁻¹, albedo 0,9 i HG g=0,65 explícit de fallback. El camp homogeni té P=101.325 Pa i T=288,15 K constants; la seva procedència es requalifica com a fixture i no es presenta com a perfil COESA. També es contrasten un gradient lateral 10⁻⁵/3·10⁻⁵ m⁻¹ i el perfil COESA sec amb nusos cada 1.000 m. Els zeros de les fixtures Rayleigh-only/isòtropa/absorció pura són condicions definides del benchmark, sense convertir dades absents en zero.

La fase tabulada de referència és una fixture analítica de dos lòbuls HG, amb pesos 0,85/0,15 i g=0,75/−0,3. No és Mie ni una mesura d’aerosol. El refinament 2.049/4.097/8.193 nusos dona errors relatius màxims 8,47754·10⁻⁶ / 2,09883·10⁻⁶ / 5,22215·10⁻⁷ sobre 2.003 cosinus fixos. La comparació de radiància usa la definició analítica independent, de manera que el residual també inclou l’aproximació de la taula.

## Transport, trajectes i dependències

Per cada node P, el kernel calcula `Iλ(source→P)/r² × [βR PR + βsca,aer Paer] × exp(−τsource−τobserver)`, i integra en ds. **No hi ha un segon factor invers de distància fins a l’observador.** La prova isòtropa òpticament prima té antiderivada independent i comprova aquesta cadena d’unitats. La linealitat inclou amplitud i suma de fonts compatibles.

`optical_paths.py` talla els dos trajectes ECEF a les cares de tile i a totes dues arrels dels límits d’altura esfèrica. Admet altura no monòtona; els buits laterals positius fallen, sense emplenar-los. La tolerància 64 ε R controla l’arrodoniment vertical als extrems del suport i als nusos compartits de capes contigües. S’ha corregit el cas de font/observador exactament a 1.000 o 5.000 m fora de l’equador; no es relaxa la cobertura lateral. El paral·lelisme manté el factor 8 ε i la propietat semioberta dels tiles.

La transmissió integra βext=βR+βext,aer amb GK7/15; en un segment P/T constant i aerosol constant usa l’expressió homogènia exacta βext·distància. Aquesta branca analítica no és una LUT ni una cache de propagació. L’aerosol també admet un perfil exponencial prescrit amb escala positiva, sense pretendre inferir-lo de dades meteorològiques.

Els rectangles usen tensor Gauss–Legendre directe sobre dA/A, en el seu pla tangent i orientació. No s’aproximen al centre. L’ordre queda a la configuració/signatura; la fixture es calcula amb ordre 4 i es contrasta amb ordres de referència 8/12/16. No hi ha una cota universal de l’error d’àrea. Els passos d’acceleració espacial continuen pendents.

Les dependències recollides durant el càlcul inclouen els dos trajectes, encara que un tile no sigui travessat per la LOS de l’observador. La signatura utilitzada combina capes P/T, origen/radi/instant/revisió, model de banda i només els aerosols dels tiles utilitzats. La signatura d’entrada conserva tota la configuració. La prova de canvi de versió/extinció al trajecte de font invalida les signatures i modifica el resultat. No s’ha implementat reutilització de resultats.

## Referència ampliada i revalidada

`reference_single_scattering.py` amplia SG-REF amb una revisió pròpia `sg-ref-spherical-monochromatic-v1`. Construeix ECEF/ENU i arrels amb NumPy, interpola P/T independentment, usa GK21 per LOS i GL per transmissió/àrea amb SciPy. No crida les fases, `OpticalField.sample`, `traverse`, `segment_path`, `optical_depth` ni GK7/15 del runtime. Una prova substitueix els mètodes runtime per errors i executa igualment la referència.

Les referències de radiància homogènia plana/F5 de 7.6 i de columnes de 7.8 es conserven intactes. Abans de comparar el candidat s’han verificat el cas isòtrop amb antiderivada, la transmissió homogènia, normalització angular, refinament d’àrea i convergència de la nova referència. Aquesta ampliació no homologa el nou domini per a dispersió múltiple.

Per cada diagnòstic es registren tres toleràncies GK21, 10⁻⁷/10⁻⁹/10⁻¹¹, amb ordres de trajecte i àrea 8/12/16. Els canvis entre les dues darreres referències són de l’ordre de l’arrodoniment en aquestes fixtures. L’error LOS de referència, el canvi d’àrea/trajecte, l’error d’interpolació i el biaix físic són magnituds diferents. No s’atribueix cap significat físic als residuals que arriben al límit de float64.

| Diagnòstic a 90° | Radiància runtime | Runtime/SG-REF − 1 |
|---|---:|---:|
| Rayleigh | 7,151464650535635·10⁻¹⁵ | −2,44249·10⁻¹⁵ |
| Rayleigh + HG | 6,969937833127469·10⁻¹⁵ | −4,99600·10⁻¹⁵ |
| Rayleigh + taula vs fase analítica | 7,139145600354013·10⁻¹⁵ | −5,55784·10⁻⁸ |
| Gradient aerosol lateral | 5,821050166521760·10⁻¹⁵ | −5,10703·10⁻¹⁵ |
| Perfil vertical estàndard | 5,206500055157555·10⁻¹⁵ | −1,06581·10⁻¹⁴ |
| Rectangle directe | 6,970854462996214·10⁻¹⁵ | −4,55191·10⁻¹⁵ |
| Escala relativa C definida | 6,969937833127469·10⁻¹⁵ | −4,99600·10⁻¹⁵ |

Unitat de les sis primeres files: W m⁻² sr⁻¹ nm⁻¹; la darrera és relativa amb les mateixes dimensions geomètriques/espectrals. **Cap PASS/FAIL de discrepància runtime↔SG-REF** s’aplica en aquest pas.

![Refinament de fase i residuals diagnòstics de radiància](fase-i-residuals-b1.png)

## Proves, errors i compatibilitat

- **21 proves noves; 384 proves backend superades**, en 41,53 s: [sortida](proves-backend.txt).
- Ruff/Pyright dels mòduls, proves i CLI afectats sense incidències. Pyright global conserva el mateix multiconjunt de **67 errors i 3 avisos previs**, sense diagnòstics nous: [comparació](pyright-backend-comparacio.json).
- Cancel·lació cooperativa en quadratura, transmissió i oracle. Prova amb fil real de substitució de revisió mentre B1 és en curs: resultat antic descartat, nou resultat publicat pel guard existent. No hi ha nou scheduler ni recursos GPU.
- Es rebutgen fases incompletes/negatives, coeficients no finits, albedo invàlid, manca de cobertura de qualsevol trajecte, unitats relatives incompatibles i intersecció singular de la LOS amb una font puntual o rectangle.
- Resultat B1 esquema 3; B0 sense camp conserva esquema 1 i el diagnòstic de columnes conserva esquema 2. La fixture B0 principal de 100 fonts/900 LOS conserva exactament `21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e` (valors, comptadors i serialització).
- Els quatre casos de columnes de 7.8 també conserven exactament els resultats serialitzats després de corregir els nusos verticals: [regressió](regressio-columnes.json). La transmissió exponencial prescrita es contrasta addicionalment amb una antiderivada vertical, sense augmentar l’abast meteorològic del model.
- L’error retornat per LOS és l’estimació de la quadratura exterior. `max_one_leg_optical_depth_error` reporta separadament l’estimació màxima d’un trajecte. No es presenta cap d’aquests valors com a cota total garantida ni com a incertesa física, i l’error d’àrea continua sense cota universal.

## Reproducció i fonts

Amb el backend instal·lat, des de l’arrel:

```powershell
python -X utf8 tools/benchmark_skyglow_b1.py --output-dir .runtime-b1-resultats
python -X utf8 tools/plot_skyglow_b1.py --input .runtime-b1-resultats/resultats-b1-v1.json --output-dir .runtime-b1-resultats
python -m pytest backend/tests -q -p no:cacheprovider --basetemp=.runtime-b1-full --tb=short
```

`--diagnostics-only` executa els contrasts i genera el JSON sense campanya temporal; no equival a B1 mesurat. La CLI només substitueix els fitxers finals en acabar tots els controls. Ctrl+C atura el treball; les sortides parcials no es publiquen com a evidència vàlida. Matplotlib és opcional i només necessari per a les figures. Les dues figures finals s’han inspeccionat visualment.

Fonts primàries consultades el 2026-10-19: [Chance i Spurr (1997)](https://lweb.cfa.harvard.edu/atmosphere/publications/1997AOring.pdf), equacions 2–7; [Henyey i Greenstein (1941)](https://articles.adsabs.harvard.edu/pdf/1941ApJ....93...70H), fase analítica; [NIST SCATMECH, documentació de fases](https://pages.nist.gov/SCATMECH/docs/phase.htm), convencions de g i taules. S’han implementat fórmules i constants amb proves pròpies, sense copiar codi extern ni redistribuir PDFs. La normalització 4π és explícita i provada; no s’hereten normalitzacions implícites de biblioteques externes.

La skill `plan` s’ha carregat i aplicat. `terralab-manel-style`, referenciada per les normes, no és instal·lada als directoris disponibles; s’han aplicat les normes locals. Durant l’execució s’han detectat eliminacions externes de nou àlies antics de tasques 7.1–7.9. No s’han revertit ni es compten com a feina d’aquest pas; l’auditoria en separa l’efecte.

## Campanya temporal

Cinc escalfaments complets i **60 passades mesurades**, amb 10 per configuració N=1/10/25/50/100/200 i nou elevacions. La sèrie principal té 100 fonts puntuals definides i 900 LOS per passada. Durada total 1280.15 s; CPU AMD Ryzen 5 5600X 6-Core Processor. [JSON complet](resultats-b1-v1.json) i [CSV per passada](passades-b1-v1.csv), relacionats amb `runId`/`run_id`.

| Fonts | Passades | p50 (ms) | p95 (ms) | p99 (ms) |
|---:|---:|---:|---:|---:|
| 1 | 10 | 273.47 | 312.85 | 313.99 |
| 10 | 10 | 2251.59 | 2370.51 | 2373.48 |
| 25 | 10 | 5440.81 | 5708.12 | 5740.45 |
| 50 | 10 | 10328.15 | 12054.73 | 12456.66 |
| 100 | 10 | 20193.32 | 24709.70 | 25225.19 |
| 200 | 10 | 39731.14 | 46863.85 | 47115.95 |

Desviació prospectiva: `campaign_exceeded_600s;at_least_10_measured_passes_per_configuration`. S’aplica el mínim de 10 passades quan la campanya supera 600 s, sense canviar llindars físics ni ometre els cinc escalfaments. RSS/peak són working set i pic de vida del procés; no s’atribueixen a una única passada. GPU no utilitzada; flags de compilador, temperatura i throttling desconeguts es mantenen absents amb estat explícit. Les proves i comprovacions estàtiques es van acabar durant els escalfaments, abans de les passades mesurades. Una campanya preliminar es va interrompre en detectar el cas límit de nusos verticals; aquestes passades no formen part del JSON/CSV final.

Les posicions de font es reutilitzen de les fixtures geomètriques B0 amb seed canònica; ara són fonts **puntuals definides**, no rectangles aproximats. Un diagnòstic separat integra el rectangle real. El medi principal és homogeni prescrit sobre geometria esfèrica; no és l’escenari pla amb visibilitat física ni atmosfera urbana mesurada. No hi ha AD, cache o acceleració, ni SLO de producte. L’error radiomètric de les 900 LOS no es fabrica: els residuals es calculen només als diagnòstics explícits.

![Escalat i histograma mesurats de B1a](escalat-i-latencia-b1.png)

L’auditoria documental consta a [resum diferencial](auditoria-documental-resum.json) i [sortida](auditoria-documental.txt). **Pas 7.9 completat en el domini declarat; punt de represa 7.10, sense executar-lo aquí.**
