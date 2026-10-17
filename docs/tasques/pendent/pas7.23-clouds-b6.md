# Pas 7.23 — Skyglow físic — CloudOpticalState i núvols single-scattering B6

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Incorporar núvols com a estat òptic físic i no com un multiplicador arbitrari.

## Dependències

7.22

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Definir `CloudOpticalState` neutral compartible amb la vertical astral.
- [ ] Integrar núvol artificial single-scattering dins el kernel, sense implementar aquí Sol/Lluna.
- [ ] Validar límit clear, atenuació i possibles reforços físics sense constants de brillantor ad hoc.
- [ ] Comparar B6 contra SG-REF/oracle cloud dins el domini v1 i quantificar biaix fora de domini.
- [ ] Versionar dades, fase i propietats òptiques de núvol.

## Criteri de sortida

B6 és incremental, reproduïble i compleix el pressupost del domini cloud declarat; `CloudOpticalState` no conté lògica específica del skyglow.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.23/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No absorbeixis el biaix de multiple scattering en un factor empíric.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
