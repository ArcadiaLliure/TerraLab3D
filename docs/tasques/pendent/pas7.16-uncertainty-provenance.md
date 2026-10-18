# Pas 7.16 — Skyglow físic — Incertesa quantitativa i provenance completa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Construir intervals i components d’error després que font, atmosfera i transport ja tinguin models concrets.

## Dependències

[Pas 7.15 — atmosfera real](pas7.15-atmos-era5-cams.md), [Pas 7.5 — font física definida S](../completat/pas7.5-source-model-v1.md) i [Pas 7.3 — model de mesura](../completat/pas7.3-dnb-rsr-measurement.md). La inferència condicionada L3→font C comença aquí, no a 7.5.

## Referències obligatòries

- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

**Ampliació executiva del domini C:** estudiar VJ146A2.002/NOAA-20 amb RSR de prelanzament com a referència **condicionada**, priors SPD/angular, mapping de guany i relació TOA/L3 identificats com a verificats o desconeguts. Quantificar sensibilitat o retornar `absoluteCalibrationStatus=unavailable`, mai inferir flux hemisfèric únic. Construir independentment el ledger d'incertesa de S perquè l'absència d'H no freni el transport. [Política](../../skyglow/20-politica-rsr-i-validacio-per-dominis.md).

## Tasques

**Obligatòries per al criteri de sortida S:**

- [ ] Implementar `UncertaintyModelRegistry` i `Provenance` dels resultats físics S, separant error numèric, atmosfera, font i model estructural.
- [ ] Representar absència de sigma amb `unavailable`; mai derivar-lo d'una etiqueta de confiança ni usar un valor inventat.
- [ ] Propagar incerteses conegudes fins a radiància i projeccions de S; documentar correlacions quan siguin materials, biaixos i domini.
- [ ] Generar un ledger per resultat S, amb identitat d'inputs, revisions de model i hipòtesis.
- [ ] Demostrar amb tests que aquesta via no exigeix RSR, ni producte Black Marble, ni una inversió L3→emissió.

**Branca C/H addicional, no bloquejant de S:**

- [ ] Investigar la parella NOAA-20 VJ146A2.002 + RSR pública de referència, el mode nocturn, el mapping de guany i la semàntica TOA→L3; registrar precisament què no és verificable.
- [ ] Si hi ha evidència suficient, implementar escenaris condicionats amb priors SPD/angular, ensembles i anàlisi de sensibilitat, sense atribuir precisió absoluta fictícia.
- [ ] Si no n'hi ha, publicar l'estat C/H `unavailable` o `not_evaluated` amb causes; no falsificar PASS ni retocar la calibració S.

## Criteri de sortida

Cada resultat S identifica incertesa numèrica/física i les absències de dades; C té escenaris condicionats o estat `unavailable` sense sigmes ni amplituds fictícies; H exigeix evidència externa. La manca de RSR 2026 no impedeix acabar el ledger físic S.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.16/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No amaguis una incertesa estructural dins el residual de validació.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
