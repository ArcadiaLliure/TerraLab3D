# Pas 7.26 — Skyglow físic — Renderer Three.js lineal i modes diagnòstics

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Connectar els controls realista/K ja implementats a la radiància física calculada. Verificar resposta espectral del cel en canviar K sota magnitud conservada; cap filtre RGB ni integral radiativa al render loop.

## Descripció funcional

Renderitzar radiància artificial lineal amb doble buffer i fer-la inspeccionable sense alterar-la.

## Fonts a consultar

- [03-pipeline-python-typescript-threejs.md](../../skyglow/03-pipeline-python-typescript-threejs.md)
- [13-debug.md](../../skyglow/13-debug.md)

Fonts locals del pla vigent consultades el 2026-10-18; cap asset no es declara validat només per una referència.

## Objectiu

Connectar els controls realista/K ja implementats a la radiància física calculada. Verificar resposta espectral del cel en canviar K sota magnitud conservada; cap filtre RGB ni integral radiativa al render loop.

## Dependències

**Depèn de:**
- [Pas 7.25](pas7.25-bridge-runtime.md)
- [Pas 7.5.1](../completat/pas7.5.1-black-marble-spectral-simulation.md)

**En depenen:**
- [Pas 7.27](pas7.27-sky-composition.md)

## Codi existent a reutilitzar

- **Repositori actual:** [SourceModel S/C](../../../backend/src/terralab3d/domain/light_pollution/source_model.py), [escenaris i configuració](../../../backend/src/terralab3d/domain/light_pollution/simulation.py), [biblioteca](../../../backend/src/terralab3d/domain/light_pollution/spectral_library.py) i [controls](../../../frontend/src/view/ui/components/SkyglowControls.ts). Reutilitzar els contractes sense duplicar el motor.
- **Projectes de referència autoritzats:** cap runtime extern; els oracles científics independents han de tenir fonts i llicències verificades abans d’incorporar-los.

## Flux tècnic

Configuració versionada + SourceModel S/C + procedència → component del pas → sortida amb unitats, revisió i qualificació pròpies. Connectar els controls realista/K ja implementats a la radiància física calculada. Verificar resposta espectral del cel en canviar K sota magnitud conservada; cap filtre RGB ni integral radiativa al render loop.

## Errors, cancel·lació i recursos

Previst: rebutjar entrades no finites, unitats i revisions incompatibles; cancel·lació cooperativa, latest-wins i descart de resultats antics. Recursos grans persistents fora del JSON de cada frame; alliberament explícit pel propietari. RSR de referència C no es promou a H; incertesa desconeguda no es converteix en sigma.

## Tasques

- [ ] Implementar `DomeSkyglowRenderer` retingut amb buffer inactiu→upload→swap.
- [ ] Sumar radiància lineal abans de camera/exposure/tone mapping/display transform.
- [ ] Implementar overlays/fals color de components, revisions, cache/error i provenance sense payload massiu per defecte.
- [ ] Mesurar frame p95/p99, GPU upload, stutter, leaks i context loss/resync.
- [ ] Mantenir el fallback visual legacy disponible però no com a autoritat científica.
- [ ] Connectar els controls realista/K ja implementats a la radiància física calculada. Verificar resposta espectral del cel en canviar K sota magnitud conservada; cap filtre RGB ni integral radiativa al render loop.

## Criteri de sortida

El renderer mostra el camp artificial sense càlcul radiatiu per frame, descarta resultats tardans i els modes debug OFF no alteren física ni rendiment materialment.

## Proves i evidències obligatòries

- [ ] Proves unitàries/golden/property rellevants en verd.
- [ ] Regressions afectades en verd.
- [ ] Evidència reproduïble sota `docs/evidencies/pas7.26/`.
- [ ] README/inventari/estat actualitzats només segons comportament observable.
- [ ] Cap capacitat d’un pas posterior marcada prematurament com a implementada.
- [ ] Verificar el nou abast S/C i les modalitats realista/K amb casos independents; H conserva el seu contrast empíric.

**Resultats verificats:** aquest pas encara no s’ha executat; les proves de configuració/font corresponen a 7.5.1.

## Fora d'abast

Homologar H sense observacions; fabricar fonts o radiància; modificar llindars després dels resultats.

## Instrucció per a Codex

No tornis a convertir Bortle/SQM en brillantor de shader. La dada d’entrada és radiància física.

Quan el criteri de sortida no es pugui demostrar, **no continuïs al pas següent**. Corregeix aquest pas o marca’l `bloquejat` amb la causa i l’evidència.

Aplicar la política de referència RSR i dominis vigent; no reobrir la cerca anual exacta com a prerequisit global. No declarar la propagació implementada a partir dels controls de 7.5.1.

## Treball pendent

- [ ] Executar les tasques i demostrar el criteri de sortida d’aquest pas. La connexió gràfica final de kelvins continua obligatòria fins a 7.27.
