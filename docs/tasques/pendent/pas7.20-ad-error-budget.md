# Pas 7.20 — Skyglow físic — Forward AD i RadiativeErrorBudget

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Crear cotes conservadores per reutilització/pruning sense convertir l’AD en part de la física autoritativa.

## Dependències

7.19

## Referències obligatòries

- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Implementar forward AD en branques suaus i validar-lo amb diferències finites offline.
- [ ] Detectar discontinuïtats topològiques i invalidar derivades quan correspon.
- [ ] Implementar `RadiativeErrorBudget` per banda i ledger acumulat.
- [ ] Projectar cotes a SQM/TESS/CIE amb pesos absoluts.
- [ ] Executar B1b i mesurar overhead AD; si no hi ha cota conservadora, la política és no reutilitzar/no podar.
- [ ] Comprovar sensibilitats, reduccions numèriques i cotes quan LOS/fonts es distribueixen entre workers o executors vectoritzats; demostrar que la reorganització del càlcul no altera els guards topològics ni consumeix el pressupost d'error sense declarar-lo.

## Criteri de sortida

Existeix una cota d’error auditable per moviments/pertorbacions suaus i una regla explícita per discontinuïtats. El contracte és reutilitzable pel cel físic 7.62.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.20/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

Una derivada no autoritza reuse si la topologia pot canviar. En dubte, miss.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
