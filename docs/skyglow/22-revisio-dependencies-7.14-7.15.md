# Revisió prospectiva de dependències: Pas 7.14 → 7.15

> **Data de decisió: 2026-10-22.** Revisió exclusivament documental; cap implementació, nova campanya, nou criteri de PASS/FAIL o requalificació retrospectiva.

## Motiu

Les tres iteracions de 7.14 van validar numèricament la projecció de radiància retinguda a CIE/AB de referència, inclosa la conversió aire/buit. El gate original continua `numericStatus=PASS`, `scientificExitPassed=false`, `BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE` perquè les respostes espectrals, cues i FOV SQM/TESS no estan prou acreditats. Aquest bloqueig instrumental **no és una dependència física necessària** per integrar dades meteorològiques a OpticalField i simular skyglow.

## Descomposició

| Subpas | Estat | Domini |
|---|---|---|
| [7.14 original](../tasques/pendent/pas7.14-photometric-projections.md) | **BLOCKED**, preservat històricament | Gate conjunt SQM/TESS/CIE, sense PASS nou |
| [7.14A](../tasques/completat/pas7.14a-projeccions-cie-ab.md) | **Completat per abast ja acreditat**, decisió prospectiva | CIE fotòpica, AB de referència, suports i geometries acreditats |
| [7.14B](../tasques/pendent/pas7.14b-perfils-instrumentals-sqm-tess.md) | **Pendent de dades instrumentals** | Model nominal SQM/TESS i eventual lectura nativa |
| [7.15](../tasques/pendent/pas7.15-atmos-era5-cams.md) | **Pendent, pròxim executable** | ERA5/CAMS i OpticalField sota contractes físics existents |

La seqüència executable S/C passa a ser **7.13, 7.14A, 7.15, 7.16, 7.17, 7.18…7.28**. 7.14B és una branca no bloquejant per a S/C, però obliga a informar `unavailable/not_evaluated` en projeccions SQM/TESS sense qualificació. No modificar les toleràncies de 0,01 mag, l'oracle de transport, la cua superior de 75 km ni les limitacions d'angulació/DEM. **Aquesta separació no és un nou PASS empíric.**

## Impacte posterior

7.16 manté absències d'incertesa instrumental, 7.17 només valida experimentalment H amb observacions independents i models de sensor qualificats; 7.24 i 7.28 revisen estats S/C/H **i SQM/TESS per separat**. Si un sensor és necessari per a una afirmació concreta, aquella afirmació continua bloquejada, encara que el motor S/C avanci. Els SLO/acceleracions 7.18–7.22 no canvien.

### Referència Falchi al 7.17

El possible GeoTIFF local de 2 GB **no està identificat ni inspeccionat**. Si correspon al [World Atlas 2016 de Falchi](10-datasets-llicencies.md#world-atlas-de-falchi--referència-històrica-opcional), permet una comparació històrica **entre models**, no un ground truth independent ni substitut del perfil instrumental. Les unitats, banda Johnson-Cousins V, data, atmosfera, terreny i llicència han de concordar o declarar-se com a diferències. GFZ v1.1 és CC BY-NC 4.0, sense autoritzar redistribució comercial.

## Política de preservació

Es canvien exclusivament documents vius; els fitxers de `docs/evidencies/`, preregistres, codi font i benchmarks històrics queden intactes. Codex reprendrà només **7.15**, amb criteris propis i sense començar 7.16.
