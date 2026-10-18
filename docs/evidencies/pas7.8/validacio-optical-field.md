# Pas 7.8 — Camp atmosfèric estàndard i dependències de travessa

Validació del 2026-10-19 (Europe/Madrid), sobre `bb1f53a` més els canvis d’aquest pas. Python 3.13.7, NumPy 2.3.3 i SciPy 1.16.2. El [protocol prospectiu](protocol-optical-field-v1.json) es va congelar abans de la primera execució; el seu SHA-256 consta als [resultats reproduïbles](resultats-optical-field-v1.json).

## Resultat i domini

El kernel consumeix un `OpticalField` immutable, interpola P/T, deriva densitat molecular i integra columnes en m⁻² travessant 1, 2 o 8 tiles. Registra per LOS els segments i les dependències efectivament mostrejades: identificador/versió de tile, índex de capa i hash de les dades que intervenen en la interpolació. El provider és darrere el port `AtmosphericOpticsProvider`; el kernel no importa infraestructura ni consulta serveis.

El model estàndard és **COESA 1975, NASA TR R-459 publicat el 1976**, limitat a **0–50 km geomètrics d’aire sec**. No s’identifica amb la implementació completa d’US Standard Atmosphere 1976. Les fixtures numèriques d’aquest informe cobreixen 100–10.000 m i una LOS a 45°; les proves analítiques de P/T arriben a 50 km i inclouen els canvis de gradient pertinents.

No es calculen encara coeficients de Rayleigh, aerosols, absorció espectral ni núvols. Els camps corresponents són absents (`None`), amb estat explícit pendent de 7.9/7.10; no s’emplenen amb extinció zero. RH=0 és una hipòtesi seca prescrita i identificada. `quality=prescribed_standard_or_fixture` i `structuralUncertainty=not_quantified` eviten atribuir qualitat observacional o incertesa física a aquesta atmosfera.

## Model, unitats i aproximació vertical

El provider calcula la temperatura per gradients geopotencials i la pressió per hidrostàtica ideal. Empra P₀=101.325 Pa, T₀=288,15 K, g₀=9,80665 m/s², M₀=0,0289644 kg/mol i R*=8,31432 J/(mol·K). La conversió geopotencial usa el radi de la font, 6.356.766 m; la geometria ECEF/ENU conserva l’esfera explícita de B0, 6.371.008,8 m. Són constants amb funcions diferents.

El perfil tabulat afegeix els canvis de gradient als nusos regulars. Interpola log(P) linealment i T linealment en altura geomètrica; calcula n=P/(kBT), en m⁻³, amb **kB=1,380649·10⁻²³ J/K exacte del SI actual**. No reutilitza el valor històric de kB de 1975. Les fórmules analítiques es contrasten en proves amb una implementació Decimal independent de 50 xifres i amb les temperatures publicades dels límits de capa.

La interpolació és una aproximació separada de la quadratura. Sobre 2.003 altures fixes de 0,37 a 9.999,63 m, el refinament dona:

| Pas vertical (m) | Error relatiu màxim de pressió vs model analític |
|---:|---:|
| 1.000 | 5,31883·10⁻⁴ |
| 500 | 1,34899·10⁻⁴ |
| 250 | 3,39686·10⁻⁵ |
| 125 | 8,51275·10⁻⁶ |
| 100 | 5,45834·10⁻⁶ |

El pas predeterminat és 100 m. Aquest error del model tabulat no és l’error numèric GK ni una cota d’error meteorològic. No s’ha ajustat cap llindar a posteriori.

![Perfils de pressió i temperatura i convergència de la interpolació](perfils-i-convergencia.png)

## Referència independent i contrasts

Abans del contrast multi-tile s’ha afegit `reference_optical_column.py`: oracle offline amb SciPy GK21, interpolació i selecció de tile pròpies amb NumPy i arrels quadràtiques Decimal de 50 xifres. Comparteix les dades d’entrada, la definició de raig i el contracte físic d’interpolació; no crida `OpticalField.sample`, `traverse`, les arrels del runtime ni GK7/15. No és un oracle de radiància variable.

Les proves analítiques, de continuïtat, canvi lateral prescrit, independència de partició, zenit i sentit oest revaliden aquest nou domini de columnes. El transport espectral homogeni pla i F5 de 7.6 queden intactes; les seves evidències històriques no es reetiqueten com a validació d’atmosfera variable. La referència de radiància s’haurà d’ampliar i revalidar a 7.9–7.11 abans de cada nou contrast físic.

| Tiles | Estat | Segments GK7/15 | Columna runtime (m⁻²) | Diferència relativa vs GK21 |
|---:|---|---:|---:|---:|
| 1 | Estàndard sec | 99 | 2,209113793236503·10²⁹ | 0 |
| 2 | Estàndard sec | 100 | 2,209113793236503·10²⁹ | 2,22045·10⁻¹⁶ |
| 2 | Pressió del segon tile multiplicada per 0,8 | 100 | 2,039454436850167·10²⁹ | 5,55112·10⁻¹⁶ |
| 8 | Estàndard sec | 106 | 2,209113793236504·10²⁹ | 0 |

El contrast ×0,8 és una fixture lateral definida, amb revisió/procedència pròpies; no es presenta com a COESA pur ni com a observació. La LOS mesura 13.989,870173 m. Les estimacions relatives d’error de quadratura són de l’ordre de 10⁻¹⁴; no són intervals garantits. El control prospectiu de columna 10⁻⁸ deriva de 10 vegades la tolerància relativa runtime 10⁻⁹, amb referència 10⁻¹⁰. És un control numèric offline. El primer gate radiomètric continua a 7.12 i H continua pendent.

## Referencial, límits i dependències

Els tiles són prismes rectangulars en un **ENU fix del camp**, amb origen explícit i altura radial esfèrica; no es desplacen quan es mou l’observador. No són les cel·les ENU locals de B0 ni un DEM. Els límits laterals són semioberts: mínim inclòs i màxim exclòs. La travessa es talla a les cares reals i als nusos verticals; rebutja solapaments, sortides de cobertura i qualsevol buit positiu representable, sense extrapolar ni omplir-lo.

Per als eixos paral·lels, components de direcció inferiors a 8 ε de float64 es tracten com a zero per estabilitzar l’error de rotació; el factor està serialitzat. Una tolerància 64 ε R controla únicament la consulta dins d’un segment i l’arrodoniment als extrems verticals. No elimina buits entre tiles. Les proves inclouen un buit d’1·10⁻⁸ m i zenit a una frontera lateral per quatre azimuts.

La signatura completa d’entrada inclou totes les dades del camp. La signatura de dependències utilitzades inclou origen, radi, instant, revisió de camp i només les capes/versions realment mostrejades. Canviar un tile o nus no utilitzat conserva aquesta segona signatura; canviar una capa utilitzada la modifica, fins i tot si es reutilitza accidentalment una etiqueta de versió. No s’ha implementat cap cache: la política d’invalidació/reutilització correspon a 7.21.

## Errors, propietat i regressions

Els constructors rebutgen perfils no finits, P/T no positives, dates sense zona, identitats absents, revisions de camp desconegudes i radis incompatibles. El pressupost limita nodes de perfil i segments; el camp és un snapshot immutable sota propietat del consumidor. No hi ha I/O, reenviament per frame, recurs GPU ni nou scheduler.

El guard existent comprova cancel·lació i revisió durant la travessa, la quadratura i la publicació sota lock. Una prova amb fil real suspèn un càlcul, substitueix camp/revisió i comprova que el resultat antic es descarta i el nou es publica. L’oracle també admet cancel·lació cooperativa. La CLI només reemplaça el fitxer final després de tots els controls.

Sense camp, `PropagationResult` conserva esquema 1 i el resultat B0. Amb camp usa esquema 2 i `stage=optical_field_column_diagnostic_not_radiance`. La reproducció de la fixture principal B0 de **100 fonts/900 LOS** conserva exactament el SHA-256 de valors, comptadors i serialització: `21d3453df822b95d56aa508fee6bd9c76e712b27c63f3f03a3222e86e075b53e`. No s’ha repetit la campanya temporal ni s’ha declarat cap nou SLO.

## Proves i reproducció

- **33 proves noves** i **363 proves backend superades**, en 21,08 s: [sortida completa](proves-backend.txt).
- Ruff i Pyright dels mòduls afegits/modificats, proves i eines: sense errors ni avisos.
- Pyright global: mateix multiconjunt de **67 errors i 3 avisos preexistents**, cap diagnòstic nou: [comparació amb baseline](pyright-backend-comparacio.json).
- Auditoria documental: 534 incidències mecàniques heretades inicials i 524 finals després de normalitzar la dependència 7.9, sense incidències noves ni dels passos executables 7.8/7.9. Zero enllaços locals trencats: [resum diferencial](auditoria-documental-resum.json) i [sortida](auditoria-documental.txt). Es conserven les evidències històriques de 7.1–7.7.

Des de l’arrel amb el backend instal·lat:

```powershell
python -X utf8 tools/validate_optical_field_step7_8.py --output .runtime-optical/resultats.json
python -X utf8 tools/plot_optical_field_step7_8.py --input .runtime-optical/resultats.json --output .runtime-optical/perfils.png
python -m pytest backend/tests -q -p no:cacheprovider --basetemp=.runtime-optical-full --tb=short
```

La figura requereix matplotlib opcional. Les proves no depenen de xarxa ni de datasets ERA5/CAMS. La figura generada s’ha inspeccionat visualment. La skill `plan` s’ha aplicat; la skill d’estil `terralab-manel-style` referenciada per les normes no és instal·lada als directoris de skills disponibles. S’han aplicat les normes locals accessibles.

## Fonts primàries consultades

- [COESA 1975 — NASA TR R-459, publicat maig de 1976](https://ntrs.nasa.gov/api/citations/19760017709/downloads/19760017709.pdf): constants, conversió geopotencial, taula 3 i equacions hidrostàtiques. Consultat el 2026-10-19; informe públic del govern dels EUA. S’han implementat les equacions i constants, sense incorporar codi extern ni redistribuir el PDF.
- [NIST — constant de Boltzmann](https://physics.nist.gov/cgi-bin/cuu/Value?k%7Csearch_for=Boltzmann) i [unitat SI de temperatura](https://www.nist.gov/pml/owm/si-units-temperature): valor SI exacte actual, consultat el 2026-10-19. Les fórmules de 1975 de P/T i l’elecció moderna de kB tenen procedències separades.

ERA5/CAMS, dispersió B1, absorció espectral, terreny/visibilitat física, cache, bridge/render i homologació H queden als passos corresponents. **El punt de represa és 7.9; no s’ha executat en aquesta iteració.**
