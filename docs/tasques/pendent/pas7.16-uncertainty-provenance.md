# Pas 7.16 — Skyglow físic — Incertesa quantitativa i provenance completa

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Construir intervals i components d’error després que font, atmosfera i transport ja tinguin models concrets.

## Dependències

7.15

## Referències obligatòries

- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)
- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)

## Tasques

- [ ] Implementar `UncertaintyModelRegistry` amb components numèrics, font, atmosfera, dades i estructurals.
- [ ] Representar explícitament `unavailable` en lloc d’inventar sigmes.
- [ ] Modelar correlacions quan siguin necessàries i separar biaix sistemàtic de variació temporal.
- [ ] Propagar incertesa a radiància i projeccions instrumentals.
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
