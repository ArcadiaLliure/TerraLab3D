# Pas 7.24 — Skyglow físic — Validació empírica final clear/cloudy i congelació de model

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Repetir la validació del sistema ja optimitzat i amb núvols abans d’integrar-lo al renderer.

## Dependències

7.23

## Referències obligatòries

- [08-validacio-cientifica.md](../../skyglow/08-validacio-cientifica.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

## Tasques

- [ ] Reexecutar clear-sky per demostrar que acceleracions 7.18–7.22 no han degradat la validesa.
- [ ] Afegir subset cloudy només dins el domini de 7.23 amb metadata suficient.
- [ ] Validar intervals d’incertesa, cobertura i biaixos per sensor/lloc/condició.
- [ ] Separar els resultats per plataforma Black Marble, producte, release i període; contrastar superposicions sense sumar radiàncies ni ampliar el domini d'una font amb dades d'una altra.
- [ ] Fer data-leakage checks i mantenir particions preregistrades.
- [ ] Congelar versions de producte, SourceModel, atmosfera, phase/backend i criteris que passin.

- [ ] Informar S (simulació física, gates propis), C (escenari condicionat) i H (validació empírica independent) per separat; sense H, cap «skyglow urbà absolut real» homologat.
- [ ] Si les dades C/H no permeten validació, registrar `not_evaluated`/`unavailable`; permetre la integració del motor S només amb etiqueta de simulació.
## Criteri de sortida

Existeix informe reproduïble dels gates físics S i, quan hi hagi dades, informes empírics C/H separats. Si C/H no es pot validar, roman explícitament no homologat mentre S pot continuar com a simulació. Els núvols només es qualifiquen al domini provat.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.24/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No ampliïs el domini per màrqueting. Homologa només el que les dades suporten.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
