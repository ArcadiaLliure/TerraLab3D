# Pla de migració des del skyglow actual

## Fase 0 — caracterització

Congelar snapshots del Pas 7 actual: Bortle 1/4/9, dia/nit, Via Làctia, estrelles, terreny. Objectiu: saber què canvia; no validar la física nova contra una heurística.

## Fase 1 — benchmark i infraestructura

B0, contractes, unitats, `PropagationKernel` mínim sense UI. La ruta directa defineix la semàntica que qualsevol LUT/FFT futura haurà de reproduir. Cap canvi visual.

## Fase 2 — kernel mínim shadow

B1, Rayleigh+HG, fonts sintètiques. Publicar resultats només a debug/telemetria.

## Fase 3 — VNP46, model DNB, SourceModel i gate zenital

Ingestió VNP46 real amb producte/release/data, RSR DNB resolta temporalment, operador `BAND_INTEGRATED`, prior SPD i model angular explícit. Preservar baixa radiància sense clipping i registrar la restricció pre/post-2017.

Tancar la cadena de propagació a 90° amb el mateix kernel i l'oracle que resulti de S1. El gate valida transport donat el model de font; la validació empírica de l'emissió continua separada. No es promouen cúpules si el gate no passa.

## Fase 4 — terreny/cache/AD i moviment

Oclusió real, curvatura, cache error-based, moviment. Demostrar zero reutilització després d'un flip d'oclusió, zero integrals per frame, coalescing de moviment ràpid i que prefetch/cold/warm mantenen el pressupost d'error.

## Fase 5 — cúpules, projeccions i renderer

`DomeProfile`, PCHIP, projeccions fotomètriques/SQM/TESS, `BortleEquivalent` versionat, composició reference/instantaneous, renderer lineal i doble buffer. La mostra 90° ha de reproduir el gate zenital. El mode **skyRenderingMode=simulated|physical** és permanent i independent del mode de contaminació lumínica; `compare` és opcional i exclusiu de diagnòstic. No eliminar el shader simulat del Pas 7.

## Fase 6 — atmosfera real

Atmosfera estàndard → ERA5/CAMS → providers observats/forecast. Procedència visible.

## Fase 7 — núvols

Single-scattering amb limitacions explícites; no activar per defecte fins validar.

## Fase 8 — B7, acceleracions i ground truth

Benchmark full, validació geogràfica, SLO i uncertainty budget. Qualsevol backend precomputat/LUT/FFT es valida contra la ruta directa dins del seu domini; no es promociona només perquè sigui més ràpid.

## Fase 9 — retirada legacy

Només després d'evidència: el mode físic esdevé automàtic per defecte. Bortle/magnitud manual romanen com a override/fallback si producte ho vol. El shader `u_artificialBrightness` deixa de ser autoritat i es pot eliminar quan cap ruta vigent el necessiti.

## Rollback

Cada fase manté un flag/configuració que permet tornar a l'últim camí homologat. No s'esborra el legacy fins a la fase 9. Els esquemes wire són versionats per permetre frontend/backend desalineats temporalment durant desenvolupament.
## Separació respecte de la vertical solar/lunar

Aquesta migració tracta **únicament el skyglow artificial**. El transport solar/lunar Hillaire, la SkyView LUT RGB, el selector permanent simulat/real i el limbe terrestre tenen [pla propi 7.51+](../cel-fisic/README.md). Compartir estat òptic i sumar radiància lineal no implica reutilitzar el PropagationKernel per al Sol o la Lluna.
