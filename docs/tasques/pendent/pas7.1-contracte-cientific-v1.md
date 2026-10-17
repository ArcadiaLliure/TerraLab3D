# Pas 7.1 — Skyglow físic — Contracte científic v1, dades i criteris d’acceptació

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Convertir les decisions que bloquegen la implementació en un perfil v1 explícit abans d’escriure física de producció.

## Dependències

7, 22.5, 23

## Referències obligatòries

- [18-decisions-obertes.md](../../skyglow/18-decisions-obertes.md)
- [10-datasets-llicencies.md](../../skyglow/10-datasets-llicencies.md)
- [07-benchmark-b0-b7.md](../../skyglow/07-benchmark-b0-b7.md)

## Tasques

- [ ] Fixar producte/release VNP46, política temporal, llicència, unitats i quality flags autoritatius (`DATA-VNP46`).
- [ ] Fixar política `LOW-RAD` i tractament versionat del canvi de baixa radiància de 2017 (`DNB-2017`), sense clipping silenciós.
- [ ] Preregistrar el perfil PASS/FAIL (`V1`) amb origen de cada llindar i declarar quines mètriques són científiques i quines de rendiment.
- [ ] Decidir `S1=SG-REF`: el skyglow tindrà oracle propi i no dependrà del Pas 7.65; decidir `F5` com a validació offline del biaix single-scattering dins SG-REF.
- [ ] Fixar `F7` com a radi adaptatiu per cota d’error; classificar `F6` com a no bloquejant per a la v1 si no s’exposa una magnitud perceptiva única.
- [ ] Crear un manifest versionat `skyglow-v1-profile` consumible per tests i passos posteriors.

## Criteri de sortida

No queda cap decisió necessària per implementar 7.2–7.4 sense propietari, origen i valor. Si manca evidència oficial per una decisió bloquejant, el pas queda `bloquejat`: Codex no pot inventar constants ni continuar.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.1/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

No implementis encara el kernel. Aquest pas és un gate de contracte: investiga, documenta, versiona i atura’t si una dada oficial imprescindible no es pot verificar.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
