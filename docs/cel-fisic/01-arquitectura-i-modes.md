# Arquitectura del cel físic i commutació simulat/real

## Decisió

`skyRenderingMode = simulated | physical` és estable, persistent i independent de `lightPollutionMode` i d'`atmosphereEnabled`. La UI pot etiquetar «Simulat» i «Real (físic)»; «real» significa model físic calculat, no meteorologia observada en directe. El valor inicial continua sent `simulated` fins a l'homologació i el mode simulat **no s'elimina** després.

## Responsabilitats

| Capa | Responsabilitat | Prohibició |
|---|---|---|
| `backend/domain/astronomy` | efemèrides, `SolarRadianceSource`, `LunarIrradianceProvider`, geometria de disc/fase | no coneix Three.js |
| `backend/domain/atmosphere` | `AtmosphericOpticsState`, `CloudOpticalState`, transport espectral de referència, `NaturalNightSkyModel`, `RadiativeErrorBudget` | no conté UI ni caches GPU |
| `backend/domain/photometry` | `SpectralBandSet`, integració CIE/SQM/TESS i transformacions amb unitats | no llegeix SkyView RGB com a espectre |
| `backend/application` | `PhysicalSkyCoordinator`, `SkyRevisionScheduler`, coalescing, revisió/invalidation | no duplica física |
| `backend/infrastructure` | datasets, manifests, ROLO, Copernicus, caches persistents i adapters de solver de referència | no fixa l'estat científic per si sola |
| `backend/scene` | snapshots/deltes neutrals, revisions, disponibilitat i identificadors de recursos | no inclou shaders |
| `frontend/contracts` / bridge | DTOs tipats, unitats, correlació i recovery | no envia espectres gegants per frame |
| `frontend/application` / UI | preferència de mode, qualitat i diagnòstic | no calcula SQM |
| `frontend/view/three` | `SkyRendererFacade` → `SimulatedSkyRenderer` / `PhysicalSkyRenderer`, LUTs, buffers, high-quality limb pass, lifecycle GPU | no és autoritat d'efemèrides ni sensors |

El camí actual `AtmosphereRenderer.ts`, `shaders/skyShader.ts` i `sky_palette.py` queda com a estratègia **simulated**. El físic entra darrere de la mateixa façana i del mateix `ThreeSceneHostImpl`; no es crea una segona escena, un segon bridge ni un segon rellotge.

## Dos integradors, una òptica compartida

1. **Cel astral:** Sol/Lluna com a fonts externes direccionals + Hillaire/LUT per runtime visual + ruta espectral científica separada.
2. **Skyglow artificial:** VIIRS + priors SPD + `PropagationKernel` + DEM + cúpules.
3. **Estat compartit:** pressió, temperatura, densitats, aerosols, ozó/gasos, `CloudOpticalState`, altitud, geodèsia, temps i procedència.
4. **Composició:** artificial + solar/twilight + lunar + `naturalMoonless` només en radiància lineal compatible i abans d'exposició/tone mapping.
5. **BortleEquivalent:** continua sent mètrica de lloc de referència sense Lluna ni crepuscle.

Compartir `AtmosphericOpticsState`, `CloudOpticalState` i `RadiativeErrorBudget` **no** autoritza a compartir els integradors o les caches radiatives.

## RGB visual i branca científica

La **SkyView LUT RGB lineal** és una textura de presentació. Hillaire utilitza tres components efectives en runtime; això no equival a una discretització espectral completa.

La branca científica conserva:
- `spectralBandCount` configurable;
- `spectralBandSetId`, límits nm, pesos i convenció d'integració;
- espectres/irradiàncies solar i lunar;
- radiància natural i artificial per banda;
- RSR/FOV/zero point de cada instrument.

No es reconstrueix espectre a partir de RGB. Canviar `spectralBandCount` invalida només recursos científics dependents; la dimensió de SkyView continua sent RGB.

## Scheduler i invalidació

`SkyRevisionScheduler` és **latest-wins**:
- una petició nova substitueix qualsevol petició pendent no iniciada;
- un resultat només es publica si `result.revision == currentRequestedRevision`;
- un resultat antic pot entrar en cache només si la seva clau física completa continua vàlida;
- no hi ha debounce perceptible;
- rellotge normal: actualització física objectiu 1 Hz;
- scrub: com a màxim una nova avaluació SkyView per frame presentat.

Regla d'invalidació inicial:

| Canvi | Transmittance / multiscattering | SkyView | branca espectral | skyglow artificial |
|---|---|---|---|---|
| +1 s amb òptica igual | reutilitzar | actualitzar si canvia geometria | fonts/geom. segons cadència | no per frame |
| scrub temporal | reutilitzar si òptica igual | sí | sí segons geometria | només si l'estat temporal ho exigeix |
| AOD/perfil/gasos/núvol | invalidar | invalidar | invalidar | invalidar dependències |
| altura/teleport | revisar clau | invalidar | invalidar geometria | revisar envelope/topologia |
| rotació de càmera | no | normalment no, es consulta altra direcció | no | no integral nova |
| `spectralBandCount` | no per la LUT RGB | no per dimensió | invalidar | invalidar vectorització espectral |

Si `physical` no està disponible, s'exposa la causa; només una acció explícita canvia a `simulated`.
