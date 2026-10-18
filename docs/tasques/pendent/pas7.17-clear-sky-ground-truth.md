# Pas 7.17 — Skyglow físic — Validació empírica clear-sky de SourceModel i transport

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Contrastar el sistema físic directe amb observacions externes abans de qualsevol acceleració espacial o cache.

## Dependències

[Pas 7.16 — incertesa i provenance](pas7.16-uncertainty-provenance.md), [Pas 7.5 — SourceModel](pas7.5-source-model-v1.md) i [Pas 7.3 — contracte de mesura TOA/L3](../completat/pas7.3-dnb-rsr-measurement.md).

## Referències obligatòries

- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

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

Els criteris empírics justificats precedeixen l'avaluació del conjunt reservat i no s'ajusten als residuals observats. Existeix una validació clear-sky reproduïble; si el SourceModel no compleix el domini declarat, el pas falla i torna a 7.5, sense calibratge compensatori del kernel.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.17/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Aquest pas valida el model contra el món real. Mantén separats error de font, atmosfera, transport i sensor.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
