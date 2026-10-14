# Pas 23.692 — Skyglow físic — composició lineal del cel i estat reference/instantaneous

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Separar i compondre artificial, natural sense Lluna, Lluna i crepuscle en radiància lineal compatible.

## Descripció funcional

Defineix la frontera entre el skyglow artificial i la resta del cel. Evita que la Lluna, el crepuscle o un fons natural fix quedin absorbits dins un factor de calibratge artificial.

## Fonts a consultar

- [`01-especificacio-algorismes.md`](../../skyglow/01-especificacio-algorismes.md), [`03-pipeline-python-typescript-threejs.md`](../../skyglow/03-pipeline-python-typescript-threejs.md), [`06-contractes-dades.md`](../../skyglow/06-contractes-dades.md) i [ADR-017](../../skyglow/adrs/ADR-017-zenith-photometric-projections.md).

## Objectiu

Publicar `SkyRadianceComponents` i dos estats explícits: `reference` (moonless/twilight-free) i `instantaneous` (data/hora real).

## Dependències

**Depèn de:**
- [Pas 23.691](pas23.691-photometric-projections.md)

**En depenen:**
- [Pas 23.72](pas23.72-ground-truth-validation.md)
- [Pas 23.74](pas23.74-b7-homologacio-skyglow.md)

## Codi existent a reutilitzar

- Camp artificial del `PropagationKernel`/`DomeProfile`.
- Models astronòmics/atmosfèrics existents o futurs per cel natural, Lluna i crepuscle mitjançant ports; no duplicar efemèrides.
- Projeccions del Pas 23.691.

## Flux tècnic

components amb band set/directions/provenance → comprovació de compatibilitat → suma lineal → estat reference/instantaneous → projeccions fotomètriques/sensor → UI/renderer.

## Errors, cancel·lació i recursos

- Component desconegut és `unavailable`; no s'inventa un fons constant.
- No es sumen magnituds, RGB tone-mapped ni SQM; només radiància/luminància lineal compatible.
- La composició és barata i cachejable; no crea LOS ni recomputa scattering artificial.

## Tasques

- [ ] Implementar `SkyRadianceComponents` i semàntica de disponibilitat.
- [ ] Definir `reference` vs `instantaneous`.
- [ ] Connectar ports per natural/Lluna/crepuscle sense acoblar-los al kernel artificial.
- [ ] Assegurar que `BortleEquivalent` de lloc només consumeix reference.
- [ ] Afegir telemetria de components i versions.

## Criteri de sortida

La suma és lineal i commutativa dins tolerància, cada component conserva provenance, l'estat reference és invariant a fase/posició lunar i crepuscle, i l'instantaneous respon a aquests components sense tocar el skyglow artificial.

## Proves i evidències obligatòries

- [ ] artificial-only, natural-only, moon-only i suma combinada.
- [ ] zero/absent/unavailable diferenciats.
- [ ] canviar Lluna modifica instantaneous però no reference/BortleEquivalent.
- [ ] cap nova integral del PropagationKernel durant composició.
- [ ] Evidència sota `docs/evidencies/pas23.692/`.

## Fora d'abast

Model físic detallat de multiple scattering lunar o airglow si encara no existeix; el pas defineix contractes i composició, no inventa aquests models.

## Instrucció per a Codex

Compon només camps físicament compatibles i conserva canals/provenance. No hardcodegis un fons natural ni utilitzis SQM/Bortle com a moneda intermèdia.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
