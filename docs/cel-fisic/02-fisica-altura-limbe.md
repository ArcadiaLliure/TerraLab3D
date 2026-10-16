# Física del Sol, la Lluna, el fons nocturn, l'altura i el limbe terrestre

## Sol

Reutilitzar efemèrides i distància Sol–Terra autoritatives. `SolarRadianceSource` conserva irradiància espectral, geometria del disc, distància, unitats, revisió i incertesa. Disc directe, extinció, dispersió Rayleigh/Mie, absorció gasosa i eclipsis són components diferents; la intensitat visual no substitueix la radiometria.

No hi ha un llindar solar fix que apagui el crepuscle. A cada punt de ray march s'avaluen per separat:
1. visibilitat **Sol → mostra atmosfèrica**;
2. visibilitat **mostra → observador**.

Això permet que el Sol sota l'horitzó de l'observador continuï il·luminant capes altes.

## Lluna: decisió ROLO + reflectància separada

La Lluna no és el Sol multiplicat per un factor RGB.

Es separen dues responsabilitats:
- **`LunarIrradianceProvider`**: quantitat espectral integrada que arriba des del disc lunar.
- **`MoonSurfaceReflectanceModel`**: distribució espacial de brillantor sobre el disc visible.

**Model principal:** ROLO/USGS per irradiància integrada en disc dins del domini observacional cobert aproximadament fins a `|phaseAngle| <= 90°`, amb geometria de fase, libració i distàncies. La implementació ha de conservar la incertesa del model i no confondre error d'interpolació amb exactitud física absoluta.

**Fora del domini ROLO:** extensió de reflectància basada en Hapke, amb Lommel-Seeliger com a fallback mínim, calibrada per continuïtat a la frontera i marcada `quality=extrapolated`. Una fase >90° no pot presentar la mateixa confiança que el domini calibrat.

`LunarRadianceSource` inclou com a mínim direcció, radi angular, `spectralIrradiance[N]`, distància, angle de fase, incertesa, `quality` i revisió. Hillaire consumeix la font; **no** implementa ROLO/Hapke.

Separar disc lunar directe, dispersió lunar atmosfèrica i irradiància lunar sobre terreny.

## Fons natural sense Lluna

`NaturalNightSkyModel` és independent del skyglow artificial i de la Lluna:

`L_natural = L_airglow + L_zodiacal + L_integratedStarlight + L_optionalExtragalactic`.

- **Airglow:** model paramètric propi, espectral i versionat; dependències mínimes de zenit/airmass, temps i proxy d'activitat solar quan sigui disponible. Cap constant opaca de “night floor” pot ser resultat científic.
- **Llum zodiacal:** geometria eclíptica + espectre solar reflectit, amb coeficients/dataset de llicència auditada.
- **Integrated starlight:** mapa/angularització precomputada a partir d'un catàleg autoritzat; excloure exactament les estrelles que el renderer resol individualment.
- **Via Làctia difusa:** continua sota el Pas 10 i es compon una sola vegada.
- **Fons extragalàctic:** port opcional, explícit i traçable.

GAMBONS i ESO/SkyCalc són referències de validació, no dependències runtime ni datasets vendorizats automàticament.

## Observador geodèsic i altura

- Declarar WGS84/geoide i distingir altitud ellipsoïdal, ortomètrica i altura sobre DEM.
- L'altura modifica camí atmosfèric, densitat local, massa d'aire, extinció, dispersió, depressió d'horitzó, oclusió terrestre, visibilitat del Sol i aspecte del cel.
- En esfera de referència, per `r=R+h`, la depressió geomètrica és `acos(R/r)`; l'el·lipsoide/DEM prevalen i qualsevol radi equivalent del shader queda documentat.
- Distingir interior, top-of-atmosphere i exterior de l'atmosfera.
- Usar ECEF/ENU i origen local/rebasament per mantenir precisió a escala orbital.

## Limbe terrestre, terminador i qualitat angular

El halo del limbe és conseqüència del transport, **mai un anell decoratiu**:
1. intersecció vista–atmosfera–Terra/DEM;
2. segment visible i trajectes tangents;
3. visibilitat solar a cada mostra;
4. extinció mostra→observador i scattering;
5. composició amb superfície terrestre sense doble comptatge.

L'arc diürn, terminador i costat nocturn són asimètrics. El resultat ha de ser continu en travessar top-of-atmosphere.

La SkyView base parteix d'un perfil angular configurable; **192×108 és només un perfil inicial de runtime**, no una constant científica. Zones d'alt gradient (limbe, terminador, proximitat solar) poden activar resolució superior o ray march per píxel/high-quality pass si la LUT base no compleix el gate visual/radiomètric corresponent.

## Núvols

`CloudOpticalState` és neutral respecte de l'integrador i conté per banda, com a mínim:
`tau`, `singleScatteringAlbedo (ω0)`, `asymmetryG`, `cloudFraction`, `baseAltitude`, `topAltitude`, revisió i procedència.

- `7.27` calcula l'efecte sobre skyglow artificial.
- `7.63` calcula l'efecte sobre Sol/Lluna/fons natural.
- Baseline astral: Beer-Lambert + fase direccional i compensació de multiple scattering amb delta-Eddington.
- Clear-sky és un estat científic vàlid.
- Una textura alpha artística no és `physical`.

## Precisió i límits

Hillaire és runtime físic aproximat, no oracle espectral. Bruneton espectral/CPU i el path tracer de Hillaire són oracles de desenvolupament. ROLO, referències de fons natural i solvers de núvols aporten validació específica. Les toleràncies de software i la incertesa dels models es registren per separat.
