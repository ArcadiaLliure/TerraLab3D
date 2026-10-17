# Pas 7.62 — Pressupost d'error i descarte radiatiu conservador

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Fixar `RadiativeErrorBudget` com a única autoritat per pruning, contribucions negligibles i reutilització aproximada.

## Descripció funcional

Cap contribució s'elimina perquè «sembla petita». Cada descart requereix una cota superior conservadora per banda i un ledger acumulat projectable a radiància, color i instruments.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Fixar `RadiativeErrorBudget` com a única autoritat per pruning, contribucions negligibles i reutilització aproximada.

## Dependències

**Depèn de:**
- [Pas 7.61](pas7.61-natural-night-sky.md)
- [Pas 7.20 — Forward AD i RadiativeErrorBudget artificial](pas7.20-ad-error-budget.md)

**En depenen:**
- [Pas 7.63](pas7.63-clouds-horizon-terminator.md)

## Codi existent a reutilitzar

Contracte `RadiativeErrorBudget` introduït a 7.20, `SpectralBandSet`, respostes SQM/TESS/CIE i bounds del quadtree artificial.

## Flux tècnic

candidate contribution → `U_i,b` conservador → ledger `ΣU` → projeccions amb `|weights|` → prune/reuse o compute.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** falsos descartes per bounds optimistes, transformacions amb pesos negatius o núvols no acotades.
- **Rollback:** pruning OFF / invalidació total quan el bound no sigui demostrable.

## Tasques

- [ ] Formalitzar `0 <= L_i,b <= U_i,b` i `E_b,max = Σ U_i,b` per qualsevol conjunt descartat.
- [ ] Defaults configurables: 0,1 % màxim individual i 0,5 % acumulat; `radianceAbsoluteFloor` obligatori prop de zero.
- [ ] Projectar error a sensors/color amb suma de valors absoluts dels pesos/matrius; no usar `ΔE` com a criteri radiomètric.
- [ ] Per scheduler entre frames, histèresi inicial: entrar en skipped sota `0.8 × budget` i sortir en superar el budget complet; el ledger sempre preval.
- [ ] Bounds de quadtree/kernel: emissió màxima, `T<=1`, scattering/phase maxima, distància mínima, segment màxim i `Kmax` versionat.
- [ ] Núvols/aerosols desconeguts que poden augmentar radiància: usar envelope conservador o desactivar pruning.
- [ ] Si no es pot demostrar la cota, calcular la contribució completa.

## Criteri de sortida

No hi ha pruning o reuse aproximat sense bound traçable; la suma de cotes descartades respecta el pressupost radiomètric i instrumental configurat.

## Proves i evidències obligatòries

- [ ] casos adversos on cada factor del bound assoleix el seu màxim;
- [ ] projeccions SQM/TESS i XYZ→RGB amb pesos/matrius signats;
- [ ] error real de tots els descartes `<=` bound calculat;
- [ ] error acumulat per culling `<=0.5 %` amb defaults, incloent seqüències temporals i histèresi.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.62/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Usar llindars d'altura solar, luminància de pantalla o CIEDE2000 per apagar física.

## Instrucció per a Codex

bound conservador per banda + ledger acumulat → projecte a cada sortida activa → només llavors prune/reuse; si falta bound, compute. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
