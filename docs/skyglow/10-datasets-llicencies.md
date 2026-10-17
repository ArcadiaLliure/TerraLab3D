# Datasets, recursos i llicències

## Regla

Accés públic no equival automàticament a permís de redistribució. Cada recurs registra URL, propietari, versió, data d'accés, checksum, llicència/termes, redistribució, atribució, transformacions, volum, resolució, actualització i fallback.

## NASA Black Marble VNP46 — font operativa

**Decisió del Pas 7.1:** `VNP46A2.002` de LAADS, processament estàndard (ArchiveSet 5200), capa diària `DNB_BRDF-Corrected_NTL` sense ompliment de buits. La [guia Collection 2](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf) i la [fitxa LAADS](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2) verifiquen unitat `nW cm⁻² sr⁻¹`, fill `-999.9` i QA 0–5. La [política LAADS](https://ladsweb.modaps.eosdis.nasa.gov/learn) permet ús i redistribució amb citació sol·licitada. Vegeu [perfil versionat](skyglow-v1-profile.json) i [auditoria](../evidencies/pas7.1/auditoria-fonts.md). La política PASS/FAIL `V1` és preregistrada; els valors resten assignats als seus gates.

Cada recurs registra producte, release, data/període d'adquisició, checksum, unitat declarada, qualitat i transformacions. No s'assumeix que dues releases siguin equivalents a baixa radiància.

**Adquisició VNP46:** el Pas 7.2 valida el lector contra un grànul local real, però no és propietari de la descàrrega. L'ús ordinari s'integra al gestor únic del [Pas 24](../tasques/pendent/pas24-cataleg-recursos-descarregues.md): un provider/resolver LAADS/Earthdata resol `producte + collection + data + tile/AOI` a un grànul immutable, el gestor autentica quan cal, descarrega, verifica i instal·la, i només llavors lliura el path local al lector VNP46. Cap token o secret pot aparèixer al catàleg, perfil científic, provenance, logs o repositori.

La integritat diferencia el **checksum de font** publicat/verificable pel proveïdor (`algorithm + value`) del **SHA-256 local** calculat per TerraLab3D sobre els bytes instal·lats. El segon serveix d'identitat interna reproduïble però no substitueix ni es presenta com una verificació externa del primer.

Correccions com stray light són **a confirmar segons producte/release**. Si el producte ja les aplica, TerraLab3D no les duplica.

La restricció de punt zero al voltant de 2017 documentada per Coesfeld et al. (2020, §2.3.1) obliga a tractar amb cautela sèries de baixa radiància que travessen aquesta data. El treball no estableix una correcció per a `VNP46A2.002`; no s'aplica cap constant universal. El rang vàlid publicat per a la capa és no negatiu: els valors negatius crus es conserven com a invàlids, sense clipping; zero i positius febles no es transformen en emissió inferida sense un model verificat.

## VIIRS DNB/VNL — referència i model de mesura

DNB SDR i VNL deixen de ser la font operativa primària de la v1, però continuen com a documentació, fixtures o contrast per interpretar mesura, calibratge i RSR. Cap producte es tracta automàticament com emissió hemisfèrica de superfície.

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
## Llicències del cel solar/lunar (vertical 7.51+)

El codi de referència Hillaire té llicència MIT; Bruneton, BSD-3-Clause; Three.js, MIT. L'auditoria de codi, submòduls, models i dades de fonts solars/lunars és a [cel-fisic/03-llicencies.md](../cel-fisic/03-llicencies.md). La llicència MIT del repositori Hillaire no cobreix automàticament codi propietari d'Unreal Engine ni dades espectrals externes.
