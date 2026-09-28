# Pas 23.73 — Skyglow físic — CloudOptics single-scattering i benchmark B6

> **Estat:** Pendent
> **Dependències:** Pas 23.65, Pas 23.61 i Pas 23.63

## Fonts a consultar

- `docs/skyglow/README.md` i documents especialitzats del dossier.
- `docs/normes-arquitectura.md`, `docs/inventari-funcional.md` i `AGENTS.md`.
- Fonts científiques exactes citades a `docs/skyglow/04-justificacio-cientifica.md`.

## Objectiu

Afegir núvols com a dispersors/absorbidors, no com a multiplicador arbitrari.

## Descripció funcional

Deriva `A_skyglow` com a diagnòstic cloudy/clear.

## Abast

Capes òpticament primes/moderades, `β_ext`, `ω0`, fase i procedència.

## Fora d'abast

Multiple scattering de núvol gruixut.

## Fitxers previsibles

cloud library/provider/kernel/tests.

## Contractes

`CloudLayer`, `CloudOptics`.

## Implementació

Source→cloud node→observer dins el mateix Γ.

## Proves i comprovacions

Clear limit, A pot ser <1 o >1, cap amplificació hardcoded.

## Benchmark / rendiment

B6 incremental.

## Criteris d'acceptació

- [ ] Limitació multiple-scattering visible en docs i debug.
- [ ] No marcar cap capacitat com a implementada només perquè existeixi el contracte o el document.
- [ ] Errors, cancel·lació, revisions obsoletes i recursos queden tractats segons `docs/normes-arquitectura.md`.

## Evidències

B6 plots i cloud manifest. Les evidències noves s'han de desar sota `docs/evidencies/pas23.73/` o la convenció equivalent validada pel repositori, sense esborrar evidència històrica.

## Riscos

Subestimació sota overcast.

## Rollback

Clouds OFF/clear-sky explícit.

## Impacte en inventari funcional

Mentre el pas sigui pendent, l'inventari només pot descriure'l com a planificat. En tancar-lo, classificar el resultat com `esquelet`, `parcial` o `observable` segons proves i ruta executable.

## Impacte en MANUAL / README / punt de represa

No actualitzar `docs/MANUAL.md` com si el comportament fos d'usuari fins que existeixi. En completar el pas: actualitzar `docs/README.md`, evidències i inventari; avançar el punt de represa al següent pas executable.

## Punt de represa

Si el pas queda incomplet, documentar l'última prova verda, fitxers tocats, evidència generada, bloqueig concret i primera acció següent.