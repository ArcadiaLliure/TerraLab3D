# Pla de migració des del skyglow actual

## Fase 0 — caracterització

Congelar snapshots del Pas 7 actual: Bortle 1/4/9, dia/nit, Via Làctia, estrelles, terreny. Objectiu: saber què canvia; no validar la física nova contra una heurística.

## Fase 1 — benchmark i infraestructura

B0, contractes, unitats, `PropagationKernel` mínim sense UI. Cap canvi visual.

## Fase 2 — kernel mínim shadow

B1, Rayleigh+HG, fonts sintètiques. Publicar resultats només a debug/telemetria.

## Fase 3 — VIIRS i espectre

Ingestió real, RSR, prior SPD, regions/patches. Comparar predicció zenital amb legacy i mesures, sense substituir encara.

## Fase 4 — terreny/cache/AD

Oclusió real, curvatura, cache error-based, moviment. Demostrar zero reutilització després d'un flip d'oclusió.

## Fase 5 — cúpules i renderer

`DomeProfile`, PCHIP, renderer lineal, doble buffer. Mode de selecció `legacy/physical/compare` només per desenvolupament.

## Fase 6 — atmosfera real

Atmosfera estàndard → ERA5/CAMS → providers observats/forecast. Procedència visible.

## Fase 7 — núvols

Single-scattering amb limitacions explícites; no activar per defecte fins validar.

## Fase 8 — B7 i ground truth

Benchmark full, validació geogràfica, SLO i uncertainty budget.

## Fase 9 — retirada legacy

Només després d'evidència: el mode físic esdevé automàtic per defecte. Bortle/magnitud manual romanen com a override/fallback si producte ho vol. El shader `u_artificialBrightness` deixa de ser autoritat i es pot eliminar quan cap ruta vigent el necessiti.

## Rollback

Cada fase manté un flag/configuració que permet tornar a l'últim camí homologat. No s'esborra el legacy fins a la fase 9. Els esquemes wire són versionats per permetre frontend/backend desalineats temporalment durant desenvolupament.