# Pas 23.67 — Skyglow físic — cache error-based i invalidació topològica

> **Estat:** Pendent
> **Dependències:** Pas 23.53, Pas 23.60 i Pas 23.66

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Implementar `PropagationCacheEntry` amb guardes topològiques i estimació contínua.

## Descripció funcional

Moviments petits poden reutilitzar resultats només si l'error de canvi és acotat.

## Abast

observerAnchor, envelope, tile deps, terrain/quadtree revisions, sensitivities.

## Fora d'abast

SLO final.

## Fitxers previsibles

cache application/infrastructure, tests.

## Contractes

`PropagationCacheEntry`, `CacheDecision`.

## Implementació

Ordre incondicional: oclusió, topologia, guardes, ΔB, budget.

## Proves i comprovacions

Occlusion flip sempre miss; tile unrelated no invalida; small smooth move pot hit.

## Benchmark / rendiment

cold/warm/small-motion/tile-change.

## Criteris d'acceptació

- [ ] Cap llindar geomètric substitueix el pressupost d'error.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

decision traces i matrix. Les evidències noves s'han de desar sota `docs/evidencies/pas23.67/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

False hit.

## Rollback

Invalidació més conservadora/total.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.