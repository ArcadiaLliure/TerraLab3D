# Pas 7.16 — Skyglow físic — Incertesa quantitativa i provenance completa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Construir intervals i components d’error després que font, atmosfera i transport ja tinguin models concrets.

## Dependències

[Pas 7.15 — atmosfera real](pas7.15-atmos-era5-cams.md), [Pas 7.5 — inferència de font](pas7.5-source-model-v1.md) i [Pas 7.3 — model de mesura](../completat/pas7.3-dnb-rsr-measurement.md).

## Referències obligatòries

- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Implementar `UncertaintyModelRegistry` amb components numèrics, font, atmosfera, dades i estructurals.
- [ ] Representar explícitament `unavailable` en lloc d’inventar sigmes.
- [ ] Modelar correlacions quan siguin necessàries i separar biaix sistemàtic de variació temporal.
- [ ] Propagar incertesa a radiància i projeccions instrumentals.
- [ ] Separar incertesa RSR/mapping de guany, correccions L3 per producte, prior SPD/angular, radiometria, atmosfera, estructura i error numèric; registrar correlacions i domini plataforma/release/període. La manca de cota espectral bloqueja només la homologació que en depèn.
- [ ] Propagar explícitament la incertesa de la inferència L3→SPD i emissió angular del `SourceModel` de 7.5; distingir-la dels errors de l'operador TOA, de la correcció Black Marble documentada i del transport posterior.
- [ ] Produir un ledger de provenance/error per resultat.

## Criteri de sortida

Cada resultat físic pot explicar quines incerteses coneix, quines desconeix i com s’han propagat; no hi ha sigmes fictícies.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.16/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No amaguis una incertesa estructural dins el residual de validació.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
