# Arquitectura del cel físic i commutació simulat/real

## Decisió

El selector de configuració **skyRenderingMode = simulated | physical** és estable i independent de **lightPollutionMode = automatic | bortle | magnitude** i d'**atmosphereEnabled**. La UI pot etiquetar els valors «Simulat» i «Real (físic)», però «real» significa model físic calculat, no observació meteorològica en directe. El valor inicial conserva **simulated** fins que la ruta física estigui homologada; no s'elimina el mode simulat en completar-la.

## Responsabilitats, segons docs/normes-arquitectura.md

| Capa existent | Responsabilitat | Prohibició |
|---|---|---|
| backend/domain/astronomy, sky_background i atmosphere | Efemèrides autoritatives, irradiància solar/lunar, geometria ECEF/geodèsica, òptica, coeficients espectrals, resultats físics i incertesa | No coneix Three.js, WebGL ni UI |
| backend/application | Selecció del mode, revisió temporal/observador, orquestració de serveis i ports, invalidació de resultats obsolets | No duplica models científics |
| backend/infrastructure | Datasets i LUT precalculades autoritzades, checksums, cache, workers i procedència | No fixa per si sola l'estat científic |
| backend/scene | Snapshot/deltes neutrals: mode, identificadors de recursos, vectors, altures, versions i estat de disponibilitat | No conté shaders ni fórmules físiques |
| frontend/contracts i bridge | DTOs tipats, correlació, unitats, versió, revisió, recuperació | No envia espectres gegants per fotograma |
| frontend/application i view/ui | Preferència de mode, indicador de disponibilitat i diagnòstic | No infereix SQM de colors |
| frontend/view/three | Estratègies de render **SimulatedSkyRenderer** i **PhysicalSkyRenderer**, SkyView LUT, buffers, uniforms, selecció, dispose i GPU | No és font autoritativa d'efemèrides, sensors ni atmosfera |

**Integració al codi real:** mantenir el camí de **AtmosphereRenderer.ts**, **shaders/skyShader.ts** i **sky_palette.py** com a estratègia simulada; crear una estratègia física separada darrere d'una façana/selector integrat a **ThreeSceneHostImpl** i al **RenderLoopImpl**. Reutilitzar el mateix horitzó/DEM, càmera, ordre de dibuix, estat solar/lunar, registre de recursos i política de color. No instanciar dues escenes o dos ponts.

## Dos integradors, una òptica compartida

1. **Cel astral:** radiació solar/lunar incident, transport atmosfèric de fonts direccionals llunyanes, transmittance/multiscattering/SkyView LUT, perspectiva aèria i llum de terreny. Referència algorísmica: Hillaire 2020, implementació MIT verificada.
2. **Skyglow artificial:** emissions terrestres distribuïdes VIIRS + priors SPD, PropagationKernel, DEM, cúpules i projeccions. Detall a [skyglow](../skyglow/README.md).
3. **Estat òptic compartit:** pressió, temperatura, densitats, aerosols, ozó/gasos, núvols quan suportats, altitud, data, geodèsia i procedència; cada integrador fa la seva pròpia transferència, amb versions compatibles.
4. **Composició:** radiància artificial + solar dispersada + lunar dispersada + fons natural nocturn, només si unitats, espectre, direcció i temps són compatibles; evitar doble comptar el disc directe, el crepuscle o el skyglow. El BortleEquivalent de lloc continua sense Lluna ni crepuscle.

## RGB visual i banda científica

La **SkyView LUT RGB lineal** és un format de presentació, no un oracle de fotometria. L'exemple Hillaire resol normalment tres components RGB efectives; aquesta aproximació no equival a una solució espectral completa. La branca científica conserva les distribucions espectrals solar/lunar i les bandes configurades quan es calculen luminància, SQM/TESS o altres sensors. No es reconstrueix un espectre únic a partir de RGB ni es fa servir la LUT RGB com a entrada científica d'instruments.

El nombre de bandes del càlcul espectral es configura per **spectralBandCount**, amb definició determinista de límits/ponderacions, identificador de band set i procedència. No hi ha nombre obligatori ni campanya de benchmarks per seleccionar-lo; les proves d'unitats, consistència i resultats físics de la configuració activa continuen sent necessàries. El nombre de canals de la LUT RGB és sempre tres.

## Actualització i errors

La UI i el render són **latest-wins**: quan canvien hora, Sol, Lluna, observador o mode, l'última revisió preval; les LUT dependents de direcció/altitud es recalculen a GPU quan correspon, i les que depenen només de l'atmosfera es reutilitzen mentre les seves claus siguin vàlides. Cap debounce perceptible a la timeline. La física del skyglow artificial no s'integra per fotograma.

Si **physical** no està disponible, exposar **unavailable** i la causa; només una acció explícita de l'usuari pot canviar a **simulated**. El canvi de mode és reversible, sense fugues de GPU ni canvis en resultats SQM/TESS. El render de la Terra/limbe és propietat de la ruta física, no del shader de gradient.
