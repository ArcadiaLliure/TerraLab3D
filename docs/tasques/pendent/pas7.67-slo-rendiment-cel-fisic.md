# Pas 7.67 — SLO de rendiment, memòria i latència interactiva

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Mesurar i congelar un perfil inicial `desktop-60` sense alterar automàticament la configuració científica ni triar `spectralBandCount` per rendiment.

## Descripció funcional

La interactivitat de timeline és un requisit mesurable. Els SLO pertanyen a un perfil de hardware/browser declarat, no són una promesa universal.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Mesurar i congelar un perfil inicial `desktop-60` sense alterar automàticament la configuració científica ni triar `spectralBandCount` per rendiment.

## Dependències

**Depèn de:**
- [Pas 7.66](pas7.66-validacio-cel-fisic.md)

**En depenen:**
- [Pas 7.68](pas7.68-homologacio-cel-fisic.md)

## Codi existent a reutilitzar

RenderLoopImpl, GPU timers/telemetria, ResourceRegistry, diagnòstic de LUTs i scheduler 7.64.

## Flux tècnic

perfil hardware fixat → escenaris normal/scrub/limb-HQ/cloud → p50/p95/p99 CPU/GPU/memòria/input-to-visible → gate SLO.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** ocultar stutter amb debounce, degradar la ciència o publicar SLO sense hardware reproduïble.
- **Rollback:** perfil de qualitat explícit o `physical` no homologat en aquell hardware; mai canviar N silenciosament.

## Tasques

- [ ] Registrar CPU, GPU, driver, navegador/WebGL, resolució i configuració de qualitat del perfil `desktop-60`.
- [ ] SLO inicial: frame 16,67 ms; CPU update físic <=0.5 ms p95 excloent offline; SkyView GPU <=2 ms p95; SkyView+composició scrub <=4 ms p99.
- [ ] Input timeline→cel: objectiu <=1 frame i p95 <=2 frames; queue efectiva <=1.
- [ ] SkyView inicial 192×108 configurable; `R11G11B10F` preferit si suportat, `RGBA16F` fallback; LUT base objectiu <8 MiB.
- [ ] Rellotge normal 1 Hz i scrub màxim una actualització per frame; mesurar high-quality limb pass separat.
- [ ] Mesurar cold/warm, context restore, altura/teleport, nubes i canvis d'òptica.
- [ ] Reportar SLO **independentment** del valor de `spectralBandCount`; es pot declarar una configuració massa lenta, no substituir N automàticament.

## Criteri de sortida

Existeix un perfil `desktop-60` reproduïble amb p50/p95/p99, memòria i input-to-visible; qualsevol incompliment és explícit i no es tapa amb degradació científica silenciosa.

## Proves i evidències obligatòries

- [ ] 60 s de rellotge 1 s/s sense backlog;
- [ ] scrub intensiu amb revisió final correcta i p95 input-to-visible;
- [ ] limbe high-quality, context loss i teleport;
- [ ] comparació de formats/resolució angular sense tocar N espectral.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.67/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Garantir 60 FPS a qualsevol GPU o plataforma sense perfil declarat.

## Instrucció per a Codex

mesura sobre hardware fixat → p50/p95/p99 → gate `desktop-60`; no ajustar automàticament la física per passar-lo. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
