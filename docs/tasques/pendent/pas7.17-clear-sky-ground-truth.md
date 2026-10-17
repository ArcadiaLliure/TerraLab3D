# Pas 7.17 — Skyglow físic — Validació empírica clear-sky de SourceModel i transport

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Contrastar el sistema físic directe amb observacions externes abans de qualsevol acceleració espacial o cache.

## Dependències

7.16

## Referències obligatòries

- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

## Tasques

- [ ] Construir dataset de validació clear-sky TESS/SQM/all-sky amb metadata temporal/geogràfica i control de leakage.
- [ ] Separar mètriques de `SourceModel` de mètriques de transport; no usar runtime↔SG-REF com a prova empírica de F1.
- [ ] Aplicar leave-one-site-out o partició equivalent preregistrada.
- [ ] Simular exactament resposta/FOV dels sensors via 7.14.
- [ ] Publicar intervals, biaixos i casos fora de domini sense retocar V1 després de veure els resultats.

## Criteri de sortida

Existeix una validació empírica clear-sky reproduïble. Si el SourceModel no compleix el domini declarat, el pas falla i torna a 7.5; no es compensa amb calibratge del kernel.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.17/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Aquest pas valida el model contra el món real. Mantén separats error de font, atmosfera, transport i sensor.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
