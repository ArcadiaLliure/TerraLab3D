# Contractes, pressupostos, validació i SLO del cel físic

## Configuració

- **skyRenderingMode:** `simulated | physical`, persistent i independent de light pollution.
- **spectralBandCount:** enter positiu configurable; mai dimensió compilada fixa ni N seleccionat per benchmark.
- **spectralBandSetId:** intervals nm, ponderacions, convenció integrada/mostrejada, rang i revisió.
- **skyPhysicalAvailability:** `initializing | available | unavailable` + causa + versió.
- **observer:** lat/lon, datum, altitud geodèsica/ortomètrica, altura sobre DEM, ECEF/ENU i revisió.
- **atmosphericOpticsRevision / cloudOpticalRevision:** claus immutables de l'estat òptic.
- **solarRadianceSource / lunarRadianceSource:** espectre, disc, distància, fase, irradiància, qualitat i incertesa.
- **naturalNightSkyState:** airglow, zodiacal, integrated starlight i components opcionals, cadascun amb disponibilitat/procedència.
- **physicalSkyResource:** transmittance LUT, multiscattering LUT, SkyView RGB lineal i high-quality resources; dimensions/formats configurables.
- **skyRadianceComponents:** artificial, solar/twilight, lunar i naturalMoonless en radiància lineal compatible.

## Radiometria i projeccions

Distingir:
- radiància espectral `W·m⁻²·sr⁻¹·nm⁻¹`;
- radiància integrada per banda `W·m⁻²·sr⁻¹`;
- irradiància `W·m⁻²`;
- RGB lineal de presentació.

SQM/TESS/CIE utilitzen la seva RSR/FOV/zero point o pesos versionats. **Mai** s'inverteix la SkyView RGB per obtenir espectre.

Per una projecció lineal `q = Σ_b w_q,b L_b`, la cota d'error usa `Σ_b |w_q,b| E_b`; això també s'aplica a transformacions amb coeficients negatius, com una matriu XYZ→RGB. La decisió de pruning es pren abans de tone mapping.

## RadiativeErrorBudget

Per cada contribució `i` i banda `b` cal una cota demostrable:
`0 <= L_i,b <= U_i,b`.

Si es descarta un conjunt `D`:
`E_b,max = Σ_(i in D) U_i,b`.

Defaults inicials **configurables**:
- una contribució individual descartada: `<= 0.1 %` de la senyal de referència activa;
- suma de descartes numèrics: `<= 0.5 %`;
- projecció de sensor atribuïble al pruning: `<= 0.5 %` o tolerància instrumental més estricta;
- prop de zero: `radianceAbsoluteFloor` obligatori per evitar mètrica relativa singular.

Per treball repetitiu entre frames, histèresi de scheduler: entrar en estat skipped només si la cota queda per sota de `0.8 ×` el pressupost assignat; sortir-ne quan supera el pressupost complet. El ledger acumulat continua sent l'autoritat.

**Si no es pot demostrar una cota conservadora, no es poda.**

## Cotes conservadores

Els bounds poden utilitzar només factors que no subestimin:
- emissió/irradiància màxima del node o font;
- `T <= 1` quan ignorar extinció sigui conservador;
- màxim de coeficient de scattering per banda/segment;
- `phaseMax` de la funció de fase;
- distància mínima geomètrica i longitud de segment màxima;
- envelope de núvols/aerosols. Si les núvols poden augmentar la radiància i no hi ha envelope segur, pruning desactivat;
- `Kmax` versionat i validat per qualsevol aproximació de multiple scattering.

Ocultar terreny pot reduir radiància; **no** es pot usar una oclusió incerta per justificar un bound inferior.

## Validació científica

Oracles:
- Bruneton CPU/espectral: clear-sky, transmittance, scattering i colorimetria;
- path tracer Hillaire: geometria i multiple scattering;
- ROLO/USGS: irradiància lunar;
- GAMBONS i ESO/SkyCalc: referència externa de fons natural, sense vendoritzar codi incompatible;
- ecRad/discrete ordinates o equivalent: núvols;
- solucions analítiques: esfera, tangència, depressió d'horitzó i casos límit.

Gates inicials de **software**, no afirmacions d'exactitud del món real:
- transmittance clear-sky vs referència: p95 `<= 2 %`;
- radiància clear-sky fora de singularitats: p95 `<= 2 %`;
- error numèric/interpolació lunar vs ROLO: `<= 0.5 %` dins del seu domini;
- error acumulat introduït per culling: `<= 0.5 %`;
- error numèric SQM/TESS atribuïble al solver: `<= 1 %` o tolerància instrumental més estricta;
- cap discontinuïtat artificial en `simulated↔physical` ni en travessar top-of-atmosphere.

La incertesa de ROLO, aerosols, núvols, airglow o dades d'entrada es registra **separada** d'aquests errors d'implementació.

## Matriu mínima

- altura: 0 m, muntanya, 10 km, 30 km, top-of-atmosphere i òrbita;
- Sol: +90°, +30°, +5°, 0°, −6°, −12°, −18° i profundament ocult;
- vista: zenit, horitzó, solar, 90° solar, antisolar i limbe;
- aerosols: net, nominal i AOD alt;
- Lluna: plena/nova, 30°, 60°, 90°, >90°, perigeu/apogeu, eclipsi;
- núvols: clear, `τ≈0.1, 1, 5, 20`, líquid/gel quan hi hagi dades;
- fons natural: airglow baix/nominal/alt i geometries eclíptiques;
- timeline: 1 s/s, salts, scrub continu i temps invers.

No es fa un benchmark `N=3/6/8/12` per seleccionar bandes.

## SLO inicial `desktop-60`

Perfil de referència, **no promesa universal de hardware**:
- frame total: 16,67 ms;
- CPU d'actualització física de cel: `<=0.5 ms p95` excloent jobs offline;
- actualització SkyView GPU: `<=2 ms p95`;
- SkyView + composició durant scrub: `<=4 ms p99`;
- input timeline → cel corresponent: objectiu `<=1 frame`, `p95 <=2 frames`;
- cua efectiva de revisions: màxim 1 pendent;
- SkyView inicial: `192×108`, configurable;
- format preferit: `R11G11B10F` si és renderitzable; fallback `RGBA16F`;
- rellotge normal: 1 Hz; scrub: màxim 1 update per frame;
- LUT base de cel físic: objectiu <8 MiB, recursos de núvol separats.

El hardware de referència, driver, resolució i navegador/WebGL s'han de registrar abans d'homologar.

## Condició de sortida

El mode simulat conserva el comportament històric; el físic és calculat, traçable i legalment distribuïble; l'altura, limbe, fons natural, Lluna, núvols, pruning i scheduler tenen contractes verificats; les mètriques científiques no depenen de RGB; i els SLO s'han mesurat amb evidència.
