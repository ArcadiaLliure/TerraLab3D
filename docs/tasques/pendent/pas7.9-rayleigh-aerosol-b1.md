# Pas 7.9 — Skyglow físic — Rayleigh, aerosol de referència i benchmark B1

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Introduir la primera física de scattering sobre la ruta directa i auditable.

## Dependències

**Depèn de:**
7.8

**En depenen:**
- [Pas següent](pas7.10-gas-spectral-kernel.md)

## Referències obligatòries

- [01-especificacio-algorismes.md](../../skyglow/01-especificacio-algorismes.md)
- [04-justificacio-cientifica.md](../../skyglow/04-justificacio-cientifica.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Implementar Rayleigh normalitzat i una `PhaseFunction` comuna.
- [ ] Implementar HG només com a fallback i una fase de referència tabulada/alta resolució per tests.
- [ ] Calcular extinció, scattering source→P→observer i transmissió sense dobles factors geomètrics.
- [ ] Executar B1 en 1 banda amb fixtures analítiques i comparació diagnòstica reproduïble contra SG-REF, sense dictar encara PASS/FAIL numèric de transport.
- [ ] Verificar linealitat, positivitat, normalització 4π i casos isòtrops.

## Criteri de sortida

B1 supera invariants analítics de normalització, linealitat, positivitat i geometria, i documenta la discrepància contra SG-REF. El primer PASS/FAIL numèric runtime↔SG-REF és 7.12.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.9/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No comprimeixis encara la fase en Legendre. Primer demostra la física amb la representació de referència.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
