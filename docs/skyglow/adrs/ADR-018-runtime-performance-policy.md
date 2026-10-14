# ADR-018 — Runtime sense integral per frame i reutilització error-bounded

- **Estat:** Acceptada — implementació pendent
- **Data:** 2026-10-15
- **Àmbit:** skyglow físic / rendiment

## Context

TerraLab3D permet moviment continu. Reintegrar dispersió a cada frame faria el cost proporcional als FPS; una cache basada només en distància pot reutilitzar resultats invàlids.

## Decisió

El `PropagationKernel` s'executa per revisions científiques, mai per frame. El runtime aplica coalescing, cancel·lació cooperativa, cache amb versions/dependències/guardes topològiques i pressupost de `ΔB`, reutilització de treball estàtic, precàrrega predictiva opcional i latest-wins.

Cap optimització pot canviar silenciosament la física. Quadtree, bandes, PCHIP, LUT, cache i prefetch es trien sobre una frontera error↔cost contra reference solver.

## Conseqüències

Canvis petits poden ser barats; teleport o occlusion flip poden forçar recompute complet. El rendiment es mesura amb p50/p95/p99, TTFF, recomputeHz, memòria, queue/cancel/stale i stutter.

## Alternatives

Integral per frame, invalidació per distància fixa i prefetch sense guardes: descartats.

## Validació

Passos 23.67, 23.70 i 23.74; B7 cold/warm/small-motion/continuous-motion/prefetch/teleport/occlusion-flip.

## Estat d'implementació

No implementat per aquest ADR.
