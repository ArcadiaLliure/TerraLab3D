# Datasets, recursos i llicències

## Regla

Accés públic no equival automàticament a permís de redistribució. Cada recurs registra URL, propietari, versió, data d'accés, checksum, llicència/termes, redistribució, atribució, transformacions, volum, resolució, actualització i fallback.

## VIIRS VNL — Earth Observation Group

Font: https://eogdata.mines.edu/products/vnl/. Radiància `nW/cm²/sr`, 15 arcsec. VNL V2/V2.1/V2.2 segons any. El catàleg Earth Engine de V2.1/V2.2 declara dades de Colorado School of Mines en domini públic sense restriccions posteriors; cal conservar citació EOG. Política TerraLab3D: preferir origen EOG i registrar exactament la versió.

## NASA Black Marble VNP46

Font oficial: https://viirsland.gsfc.nasa.gov/Products/NASA/BlackMarble.html i DOI de producte LAADS. VNP46A1/A2/A3/A4 tenen semàntiques diferents. Cal revisar els termes del DAAC/producte concret abans d'empaquetar; preferència per descàrrega gestionada i cache local.

## NOAA-20 VIIRS DNB RSR

Font: https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php. Estat: accés públic verificat; redistribució del ZIP específic **PENDENT DE VERIFICACIÓ**. No versionar el ZIP original al repositori. Es pot versionar metadata/checksum i un script de descàrrega si els termes ho permeten.

## HITRAN

Font: https://www.hitran.org/. Versió actual: HITRAN2024. Ús previst: generació/validació offline de LUT, no runtime line-by-line. **PENDENT LEGAL:** revisar termes de dades HITRAN per redistribució de derivats/LUT abans de publicar-los; no assumir que l'article open access implica llicència de la base.

## SBDART/LOWTRAN

SBDART paper: DOI 10.1175/1520-0477(1998)079<2101:SARATS>2.0.CO;2. Repositori públic actual de SBDART declara GPL-3.0 per al codi. Si només s'usen resultats/idees i LUT pròpies, documentar transformació; si s'incorpora codi, revisar compatibilitat de llicència.

## ERA5

Font ECMWF/C3S. ERA5: reanàlisi horària global, ~31 km, 137 nivells fins ~80 km. Els termes Copernicus permeten ús, reproducció, distribució i adaptació amb atribució; els catàlegs moderns poden indicar CC BY 4.0 per datasets concrets. Registrar DOI/termes del dataset descarregat, no una llicència genèrica antiga.

## CAMS

Font ECMWF/CAMS: anàlisi/forecast de composició, aerosols i gasos. Llicència Copernicus: ús mundial, gratuït, reproducció/distribució/adaptació amb atribució. Registrar producte, lead time, resolució i data.

## DEM

Reutilitzar la política multiproveïdor de TerraLab3D/Pas 28. El kernel no pot assumir que tot DEM té la mateixa llicència. `TerrainRevision` ha d'incloure provider/product/version/checksum.

## TESS-W / SQM

Les dades de xarxes reals depenen del proveïdor. La resposta espectral/calibratge publicada a Bará et al. 2019 és CC BY 4.0. Les observacions individuals necessiten termes de la xarxa concreta i metadata d'instrument.

## SpectralBasisLibrary

Projecte de dades independent. No copiar SPD de fabricants sense termes. Preferir mesures/publicacions amb llicència clara o generar bases sintètiques físicament documentades. Cada SPD conserva font, aparell, resolució, normalització i drets.

## AerosolOpticsLibrary

Projecte independent. Candidats: taules Mie generades internament a partir d'índexs/size distributions amb llicència compatible, models SBDART/LOWTRAN com a referència i CAMS per composició/AOD. La font definitiva queda oberta.

## CloudOpticsLibrary

Projecte independent. Candidats: propietats Mie/ice tabulades d'una font oficial/peer-reviewed. No es congela fins que single-scattering B6 i la política de multiple scattering estiguin definides.

## UncertaintyModelRegistry

Derivat de documentació oficial de productes i validacions publicades. Cada registre és versionat i cita la font exacta; no es pot crear un sigma només a partir d'una etiqueta de qualitat.