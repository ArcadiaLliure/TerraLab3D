# Pas 7.15 — Skyglow físic — Atmosfera real ERA5/CAMS i composició de camps

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Substituir el provider estàndard per dades reals sense canviar la física del kernel.

## Dependències

**Depèn de:**
7.14

**En depenen:**
- [Pas següent](pas7.16-uncertainty-provenance.md)

## Referències obligatòries

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)
- [10-datasets-llicencies.md](../../skyglow/10-datasets-llicencies.md)

## Tasques

- [ ] Implementar adapters ERA5/CAMS o fonts adoptades pel manifest amb cache/fixtures reproduïbles.
- [ ] Compondre P/T/RH, aerosols i gasos per variable amb validTime/leadTime/provenance individuals.
- [ ] Definir fallback per camp, mai un fallback global opac.
- [ ] Provar camps parcials, discontinuïtats temporals/espacials i mode offline de fixtures.
- [ ] Mesurar latència de provider fora del render thread.

## Criteri de sortida

El mateix kernel pot executar atmosfera estàndard o real amb contracte idèntic i provenance completa; fixtures reanàlisi són reproduïbles.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.15/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No facis que un detall ERA5/CAMS aparegui al kernel. El provider prepara `OpticalField`.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
