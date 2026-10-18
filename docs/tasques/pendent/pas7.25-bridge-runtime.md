# Pas 7.25 — Skyglow físic — Bridge Python→TypeScript i SkyglowRuntime

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Reutilitzar `configure_skyglow` i `skyglow_configuration_snapshot` de 7.5.1. Connectar modalitat/K/família/normalització a les observacions seleccionades i al transport real, amb provenance Black Marble/RSR resolta, hash complet, revisions i descart de resultats obsolets.

## Descripció funcional

Transportar resultats físics ja homologats sense portar integració radiativa al frontend.

## Fonts a consultar

- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [06-contractes-dades.md](../../skyglow/06-contractes-dades.md)

**Etiqueta de domini obligatòria a la integració:** `sourceMode=DEFINED_SOURCE|CONDITIONAL_L3|OBSERVATION_VALIDATED`, `absoluteCalibrationStatus`, procedència i estats d'incertesa. S pot mostrar-se com a simulació, C només com a escenari hipotètic, H com a validat empíricament quan superi gates. Cap conversió silenciosa C→H.

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Reutilitzar `configure_skyglow` i `skyglow_configuration_snapshot` de 7.5.1. Connectar modalitat/K/família/normalització a les observacions seleccionades i al transport real, amb provenance Black Marble/RSR resolta, hash complet, revisions i descart de resultats obsolets.

## Dependències

**Depèn de:**
- [Pas 7.24](pas7.24-full-ground-truth.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.26](pas7.26-three-renderer-debug.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Reutilitzar `configure_skyglow` i `skyglow_configuration_snapshot` de 7.5.1. Connectar modalitat/K/família/normalització a les observacions seleccionades i al transport real, amb provenance Black Marble/RSR resolta, hash complet, revisions i descart de resultats obsolets.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [ ] Definir DTO versionat per `PropagationResultSummary`/`DomeProfile`, bandSetId, unitats, revisions i provenance compacta.
- [ ] Implementar `SkyglowRuntime` amb requested/accepted revision, double-buffer de presentació i stale discard.
- [ ] Compartir golden tests de PCHIP si la reconstrucció es fa a TypeScript.
- [ ] Mesurar bytes de bridge, latència i upload preparatori.
- [ ] Prohibir nodes de quadratura, rasters massius i integrals del kernel al render loop.
- [ ] Reutilitzar `configure_skyglow` i `skyglow_configuration_snapshot` de 7.5.1. Connectar modalitat/K/família/normalització a les observacions seleccionades i al transport real, amb provenance Black Marble/RSR resolta, hash complet, revisions i descart de resultats obsolets.

## Criteri de sortida

TypeScript pot rebre/validar/swap resultats de skyglow amb revisió monotònica i sense executar física de propagació.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.25/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

El frontend transporta i presenta. Si necessites física nova per dibuixar, torna al backend.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
