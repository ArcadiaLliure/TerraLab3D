# Pas 23.74 — Skyglow físic — B7 FULL, SLO, migració i tancament documental

> **Estat:** Pendent
> **Dependències:** Passos 23.50–23.73

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Executar configuració candidata completa, fixar SLO basats en evidència i decidir shadow→default.

## Descripció funcional

Tanca la vertical sense declarar rendiment o precisió per intuïció.

## Abast

B7 AD OFF/ON, uncertainty OFF/ON, cache, renderer, ground truth i documentació.

## Fora d'abast

Multiple scattering general si encara no és requisit.

## Fitxers previsibles

benchmark reports, docs, README/MANUAL/inventari/evidències.

## Contractes

Congelar versions candidates aprovades.

## Implementació

Seleccionar paràmetres només a partir de frontera error↔cost i validació.

## Proves i comprovacions

Regressió completa, validate_docs, backend/frontend i escenaris manuals.

## Benchmark / rendiment

B7 FULL i SLO multidimensional.

## Criteris d'acceptació

- [ ] E_physical/L_p95/F_recompute/stutter tenen llindars documentats i complerts; cap pendent bloquejant ocult.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

Informe final, manifests, captures i raw results. Les evidències noves s'han de desar sota `docs/evidencies/pas23.74/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Cap configuració compleix tots els SLO.

## Rollback

Mantenir shadow/legacy i obrir pas de millora específic.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.