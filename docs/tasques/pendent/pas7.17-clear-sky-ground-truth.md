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

**Gate S obligatori per autoritzar acceleracions:**

- [ ] Registrar abans de la comparació un pressupost d'error físic/numèric, mètriques, domini de fonts S, referència independent i criteris amb procedència.
- [ ] Comparar SG-REF/ruta directa contra casos analítics o altres oracles independents, sense reutilitzar la mateixa aproximació crítica.
- [ ] Verificar transport zenital/all-sky, projeccions i invariants per fonts S del domini aprovat, incloent casos adversos.
- [ ] Documentar PASS/FAIL S amb evidència reproduïble; una fallada obliga a reparar el model físic, mai a relaxar retrospectivament el pressupost.
- [ ] Permetre 7.18 únicament dins el domini S realment validat.

**Gate empíric C/H separat, no bloquejant si encara no és avaluable:**

- [ ] Preparar, si hi ha dades adequades, observacions externes TESS/SQM/all-sky i estratificació per plataforma/lloc/data; mantenir metadata i prevenir filtració de dades.
- [ ] Preregistrar criteris empírics, incertesa i partició `held-out` abans d'avaluar, amb leave-one-site-out o equivalent, sense reajustar al conjunt reservat.
- [ ] Contrastar explícitament la inferència L3→font/transport quan C sigui avaluable; si no, deixar `not_evaluated` documentat, **no** un PASS ni un obstacle al gate S.

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
