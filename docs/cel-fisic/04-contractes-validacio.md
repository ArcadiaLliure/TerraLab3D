# Contractes i acceptació del cel físic

## Configuració

- **skyRenderingMode:** simulated | physical, independent del mode de contaminació lumínica i de l'activació d'atmosfera; preferència persistent i serialitzada.
- **spectralBandCount:** enter positiu configurable, sense dimensió compilada fixa; acompanyat de **spectralBandSetId**, intervals nm, ponderacions, convenció de radiància integrada o mostrejada, rang espectral i revisió de configuració. Si s'ofereixen límits explícits, el nombre ha de coincidir. Configuració invàlida → error tipat, no truncament silenciós.
- **skyPhysicalAvailability:** available | unavailable | initializing; causa i versió; cap fallback silenciós de physical a simulated.
- **observer:** lat/lon, altitud geodèsica/ortomètrica amb datum, altura relativa al terreny si escau, ECEF/ENU i revisió de geometria.
- **atmosphericOpticsRevision:** identificador immutable de perfils i propietats compartides; validesa espacial/temporal i procedència.
- **solarRadianceSource / lunarRadianceSource:** espectre, distància, geometria del disc, fase lunar, irradiància i incertesa amb unitats.
- **physicalSkyResource:** transmittance LUT, multiscattering LUT, SkyView LUT RGB lineal i recursos d'aerial perspective quan calgui; clau de cache, dimensions, espai de color i propietari de GPU.
- **skyRadianceComponents:** artificial, solar/twilight, lunar i naturalMoonless en espai lineal compatible; no sumar magnituds ni colors després de tone mapping.

## Convencions espectrals

Distingir **radiància espectral** en W·m⁻²·sr⁻¹·nm⁻¹ de **radiància integrada per banda** en W·m⁻²·sr⁻¹. Cada conversió usa quadratura/pesos declarats; la radiància de VIIRS DNB és una mesura de banda ampla i no identifica per si sola un espectre d'emissió. Les respostes de SQM/TESS/CIE requereixen espectre o projecció calibrada pròpia, **mai** la inversió de la SkyView LUT RGB. Canviar spectralBandCount invalida caches, LUT científiques i projeccions dependents, no els catàlegs estel·lars.

## Proves obligatòries

1. **Mode:** alternança repetida simulated↔physical sense recrear escena/bridge, conservar l'estat solar/lunar i de skyglow; errors visibles i dispose de recursos.
2. **Bandes:** provar dimensions, límits, identificadors, unitats, suma/integració i invalidació de configuració activa. **No executar sweeps ni benchmarks per determinar el nombre de bandes.** Els benchmarks generals de runtime i la validació científica continuen.
3. **Altitud:** superfície, muntanya, avió, estratosfera, límit superior de l'atmosfera i òrbita; oclusió del planeta, depressió d'horitzó, trajectes tangents, absència de salt en creuar capes i estabilitat ECEF/ENU.
4. **Limbe:** arc diürn dispersat, costat nocturn, terminador, geometria solar i ombra terrestre; la franja no pot ser un anell afegit sense transferència física.
5. **Fonts:** Sol/Lluna independents, fase/distància, disc directe vs dispersió, eclipsis, canvi de temps d'1 s/s i scrub ràpid amb latest-wins.
6. **Ciència:** transmittance i radiància comparades amb casos analítics o solver de referència per la configuració escollida; resposta instrumental amb RSR/FOV/zero point; error/limitacions documentats.
7. **Render:** SkyView LUT RGB lineal, gestió de color i exposició únics, ombres/il·luminació del terreny coherents; cap doble comptatge amb skyglow ni càlcul radiatiu artificial al render loop.
8. **Llicències:** manifests/avisos per cada recurs incorporat, sense restricció comercial ni dades no verificades.

## Condició de sortida

El mode simulat preserva el comportament històric; el físic és calculat, traçable i disponible quan se selecciona; l'altura i el limbe són correctes; no es promet precisió espectral a partir de RGB; l'estat funcional només passa a completat amb proves i evidències reals. Els SLO de GPU i CPU es mesuren independentment del nombre de bandes seleccionat.
