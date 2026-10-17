# Pas 7.2 — Skyglow físic — Adaptador VNP46 d’observació, qualitat i procedència

> **Estat:** pendent. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Finalitat

Ingerir la font operativa exacta congelada a 7.1 sense confondre radiància observada amb emissió hemisfèrica.

## Dependències

7.1

## Referències obligatòries

- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)
- [10-datasets-llicencies.md](../../skyglow/10-datasets-llicencies.md)
- [09-incertesa-proveniencia.md](../../skyglow/09-incertesa-proveniencia.md)

## Tasques

- [ ] Implementar `Vnp46Observation` immutable amb producte, release, data, unitat, georeferència, quality/nodata i provenance.
- [ ] Aplicar exactament la política temporal i `LOW-RAD` del manifest v1; conservar valors negatius o dubtosos segons la política, mai amb `max(0,·)` implícit.
- [ ] Evitar doble correcció de stray light o altres correccions ja incorporades pel producte/release.
- [ ] Afegir fixtures reproduïbles de radiància alta, baixa, negativa, nodata, quality degradada i frontera temporal 2017.
- [ ] Separar descàrrega/cache de dades de la interpretació científica.

## Criteri de sortida

Un fixture VNP46 es pot llegir i serialitzar preservant unitats, quality, temps i provenance; cap transformació converteix encara l’observació en SPD o emissió angular.

## Evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.2/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.

## Instrucció per a Codex

La sortida és observació, no `SourceModel`. Qualsevol ambigüitat del producte torna a 7.1; no la resolguis localment.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.
