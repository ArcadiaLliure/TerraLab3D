# Pas 7.3 — Skyglow físic — Model de mesura VIIRS DNB, RSR real i BAND_INTEGRATED

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Modelar què mesura DNB amb la RSR real i semàntica radiomètrica versionada.

## Dependències

7.2

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

## Tasques

- [ ] Implementar `ViirsDnbMeasurementModel` resolt per release i data d’adquisició.
- [ ] Carregar RSR tabulada real; prohibir aproximacions centre/FWHM/rectangle.
- [ ] Implementar `measurementOperatorId=BAND_INTEGRATED` amb cadena d’unitats explícita i tests contra integració espectral fina.
- [ ] Verificar la semàntica d’unitats a documentació oficial abans de codificar conversions.
- [ ] Crear fixtures de regressió per release/data i tests que detectin normalitzacions incorrectes de la RSR.

## Criteri de sortida

La mateixa SPD produeix una mesura DNB reproduïble i auditada contra una referència fina; la unitat i la RSR queden versionades i traçables.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.3/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No ajustis factors perquè una fixture “quadri”. Si la unitat oficial no es pot verificar, marca el pas `bloquejat`.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
