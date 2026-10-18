# Pas 7.17 — Skyglow físic — Validació empírica clear-sky de SourceModel i transport

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Contrastar el sistema físic directe amb observacions externes abans de qualsevol acceleració espacial o cache.

## Dependències

[Pas 7.16 — incertesa i provenance](pas7.16-uncertainty-provenance.md), [Pas 7.5 — SourceModel](pas7.5-source-model-v1.md) i [Pas 7.3 — contracte de mesura TOA/L3](../completat/pas7.3-dnb-rsr-measurement.md).

## Referències obligatòries

- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

**Separació obligatòria:** (1) gate numèric/físic preacceleracions S amb fonts definides i oracle independent, criteris justificats/preregistrats, permet 7.18 només en S; (2) gate empíric observacional C/H amb ground truth extern i `held-out`, criteris i incerteses preregistrats. Si (2) no és avaluable, registrar `not_evaluated`, no PASS; no impedir la continuació de S. Un oracle numèric no és una observació empírica. [Política](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md).

## Tasques

- [ ] Construir dataset de validació clear-sky TESS/SQM/all-sky amb metadata temporal/geogràfica i control de leakage.
- [ ] Separar mètriques de `SourceModel` de mètriques de transport; no usar runtime↔SG-REF com a prova empírica de F1.
- [ ] Contrastar empíricament la inferència Black Marble L3→font del domini homologable, amb diagnòstic separat dels efectes de RSR, correcció L3, SPD i emissió angular; un QA 0 real per si sol no valida aquests efectes.
- [ ] Aplicar leave-one-site-out o partició equivalent preregistrada.
- [ ] Reservar el conjunt `held-out` i preregistrar mètriques, dominis i criteris empírics abans d'avaluar-lo, amb incerteses instrumental, de dades i del model; bloquejar 7.17 si no hi ha justificació.
- [ ] Estratificar validació per plataforma/producte/release i domini d'admissibilitat; registrar discrepàncies en dies/àrees solapats sense calibrar un SBAF amb el mateix conjunt reservat.
- [ ] Simular exactament resposta/FOV dels sensors via 7.14.
- [ ] Publicar intervals, biaixos i casos fora de domini sense retocar V1 després de veure els resultats.

## Criteri de sortida

El gate S contra oracle físic independent supera els criteris preregistrats i només habilita acceleracions S. Els criteris empírics C/H precedeixen l'avaluació `held-out` i no s'ajusten als residuals; absència de dades C/H implica `not_evaluated`, sense frenar acceleracions S ni declarar skyglow Black Marble homologat.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.17/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Aquest pas valida el model contra el món real. Mantén separats error de font, atmosfera, transport i sensor.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
