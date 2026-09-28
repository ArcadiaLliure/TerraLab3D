# Pas 23.59 — Skyglow físic — RadiancePatch, quadtree adaptatiu i amplada angular

> **Estat:** Pendent
> **Dependències:** Pas 23.58

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Representar internament cada regió amb error controlat i calcular `W_physical/W_effective`.

## Descripció funcional

Permet oclusió parcial i fonts extenses sense un patch per píxel.

## Abast

Quadtree que no creua regions, projecció topocèntrica, 95% candidat.

## Fora d'abast

Cache global.

## Fitxers previsibles

patch tree, geometry, tests.

## Contractes

`RadiancePatch`, width metrics.

## Implementació

Refinar per error en `I/r²×T×V`; circular statistics per azimut.

## Proves i comprovacions

Regió allargada, wrap 359°/1°, oclusió parcial, 95% outlier feble.

## Benchmark / rendiment

B5 preliminar `ε_patch` vs patches/error.

## Criteris d'acceptació

- [ ] Cap patch travessa `EmissionRegion` i l'error és mesurable.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

plots quadtree/width. Les evidències noves s'han de desar sota `docs/evidencies/pas23.59/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Explosió de patches propers.

## Rollback

Límit conservador + més refinament, mai fusió no controlada.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.