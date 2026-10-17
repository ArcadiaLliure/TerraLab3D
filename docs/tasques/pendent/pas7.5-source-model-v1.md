# Pas 7.5 — Skyglow físic — SourceModel v1: SPD, emissió angular i incertesa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Tancar `F1` i transformar observacions DNB en una distribució de font explícita, versionada i falsable.

## Dependències

7.4

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

## Tasques

- [ ] Definir `SourceModel` separant normalització DNB, pesos SPD, distribució angular i components d’incertesa.
- [ ] Adoptar un model angular publicat/empíric/ensemble amb domini declarat; Lambert no és fallback implícit.
- [ ] Documentar inputs auxiliars necessaris i comportament quan falten.
- [ ] Propagar la incertesa estructural de la inferència VNP46→font sense confondre-la amb error numèric.
- [ ] Validar fixtures sintètiques i, si existeixen, dades angulars externes independents; versionar `sourceModelId`.

## Criteri de sortida

`F1` queda resolta per al domini v1 o el pas queda `bloquejat`. Un `Vnp46Observation` pot produir un `SourceModel` complet amb provenance i incertesa declarada.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.5/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No permetis que un model angular provisional arribi a producció com si fos una mesura. Si no hi ha evidència suficient, atura la seqüència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
