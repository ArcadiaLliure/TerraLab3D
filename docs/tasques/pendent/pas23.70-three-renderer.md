# Pas 23.70 — Skyglow físic — renderer Three.js lineal i doble buffer

> **Estat:** Pendent
> **Dependències:** Pas 23.69

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Visualitzar DomeProfile sense fer ciència al shader ni bloquejar el render thread.

## Descripció funcional

Substitució progressiva del glow Bortle com a autoritat visual.

## Abast

DTO TS, buffers/textures, shader, suma lineal i tone mapping posterior.

## Fora d'abast

Retirada legacy.

## Fitxers previsibles

frontend contracts/runtime/three/shaders/tests.

## Contractes

wire `DomeProfile` versionat.

## Implementació

Upload al buffer inactiu, swap atòmic i `dispose` correcte.

## Proves i comprovacions

Resultats tardans descartats, suma lineal, zero upload per frame.

## Benchmark / rendiment

GPU upload, frame p95/p99 i stutter.

## Criteris d'acceptació

- [ ] `renderThreadStutter=0` en els escenaris acordats.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

telemetria i captures debug. Les evidències noves s'han de desar sota `docs/evidencies/pas23.70/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Banding o precisió GPU.

## Rollback

Conservar últim buffer vàlid o legacy.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.