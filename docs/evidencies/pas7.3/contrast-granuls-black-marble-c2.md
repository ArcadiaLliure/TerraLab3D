# Contrast de la guia Black Marble C2 i de dos grànuls VJ146A2 reals — Pas 7.3

Data de comprovació: 2026-10-18. [Script d'inspecció reproduïble](../../../tools/inspect_black_marble_a2.py). Els HDF5 i el PDF oficial són a `I:/TerraLab/data/earth/light-pollution/`, fora del repositori; els SHA-256 següents identifiquen els bytes locals i no són checksums publicats per NASA.

## Tres contractes diferents

| Contracte | Evidència directa i abast verificat | Límit i pas propietari |
|---|---|---|
| SPD/radiància espectral TOA → DNB | L'[ATBD de calibratge VIIRS SDR](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf) defineix la resposta instrumental energètica. L'[operador](../../../backend/src/terralab3d/domain/light_pollution/dnb_measurement.py) integra `Lλ·R(λ)` en `nm` i retorna `BAND_INTEGRATED` en `nW cm^-2 sr^-1`, amb RSR, guany, plataforma, producte, release, dia i procedència explícits. | Les taules NOAA de prelanzament i SNPP LGS 2013 continuen **diagnòstiques** per als productes L3 del 2026. La manca d'una RSR aplicable es comunica per sensor/període; no es substitueix ni es força una equivalència. La sensibilitat espectral del conjunt de bandes és 7.4; l'admissibilitat física de cada font és 7.5. |
| DNB TOA → Black Marble L3 corregit | La [User Guide C2, §2.2, equació (1)](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) escriu explícitament la recuperació de la radiància nocturna ascendent de superfície `L_NTL` a partir de `L_DNB` TOA. En notació compacta: `L_NTL = {[(L_DNB−L_path)/T_up]·(1−a·ρ_a) − L_m·T_down}/P_up`. Els termes inclouen radiància de trajecte, transmissió atmosfèrica, albedo/retrodispersió, Lluna i escapament pel dosser. La secció 5.2 i la taula 8 assignen a `DNB_BRDF-Corrected_NTL` de **VNP46A2/VJ146A2** radiància corregida `nW cm^-2 sr^-1`, `float32`, fill `-999.9`, rang `≥0`, escala 1 i offset 0. | La guia descriu el model de correcció, però els camps L3 no contenen tots els termes auxiliars per reconstruir cada píxel TOA→L3; aquí no s'afirma una inversió numèrica per grànul ni equivalència TOA=L3. El [DTO VNP46](../../../backend/src/terralab3d/domain/light_pollution/vnp46.py) etiqueta l'etapa L3 i preserva el valor cru. |
| Black Marble L3 → SPD i emissió angular física | La banda DNB pancromàtica i les correccions de NASA **no** determinen una SPD única, emissió hemisfèrica ni llei angular urbana. | `SourceModel` i admissibilitat per sensor a [7.5](../../tasques/pendent/pas7.5-source-model-v1.md); propagació de la incertesa estructural, RSR i L3 a [7.16](../../tasques/pendent/pas7.16-uncertainty-provenance.md); contrast extern clear-sky a [7.17](../../tasques/pendent/pas7.17-clear-sky-ground-truth.md). |

El PDF oficial obtingut a `references/BlackMarbleUserGuide_Collection2.0.pdf` té SHA-256 `3bd88ecfb70594286d0613dc3cf180260f0d614150d6f74f00d1ba6650fa4da9`. L'equació s'ha llegit a la pàgina impresa 3 i s'ha contrastat visualment en la pàgina 9 del PDF. **Inferència delimitada:** la interpretació d'etapa física del DTO deriva de la guia i del nom/atributs de la capa; no és un atribut HDF anomenat `physicalStage`.

## Grànuls i procedència

| Producte, dia i tile | SHA-256 local; mida | Metadades verificades |
|---|---|---|
| `VJ146A2.A2026256.h00v01.002.2026264103507.h5` | `c12dec50398abc31feb503a92a9d3f4808220efafb356dab8615381a2a68e6ea`; 5.094.809 bytes | `ShortName=VJ146A2`, `PlatformShortName=JPSS-1`, `SatelliteInstrument=JP1VIIRS`, DOI `10.5067/VIIRS/VJ146A2.002`, `PGEVersion=2.0.5`, `PGENumber=555`, `AlgorithmVersion=NPP_PR46A2 1.0.3`, `ProcessingCenter=LandSIPS`, dia 2026-09-13. |
| `VJ146A2.A2026256.h18v04.002.2026264085938.h5` | `2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762`; 27.876.020 bytes | La mateixa identitat/producte/PGE i dia; `ProductionTime=2026-09-21 08:59:38.000`. [Índex oficial LAADS 2026/256](https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/5200/VJ146A2/2026/256/) i [fitxa del producte](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ146A2). |

Els dos fitxers s'han traslladat de `C:/Users/Manel/Downloads` a `I:/TerraLab/data/earth/light-pollution/vj146a2/2026/256/`; el SHA-256 s'ha comprovat abans i després del trasllat. `InputPointer` inclou, respectivament, `VJ146A1.A2026256.h00v01.002.2026258024246.h5` i `VJ146A1.A2026256.h18v04.002.2026258024722.h5`, a més de productes atmosfèrics, terreny i auxiliars. Això acredita el **llinatge declarat del grànul**, no la RSR numèrica emprada pel processament. El literal `NPP` d'`AlgorithmVersion` no canvia la plataforma explícita `JPSS-1`.

Tots dos HDF5 tenen nou datasets sota `HDFEOS/GRIDS/VIIRS_Grid_DNB_2d/Data Fields`, com el VNP46 real de 7.2: radiància primària i gap-filled, radiància lunar, QA, màscara de núvol, neu, darrera recuperació d'alta qualitat, `lat` i `lon`. La radiància primària és `float32` de 2400×2400, `nWatts/(cm^2 sr)`, `valid_range=>=0.0`, `_FillValue=-999.9`, escala 1 i offset 0. El QA és `uint8`, fill 255 i `valid_range=0 - 5`. La [User Guide C2, taules 8–9](https://viirsland.gsfc.nasa.gov/PDF/BlackMarbleUserGuide_Collection2.0.pdf) i els atributs dels grànuls coincideixen en 0–5; el `valid_range` 0–3 de la [file spec VJ146](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VJ146A2_v2.0) és inconsistent amb la seva pròpia descripció i amb els bytes reals. QA 0 significa recuperació d'alta qualitat de l'algorisme principal, no homologació espectral.

## Qualitat i mostres reals

| Tile | Recompte `Mandatory_Quality_Flag` | Conclusió |
|---|---|---|
| h00v01 | 2: 51.903; 4: 47.619; 5: 212; 255: 5.660.266 | Cap QA 0; no es fa passar aquest tile d'alta latitud per mostra urbana bona. |
| h18v04 | 0: 4.761.693; 1: 28.008; 2: 17; 5: 3.395; 255: 966.887 | Cobertura terrestre amb QA 0 real. Els recomptes sumen 5.760.000 píxels. |

Mostres QA 0 de la capa **sense gap-fill**, escollides com el píxel de la graella més proper a coordenades urbanes de referència; les coordenades no acrediten per si soles l'origen físic de cada fotó:

| Àrea | Fila, columna | Latitud, longitud del píxel | Radiància crua `nW cm^-2 sr^-1` | `QF_Cloud_Mask`; neu |
|---|---:|---:|---:|---:|
| París | 274, 565 | 48.8583333, 2.3541667 | 53.67601013183594 | 50; 0 |
| Barcelona | 2067, 520 | 41.3875, 2.1666667 | 139.34158325195312 | 34; 0 |
| Lió | 1017, 1161 | 45.7625, 4.8375 | 103.10929107666016 | 42; 0 |
| Marsella | 1609, 1289 | 43.2958333, 5.3708333 | 91.98152923583984 | 42; 0 |

La mostra fill `(0,0)` d'h18v04 té QA 255 i radiància `-999.9000244140625` en `float32`; no s'ha retallat a zero. La comparació amb el [grànul VNP46 real de 7.2](../pas7.2/validacio-adaptador.md) confirma igualtat estructural de capes, però identitat de producte, DOI i plataforma diferents. L'`Vnp46GranuleAdapter` rebutja el VJ146 real amb `Vnp46QuarantineError: Producte o col·lecció incompatibles al nom del grànul`; no se li amplia silenciosament el domini. La lectura J1 d'aquest pas és offline amb `h5py`, no una via d'ingesta de producte: aquesta s'integra al gestor comú del Pas 24.

## Reproducció i límits

```powershell
python -X utf8 tools/inspect_black_marble_a2.py 'I:\TerraLab\data\earth\light-pollution\vj146a2\2026\256\VJ146A2.A2026256.h18v04.002.2026264085938.h5' --expected-product VJ146A2 --expected-sha256 2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762
```

L'script verifica SHA, identitat, capes, atributs i recomptes QA i emet una mostra per cada codi present. L'extracció dels píxels urbans s'ha fet amb `h5py` escollint els índexs més propers a les coordenades indicades. No s'ha trobat cap taula RSR nocturna efectiva de 2026 vinculada directament a VNP46A2.002 o VJ146A2.002. Tampoc s'ha estimat una incertesa per a la inferència L3→SPD/emissió angular. Aquestes absències impedeixen **homologar una font física**, però no contradiuen la validesa del contracte matemàtic i d'interpretació de 7.3.
