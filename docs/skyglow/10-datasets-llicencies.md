# Datasets, recursos i llicències

## Regla

Accés públic no equival automàticament a permís de redistribució. Cada recurs registra URL, propietari, versió, data d'accés, checksum, llicència/termes, redistribució, atribució, transformacions, volum, resolució, actualització i fallback.

## NASA Black Marble multisatèl·lit — fonts candidates

**Decisió del Pas 7.1, conservada:** `VNP46A2.002` de LAADS, ArchiveSet 5200, capa diària `DNB_BRDF-Corrected_NTL` sense ompliment de buits. La [guia Collection 2](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf) i la [fitxa LAADS](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2) fonamenten unitats i QA; el [perfil v1](skyglow-v1-profile.json) i l'[auditoria](../evidencies/pas7.1/auditoria-fonts.md) en conserven l'abast verificat. El [perfil v2](skyglow-v2-profile.json) afegeix `VJ146A2.002`/NOAA-20 i `VJ246A2.002`/NOAA-21 com a candidates independents, sense declarar homologació operativa. La política PASS/FAIL `V1` continua preregistrada, amb valors als gates corresponents.

Cada recurs registra producte, release, data/període d'adquisició, checksum, unitat declarada, qualitat i transformacions. No s'assumeix que dues releases siguin equivalents a baixa radiància.

**Adquisició comuna:** el Pas 7.2 valida només VNP46 contra un grànul local real. L'ús ordinari de VNP46/VJ146/VJ246 ha de passar pel [Pas 24](../tasques/pendent/pas24-cataleg-recursos-descarregues.md): un provider/resolver LAADS/Earthdata resol `producte + collection + dia + tile/AOI` a un grànul immutable, el gestor autentica, descarrega, verifica i instal·la, i després lliura el path local a l'adaptador científic específic. No s'exposen tokens ni secrets en manifests, perfils, logs o provenance.

La integritat diferencia el **checksum de font** publicat/verificable pel proveïdor (`algorithm + value`) del **SHA-256 local** calculat per TerraLab3D sobre els bytes instal·lats. El segon serveix d'identitat interna reproduïble però no substitueix ni es presenta com una verificació externa del primer.

Correccions com stray light són **a confirmar segons producte/release**. Si el producte ja les aplica, TerraLab3D no les duplica.

La restricció de punt zero al voltant de 2017 documentada per Coesfeld et al. (2020, §2.3.1) obliga a tractar amb cautela sèries de baixa radiància que travessen aquesta data. El treball no estableix una correcció per a `VNP46A2.002`; no s'aplica cap constant universal. El rang vàlid publicat per a la capa és no negatiu: els valors negatius crus es conserven com a invàlids, sense clipping; zero i positius febles no es transformen en emissió inferida sense un model verificat.

## VIIRS DNB/VNL — referència i model de mesura

DNB SDR i VNL deixen de ser la font operativa primària de la v1, però continuen com a documentació, fixtures o contrast per interpretar mesura, calibratge i RSR. Cap producte es tracta automàticament com emissió hemisfèrica de superfície.

## NOAA-20 i NOAA-21 VIIRS DNB RSR

[NOAA-20](https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php) i [NOAA-21](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php): ZIP DAWG de prelanzament obtinguts i inspeccionats directament, amb LGS/MGS numèriques i README. [Matriu, hashes i límits](../evidencies/pas7.3/revisio-multisatel-lit.md). La redistribució dels ZIP específics és **pendent de verificar**; binaris a la biblioteca externa, al repositori només script i metadata. La recomanació NOAA-21 MGS→HGS no inclou cota d'incertesa ni acredita el vincle amb VJ246A2.002 L3. No es trasllada aquesta recomanació a NOAA-20 sense evidència.

### RSR no bloquejant i NOAA-20 com a primer candidat C

La [política S/C/H](20-politica-rsr-i-validacio-per-dominis.md) separa el motor físic independent de satèl·lit S de la inferència L3. Primer candidat experimental C: NOAA-20/VJ146A2.002, grànul urbà QA 0 real i RSR oficial de prelanzament, etiquetada diagnòstica. L'estabilitat espectral reportada no acredita resposta HGS/L3 efectiva de 2026, incertesa ni emissió angular. Conservar versió, gainStage, fingerprints, llicències i limitacions. NOAA-21 i Suomi-NPP continuen com a alternatives candidates/històriques.

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
## Llicències del cel solar/lunar (vertical 7.51+)

El codi de referència Hillaire té llicència MIT; Bruneton, BSD-3-Clause; Three.js, MIT. L'auditoria de codi, submòduls, models i dades de fonts solars/lunars és a [cel-fisic/03-llicencies.md](../cel-fisic/03-llicencies.md). La llicència MIT del repositori Hillaire no cobreix automàticament codi propietari d'Unreal Engine ni dades espectrals externes.
