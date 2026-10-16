# Pas 7.23 — Skyglow físic — composició lineal del cel i estat reference/instantaneous

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Separar i compondre artificial, natural sense Lluna, Lluna i crepuscle en radiància lineal compatible.

## Descripció funcional

Defineix la frontera entre el skyglow artificial i la resta del cel. Evita que la Lluna, el crepuscle o un fons natural fix quedin absorbits dins un factor de calibratge artificial.

## Fonts a consultar

- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`06-contractes-dades.md`](../../skyglow/06-contractes-dades.md) i [ADR-017](../../skyglow/adrs/ADR-017-zenith-photometric-projections.md).

## Objectiu

Publicar `SkyRadianceComponents` i dos estats explícits: `reference` (moonless/twilight-free) i `instantaneous` (data/hora real).

## Dependències

**Depèn de:**
- [Pas 7.22](pas7.22-photometric-projections.md)

**En depenen:**
- [Pas 7.26](pas7.26-ground-truth-validation.md)
- [Pas 7.28](pas7.28-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- Camp artificial del `PropagationKernel`/`DomeProfile`.
- Models astronòmics/atmosfèrics existents o futurs per cel natural, Lluna i crepuscle mitjançant ports; no duplicar efemèrides. La vertical 7.51+ desenvolupa aquests ports sense fer dependre el kernel artificial del renderer Hillaire.
- Projeccions del Pas 7.22.

## Flux tècnic

components amb band set/directions/provenance → comprovació de compatibilitat → suma lineal → estat reference/instantaneous → projeccions fotomètriques/sensor → UI/renderer.

## Errors, cancel·lació i recursos

- Component desconegut és `unavailable`; no s'inventa un fons constant.
- No es sumen magnituds, RGB tone-mapped ni SQM; només radiància/luminància lineal compatible.
- La composició és barata i cachejable; no crea LOS ni recomputa scattering artificial.

## Tasques

- [ ] Implementar `SkyRadianceComponents` i semàntica de disponibilitat.
- [ ] Definir `reference` vs `instantaneous`.
- [ ] Connectar ports per natural/Lluna/crepuscle sense acoblar-los al kernel artificial; no convertir la SkyView LUT RGB en radiància espectral de sensor.
- [ ] Assegurar que `BortleEquivalent` de lloc només consumeix reference.
- [ ] Afegir telemetria de components i versions.

## Criteri de sortida

La suma és lineal i commutativa dins tolerància, cada component conserva provenance, l'estat reference és invariant a fase/posició lunar i crepuscle, i l'instantaneous respon a aquests components sense tocar el skyglow artificial.

## Proves i evidències obligatòries

- [ ] artificial-only, natural-only, moon-only i suma combinada.
- [ ] zero/absent/unavailable diferenciats.
- [ ] canviar Lluna modifica instantaneous però no reference/BortleEquivalent.
- [ ] cap nova integral del PropagationKernel durant composició.
- [ ] Evidència sota `docs/evidencies/pas7.23/`.

## Fora d'abast

Model físic detallat de multiple scattering lunar o airglow si encara no existeix; el pas defineix contractes i composició, no inventa aquests models.

## Instrucció per a Codex

Compon només camps físicament compatibles i conserva canals/provenance. No hardcodegis un fons natural ni utilitzis SQM/Bortle com a moneda intermèdia.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
