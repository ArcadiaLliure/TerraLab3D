# Fonts científiques i disponibilitat instrumental de 7.14

Consulta del 2026-10-19. Els [models numèrics arxivats](models-resposta-referencia.json) són referències identificades; no són perfils operatius de qualsevol SQM/TESS. Els [URL i hashes](fonts-manifest.json) permeten repetir-ne l’obtenció.

## CIE i unitats

La [CIE publica V(λ)](https://cie.co.at/datatable/cie-spectral-luminous-efficiency-photopic-vision) a pas d’1 nm, amb **longitud d’ona en aire estàndard**, CIE 018:2019, taula1, DOI10.25039/CIE.DS.dktna2s3. Es reutilitza el CSV empaquetat, amb metadades, llicència CC BY-SA4.0 i MD5 publicat `f389958555461a7d9a7562145e8ca9c0`; no es modifica.

La [definició SI de la candela del BIPM](https://www.bipm.org/en/si-base-units/candela) fixa 683 lm/W per a radiació monocromàtica de 540 THz. La projecció implementada és `Lv=683∫LλV(λ)dλ`, amb Lλ en W·m⁻²·sr⁻¹·nm⁻¹ i resultat en cd/m². La conversió explícita de nW·cm⁻² a W·m⁻² és10⁻⁵. Per a C el resultat conserva l’escala relativa i no rep unitats cd/m².

**Convenció espectral pendent de qualificació física:** el kernel heretat declara `vacuum_nm`, mentre que la CIE identifica la taula en aire. Els contrasts numèrics conserven les taules i la convenció de problema discret heretades de7.4/7.10; no converteixen silenciosament els espectres ni requalifiquen les evidències anteriors. La concordança amb un oracle sobre aquestes taules no demostra que la diferència aire/buit sigui inferior a0,01mag per a qualsevol SPD. Cal una convenció comuna versionada per a una homologació física instrumental completa.

## Magnituds AB i lectures natives

[Bará, Tapia i Zamorano2019](https://doi.org/10.3390/s19061336) formulen la radiància ponderada espectralment i mitjanada amb un FOV normalitzat en angle sòlid. Es fa servir aquesta separació i una referència AB explícita de3631Jy per arcsec². `1arcsec²=(π/648000)²sr`; amb λ en nm, la densitat espectral de referència és `3631·10⁻²⁶·c_nm/s /(Ω_arcsec²·λ²)`. La integral de cada tram lineal de resposta dividit per λ² es calcula analíticament i es contrasta amb Decimal50 independent.

Una magnitud AB d’una **banda de referència** no és una lectura nativa de l’aparell. El calibratge natiu requereix que resposta, freqüència fosca, guany/zero point i FOV pertanyin al mateix perfil. Els constants de les taules2019 de stars3/stars222 i SQM2370/2747 no s’apliquen a altres unitats. Cap offset s’ajusta al residual del kernel. Per a C es retorna senyal relatiu i, si les escales són compatibles, contrast entre escenaris; no una magnitud absoluta.

## SQM: dades disponibles i cua desconeguda

El [SVO Filter Profile Service](https://svo2.cab.inta-csic.es/svo/theory/fps/index.php?gname=Cameras&gname2=SQM&mode=browse) proporciona `Cameras/SQM.CM500`, digitalitzat de la figura8 de [Cinzano2005, publicat pel fabricant](https://unihedron.com/projects/darksky/sqmreport_v1p4.pdf). El VOTable identifica `DetectorType=0`, resposta d’energia: **no s’hi afegeix un factor λ de comptatge de fotons**.

La taula arxivada conté200nusos entre313,2i739,4nm, amb últim valor0,00124336, no zero. No defineix ni acota tota la cua vermella/infraroja d’un SQM. La banda truncada al suport conegut és un diagnòstic condicionat; la finestra nul·la utilitzada en aquest diagnòstic no afirma que la resposta física desconeguda sigui nul·la.

El FOV gaussià nominal20° de SQM-L prové de la descripció aproximada2019; no és una mesura angular de la mateixa unitat de2005. Aquestes fonts no es combinen com si fossin un calibratge complet i emparellat. `kind=SQM` continua `unavailable` amb motiu explícit.

## TESS-W: dades primàries i fosc no resolt

El [projecte TESS-W de GUAIX](https://guaix.fis.ucm.es/tess/node/2) identifica el dispositiu terrestre i la seva banda més estesa al vermell; no és el telescopi espacial TESS. S’han inspeccionat repositoris i mesures del laboratori. Les dades seleccionades són [stars1277 a licaplot](https://github.com/guaix-ucm/licaplot/tree/0f55129d6a27ccfe489558f1f46d441e278626f6/data/tessw), del2024-10-30, amb freqüències i corrent de fotodíode entre350i1045nm.

La forma de referència es deriva de `mediana(f)·R_PIN/|i_PIN|` i es normalitza al màxim, amb [responsivitat PIN10D de lica](https://github.com/guaix-ucm/lica/blob/a70ee75f24ef3c9766673a8dbb449147f90a1352/src/lica/lab/photodiode/PIN-10D-Responsivity-Cross-Calibrated%401nm.ecsv). És una resposta d’energia; no s’importa el codi del laboratori ni s’hi afegeix λ. La polaritat del corrent es tracta amb el valor absolut. No es resta una freqüència fosca inventada: el seu valor emparellat no està documentat en aquests fitxers, cosa que impedeix acreditar el model com a resposta completa.

El FOV gaussià17° és una prescripció nominal2019, no una mesura de stars1277. Tampoc hi ha cota de resposta fora del suport finit ni calibratge natiu conjunt. L’[informe LICA de2026 sobre lots de filtres](https://doi.org/10.5281/zenodo.22873442) reforça la necessitat d’identificar les òptiques de cada lot. `kind=TESS_W` continua `unavailable`; una banda AB condicionada no substitueix aquesta qualificació.

## Drets, traçabilitat i criteris

Les dades de licaplot i la seva derivació es distribueixen sota GPL3, amb llicència original adjunta. El calibratge PIN de lica té llicència MIT, també adjunta. El codi de projecció és propi; només reutilitza dades i formulacions matemàtiques publicades. Les mesures factuals SQM conserven atribució SVO/Cinzano i el VOTable original; no s’empaqueta el PDF. La [precisió administrativa de llicències](esmena-llicencia-abans-campanya.json) es va registrar abans de la campanya, sense canviar les dades numèriques.

Els [criteris de projecció](criteri-projeccions-preregistrat-v1.json) i el [criteri espectral](criteri-espectral-sensors-preregistrat-v1.json) es van registrar abans de comparar candidats. El pressupost numèric0,01mag és independent de la incertesa de resposta, fosc, calibratge, FOV, inferència C i convenció aire/buit. No es declara que aquestes incerteses desconegudes siguin zero ni que la concordança numèrica sigui exactitud observacional.
