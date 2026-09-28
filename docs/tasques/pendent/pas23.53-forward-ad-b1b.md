# Pas 23.53 — Skyglow físic — forward AD geomètric i benchmark B1b

> **Estat:** Pendent
> **Dependències:** Pas 23.52

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Propagar `(B,dBx,dBy,dBz)` en la mateixa quadratura dins branques diferenciables.

## Descripció funcional

Mesura el cost real de sensibilitats geomètriques abans d'usar-les al cache.

## Abast

AD forward, terme de Leibniz, validació offline amb diferències finites.

## Fora d'abast

Cap diferenciació d'oclusió/quadtree.

## Fitxers previsibles

tipus dual/AD intern, tests, benchmark.

## Contractes

`PropagationSensitivities`.

## Implementació

Activació per opció; mateix node GK calcula valor i derivades.

## Proves i comprovacions

Comparació central finite-difference offline en casos suaus; invalidació de casos discontinus.

## Benchmark / rendiment

B1b vs B1a, `AD_overhead`.

## Criteris d'acceptació

- [ ] Derivades concorden amb referència i overhead queda mesurat.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

Taula d'errors i overhead. Les evidències noves s'han de desar sota `docs/evidencies/pas23.53/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Derivades incorrectes a `s_max`.

## Rollback

AD OFF sense canviar kernel base.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable de la seqüència skyglow o al pas global que correspongui.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.