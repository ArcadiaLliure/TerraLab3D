# Pas 7.14B — Qualificació instrumental SQM-L / TESS-W

> **Estat:** pendent, bloquejat per dades (`BLOCKED_NOMINAL_RESPONSE_OR_COVERAGE`). No bloqueja 7.15–7.28 **en el domini S/C i CIE/AB acreditat**. Cap implementació nova en aquesta revisió documental.

## Objectiu

Resoldre els requisits que no ha superat el [gate original 7.14](pas7.14-photometric-projections.md) sense falsificar-ne el PASS. Partir de [7.14A](../completat/pas7.14a-projeccions-cie-ab.md) i de [fonts, mancances i vies v3](../../evidencies/pas7.14/represa-v3/fonts-mancances-i-vies-v3.md).

## Requisits de dades i treball pendent

- [ ] Identificar una configuració concreta SQM-L o TESS-W amb resposta **conjunta** detector × filtre × òptica, convenció espectral aire/buit documentada, suport complet o cotes explícites de cues. No empalmar lots o models incompatibles.
- [ ] Caracteritzar el FOV i la sensibilitat angular de la configuració, incloses cues. Una gaussiana de prova no acredita un instrument real; un DomeProfile escalar CIE no acredita el camp angular **espectral** necessari.
- [ ] Distingir magnitud AB nominal de banda definida, magnitud nativa de dispositiu i observació. El calibratge individual no és un requisit general de la banda nominal, però fosc/guany/zero point sí poden ser-ho per a lectures natives.
- [ ] Obtenir dades del [registre concret v3](../../evidencies/pas7.14/represa-v3/perfils-candidats-i-mancances-v3.json), fixar model/versió/termes/llicència i preregistrar una nova campanya independent abans de comparar cap candidat.
- [ ] Revalidar cobertura espectral/angular, quadratures/FOV i el pressupost pertinent de **0,01 mag** amb oracles independents; si la cota científica no es pot demostrar, retornar `unavailable`.

## Criteri de sortida

Disposar d'un perfil nominal complet o amb contribucions absents **acotades per sota dels criteris preregistrats**, suport angular espectral compatible i evidències independents reproduïbles. No reinterpretar el gate original v1/v2/v3 ni publicar una predicció instrumental no acreditada.

## Dependència i ús posterior

7.15, 7.16, 7.17, 7.18–7.28 no exigeixen 7.14B per al seu domini S/C; però **cap lectura nativa SQM/TESS ni homologació empírica dependent del sensor** pot rebre `PASS` sense la qualificació requerida. 7.24 i 7.28 han d'auditar aquesta indisponibilitat. Represa instrumental només amb dades noves; represa general [7.15](pas7.15-atmos-era5-cams.md).
