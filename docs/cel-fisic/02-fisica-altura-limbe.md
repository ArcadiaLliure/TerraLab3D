# Física del Sol, la Lluna, l'altura i el limbe terrestre

## Fonts radiatives

**Sol:** reutilitzar efemèrides i distància Sol–Terra autoritatives; model d'irradiància espectral amb unitats, calibratge i procedència. Calcular disc directe, extinció, dispersió Rayleigh/Mie i absorció gasosa; evitar confondre intensitat visual amb radiància física. La geometria del disc i eclipsis és coherent amb el Pas 9.

**Lluna:** direcció, distància, fase, geometria Sol–Lluna–observador i irradiància espectral reflectida; el model de fase/oposició i albedo espectral ha de tenir procedència i drets verificats. Transportar la font lunar amb la mateixa òptica, sense tractar-la com un Sol de color blanc simplement atenuat. Separar disc lunar directe, dispersió lunar i il·luminació lunar de superfícies.

**Crepuscle i nit:** no introduir un llindar solar fix que talli la radiància; calcular dispersió quan el Sol és geomètricament sota l'horitzó local però il·lumina capes atmosfèriques altes. El fons sense Lluna (airglow, estrelles, zodiacal) és un component explícit amb estat **available/unavailable**, mai una constant opaca per calibrar el skyglow.

## Observador geodèsic i altura

- Convertir latitud, longitud i altura amb datum declarat (ellipsoidal WGS84 o ortomètrica + geoide). No confondre altura sobre el terreny, altura sobre el nivell del mar i radi des del centre de la Terra.
- L'altura modifica la longitud dels raigs atmosfèrics, densitat local, massa d'aire, extinció, dispersió, horitzó aparent, oclusió terrestre, exposició al Sol i aspecte del cel. Actualitzar la LUT segons posició/altura de càmera quan variïn les condicions geomètriques.
- Per una aproximació esfèrica de radi R i observador a r=R+h, la depressió geomètrica de l'horitzó és **acos(R/r)** per h≥0. L'el·lipsoide i el DEM són l'autoritat geodèsica; qualsevol radi equivalent utilitzat pel shader s'explicita i se n'acota l'error.
- Distingir els casos **dins l'atmosfera**, **al voltant del límit superior** i **fora de l'atmosfera**. No projectar un degradat de cel de superfície sobre una càmera orbital.
- Els raigs han d'intersectar correctament superfície/DEM, cos terrestre i capes atmosfèriques. Si un raig toca la Terra, no s'integra la radiància del cel darrere del planeta. La precisió de coordenades a gran altura exigeix origen local/rebasament i conversió ECEF→ENU coherent.

## Limbe terrestre il·luminat

Quan la càmera s'eleva prou per veure la curvatura, l'atmosfera al voltant del **limbe terrestre** pot presentar una franja/halo il·luminat pel Sol, amb color i gruix angular dependents de la geometria, altitud, òptica i direcció solar. També apareixen el terminador dia/nit i la regió d'ombra terrestre. **No dibuixar un cercle lluminós artificial.**

El resultat surt de:
1. intersecció del raig de vista amb l'embolcall atmosfèric i amb el planeta;
2. integració de radiància dispersada sobre el segment visible, incloent trajectes tangents llargs;
3. visibilitat del Sol a cada punt (oclusió per la Terra, eclipsis i geometria de disc quan calgui);
4. extinció punt→observador i múltiples dispersions segons l'aproximació declarada;
5. composició amb la superfície terrestre il·luminada, sense duplicar la llum difusa o el disc solar.

El halo pot ser asimètric: l'arc de costat diürn és diferent del nocturn. El comportament ha de ser continu quan la càmera travessa l'altura superior de l'atmosfera, gira cap al limbe o creua el terminador.

## Precisió i límits

Hillaire és una base de transport atmosfèric de temps real amb aproximacions RGB i LUT, no una garantia de precisió espectral. Documentar aproximacions (esfera local, dispersió múltiple, aerosols, núvols, fonts espectrals) i validar casos de solució coneguda i observació. No afirmar que el render RGB és una mesura SQM. El nombre de bandes científiques és configurable i no es tria mitjançant un benchmark de nombre de bandes.
