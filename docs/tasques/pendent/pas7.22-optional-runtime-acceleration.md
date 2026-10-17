# Pas 7.22 — Skyglow físic — Decisió i backend opcional LUT/precomputació/FFT

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Afegir una acceleració global només si la ruta directa+cache no compleix els SLO preregistrats.

## Dependències

7.21

## Referències obligatòries

- [02-arquitectura-integracio.md](../../skyglow/02-arquitectura-integracio.md)
- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Executar perfil de rendiment previ amb la ruta actual i comparar-lo amb els SLO de V1.
- [ ] Si els SLO ja es compleixen, tancar el pas com `no necessari` amb evidència i no afegir complexitat.
- [ ] Si no es compleixen, seleccionar LUT/precomputació/FFT només dins hipòtesis matemàtiques declarades.
- [ ] Comparar backend accelerat contra la ruta directa en error radiomètric/angular i casos límit.
- [ ] Definir fallback fora de domini i invalidació per versions.

## Criteri de sortida

O bé hi ha evidència que no cal backend addicional, o bé existeix un backend accelerat homologat contra la ruta directa amb domini/error/fallback explícits.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.22/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

FFT no és física nova. Si falla la invariància requerida, no la facis servir.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
