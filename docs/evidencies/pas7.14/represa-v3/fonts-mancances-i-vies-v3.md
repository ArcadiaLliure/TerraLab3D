# Perfils nominals SQM-L/TESS-W: recerca delimitada i dades pendents

Consulta del **2026-10-21**, exclusivament per al Pas7.14. El [registre de recerca](registre-recerca-v3.json) distingeix les pistes noves de les fonts [ja examinades a v2](../represa-v2/fonts-i-qualificacio-v2.md). Els [hashes de consulta](fonts-noves-consultades-v3.json), la [disponibilitat d’annexos](annexos-i-disponibilitat-v3.json) i les [metadades arxivades](index-metadades-v3.json) permeten evitar cerques repetides. No s’ha demostrat que cap altra dada pública pugui existir: **no s’ha recuperat una resposta nominal completa qualificable entre les fonts consultades**. Els errors d’accés consten al registre; no s’han interpretat com absència de dades.

## SQM-L: òptica i fuites, no només detector per filtre

L’[informe específic de Cinzano2007](https://unihedron.com/projects/sqm-l/sqmreport2.pdf), pàgines1–3, mesura el FOV del SQM-L#1885 però remet a2005 per a l’espectre, sense tornar-lo a mesurar. Descriu aproximadament20° de FWHM, atenuació de5mag a40° i resposta de l’ordre de0,004 a60°. Són ancoratges de dues seccions, no una taula hemisfèrica ni una cota uniforme de totes les unitats.

La [publicació de2017](https://doi.org/10.1093/mnras/stx145), secció2 i figures3/4, compara components i sistema: troba una cua infraroja en SQM-LU/LE/DL atribuïda a una via òptica que no queda completament coberta pel filtre. Les figures s’han inspeccionat visualment; no s’han digitalitzat per atribuir-los precisió no publicada. El paquet de fonts [arXiv1701.05019](https://arxiv.org/src/1701.05019) conté figures/TeX i cap taula numèrica; [Zenodo2548628](https://zenodo.org/records/2548628) conté només el PDF. El suplement editorial anunciat enumera imatges de simulacions. Cap d’aquests arxius recuperats aporta la resposta conjunta tabulada i les metadades que falten.

El [document de Unihedron sobre lents](https://www.unihedron.com/projects/sqm-lu-dl-v/halfballcomparison.pdf), cinc pàgines, confirma dues configuracions: Golden Dragon/CM500 i semiesfera BK7/UVIR650, aquesta última introduïda a SQM-LU-DL-V i models ...2 per reduir fuites IR. No són intercanviables perquè comparteixin calibratge de lectura. Les figures preliminars en magnitud no donen resposta neta radiomètrica, llindar de detecció, incertesa o coordenada de λ; el fons dels gràfics tampoc és resposta espectral real demostrada. Aquesta comparació **no homologa SQM-L clàssic ni substitueix el model demanat per SQM-LE2**.

Per això no és suficient multiplicar TSL237 per CM500: cal també transmissió de la mateixa òptica i, si escau, la via no filtrada o una mesura conjunta. Una reconstrucció podria descriure la suma de trajectes filtrats/no filtrats, però aquí **no es coneix la fracció ni la seva dependència angular**. No se n’ha inventat cap coeficient ni empalmat una lent nova amb una mesura antiga. La [campanya SUPSI de2016](https://doi.org/10.1016/j.jqsrt.2016.03.015) és una via concreta: el resum editorial informa de16 instruments i resposta per damunt800nm. Només s’han recuperat resum/fragments; no es declara haver llegit les taules del text complet ni haver-ne comprovat la inexistència.

## FOV: les gaussianes de control no són un embolcall instrumental

L’[estudi de Padova2021](https://doi.org/10.3390/s21227544) examina SQM-LE5009/5143 i troba doble pic i FWHM aproximadament30°, en lloc de20°. La declaració de disponibilitat indica dades a petició de l’autor de correspondència; l’XML consultat no inclou annex numèric. És evidència de variació del disseny/alineació, no un perfil a traslladar automàticament a totes les SQM-L.

La gaussiana matemàtica de20° usada als controls té a40° un pes relatiu `exp(-4 ln(2)·(40/20)²)=1/65536`, és a dir12,041mag d’atenuació. No domina l’ancoratge aproximat de5mag publicat per al SQM-L#1885. Aquesta comparació algebraica **no integra el FOV d’un aparell**, però impedeix usar la gaussiana de control com una cota física conservadora de les seves cues.

Per a una regió absent, el pressupost heretat0,001mag exigeix `contribució_absent/senyal_conegut ≤ exp(0,001 ln(10)/2,5)−1 ≈ 0,000921458`. El senyal conegut usa la normalització del FOV **total**, sense renormalitzar el retall. Un FWHM, dos talls o un pes petit sense cota de radiància no demostren aquesta desigualtat.

La cambra de7.13 conté un camp **escalar CIE** per sobre0,5°, no espectres SQM/TESS de totes les direccions. El perfil COESA a azimut270,7°/elevacions45–60° és una línia, sense cobertura de FOV d’angle sòlid positiu. Les13 LOS espectrals de7.14 tampoc són una quadratura hemisfèrica. La integració directa seria vàlida amb un perfil seleccionat i una campanya preregistrada; executar-la ara no resoldria l’absència de resposta. Tampoc s’ha acreditat una cota física de contribució per a les regions que falten. Es mantenen `unavailable`, visibilitat/DEM i zeros físics, sense transparència o suavitzat.

## TESS-W: novetats verificades i què continua faltant

El [repositori primari licaplot](https://github.com/guaix-ucm/licaplot/tree/0f55129d6a27ccfe489558f1f46d441e278626f6) continua al mateix commit. S’han reutilitzat les dades v2, sense repetir descàrregues o el diagnòstic de passivitat: filtre350–1048nm, mesures conjuntes de les unitats2026 entre350–900nm i talls angulars d’altres unitats. No s’han empalmat amb stars1277 ni amb altres lots. L’[API del report2026](https://zenodo.org/api/records/22873442) encara enumera només el PDF; no aporta un annex nou. La data pública de la fitxa és2026-09-21; les dates històriques de consulta v2 es preserven.

Per a stars618 hi ha una via assequible: completar aquella mateixa configuració i el seu assaig conjunt, amb resposta de fons, finestra/col·lector, λ i límits UV/IR documentats. L’alternativa2019 necessita les taules de stars3 **o** stars222 i una definició del nominal que representen; no una mitjana o un empalmament improvisats. L’XML de l’[article2019](https://doi.org/10.3390/s19061336), reutilitzat sense baixar-lo de nou, no inclou `supplementary-material`; això no prova que els autors no disposin de dades. Les [bandes TESS-4C](https://zenodo.org/records/13992527) corresponen a un altre instrument i no completen automàticament TESS-W.

## Petició tècnica preparada, sense enviar

El [registre de candidats](perfils-candidats-i-mancances-v3.json) identifica els buits per configuració. Les vies següents eviten tornar a començar una cerca genèrica:

| Destinatari/via primària | Dada concreta que permet avançar |
|---|---|
| [Unihedron, contacte del fabricant](https://unihedron.com/) i SUPSI, autors de la comparació òptica | Taula conjunta d’energia i FOV del **SQM-L amb òptica identificada**; components/lents i camins de fuga coherents. Dades originals netes del fons dels gràfics de comparació, convenció de λ i cotes fora del mesurat. |
| LICA/GUAIX, Carlos E. Tapia (`ceta@ucm.es`) i Jaime Zamorano (`jzamorano@fis.ucm.es`), contactes publicats als articles/portal | Taules de figures1/2 del2019 amb identitat òptica, o assaig complet de **TESS-W stars618**; incertesa, fons i metadades de λ. Nominal de disseny/lot admissible, sense exigir calibratge de cada aparell de TerraLab3D. |
| Mirco Bartolomei (`mirco.bartolomei@unipd.it`), correspondència de2021 | Dades angulars originals i condicions del banc, possibilitat d’un nominal verificable i cotes de cues; no adoptar una unitat modificada amb baffle com si fos el disseny original. |

Format sol·licitat: CSV/ECSV amb λ i unitat/coordenada aire o buit; condicions de l’aire/calibratge si cal; resposta d’**energia** o definició explícita de QE; transmissió i identitat de cada element; configuració/lot del sistema; errors i límit de detecció, llum paràsita/fosc del **banc**; límits superiors fora de la banda; resposta angular normalitzable amb `dΩ`, cobertura i acoblament amb λ. La informació de fons de l’assaig serveix per extreure R(λ); no equival a exigir calibratge fosc individual de l’instrument que es vol predir.

Per a prediccions natives s’afegirien guany, fosc tèrmic i zero point del dispositiu i la seva convenció. Per a una **predicció nominal AB** n’hi ha prou amb un nominal verificable, la referència AB i cobertura justificada; no requereix aquells calibratges individuals. La lectura observada afegeix condicions, resposta real i incerteses experimentals. C conserva la seva escala condicionada i no produeix magnitud absoluta. No s’ha enviat cap missatge extern.

## Decisió i condició per reprendre

No adoptar perfils nous ni relaxar0,01mag. CIE450ppm/buit, retenció, referència AB, conversions i projecció continuen com a v2, sense reinterpretar evidències. La incertesa del nominal és diferent de la precisió numèrica; no s’exigeix exactitud observacional de0,01mag. El problema és que encara no es pot definir/acotar prou la integral nominal per aplicar-hi el pressupost vigent.

El gate continua **`BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE`**. Reprendre quan hi hagi una taula o cota nova identificada, o resposta del fabricant/laboratori, i llavors preregistrar perfil/domini/cobertura i estimació de cost abans de comparar. No repetir cerques tancades sense una pista nova; no iniciar7.15 ni acceleracions7.18–7.22.
