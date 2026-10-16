# Pas 7.61 — Fons natural nocturn: airglow, zodiacal i llum estel·lar integrada

> **Estat:** pendent. **Estat funcional:** no implementat. **Origen:** planificat. **Abast vigent:** Implementar `NaturalNightSkyModel` com a component espectral independent, sense Lluna ni contaminació artificial.

## Descripció funcional

El cel sense Lluna no és negre ni un `night floor` constant. Es componentitza en airglow, llum zodiacal, integrated starlight no resolta i un port extragalàctic opcional, evitant doble comptatge amb estrelles resoltes i Pas 10.

## Fonts a consultar

- [Dossier del cel físic](../../cel-fisic/README.md), especialment [decisions tancades](../../cel-fisic/05-decisions-tancades.md) i [contractes](../../cel-fisic/04-contractes-validacio.md).
- [Normes d'arquitectura](../../normes-arquitectura.md) i [inventari funcional](../../inventari-funcional.md).
- [Dossier skyglow](../../skyglow/README.md) només per contractes compartits; no fusionar integradors.

## Objectiu

Implementar `NaturalNightSkyModel` com a component espectral independent, sense Lluna ni contaminació artificial.

## Dependències

**Depèn de:**
- [Pas 7.60](pas7.60-integracio-three-bridge.md)

**En depenen:**
- [Pas 7.62](pas7.62-radiative-error-budget.md)

## Codi existent a reutilitzar

Catàleg estel·lar ja autoritzat pel projecte, Pas 10, efemèrides/eclíptica, `SkyRadianceComposer` i contractes espectrals.

## Flux tècnic

providers autoritzats → airglow + zodiacal + integrated starlight → `NaturalNightSkyState[N,direction]` → composició lineal.

## Errors, cancel·lació i recursos

- Revisions temporals latest-wins; cap resultat obsolet es publica.
- Dades o drets no verificats → `unavailable`, no dades inventades.
- **Risc:** doble comptatge amb Gaia/Pas 10 o convertir una constant visual en radiància científica.
- **Rollback:** component concret `unavailable`; la resta del cel físic continua traçable.

## Tasques

- [ ] Crear `NaturalNightSkyModel` amb components i disponibilitat/procedència separades.
- [ ] Airglow: model paramètric espectral propi, amb dependències explícites de geometria/temps/proxy solar quan disponible; cap constant opaca de calibratge.
- [ ] Zodiacal: model en coordenades eclíptiques amb espectre solar reflectit i coeficients/dades auditats.
- [ ] Integrated starlight: mapa angular precomputable d'un catàleg autoritzat; definir `unresolvedMagnitudeCut` i excloure estrelles renderitzades individualment.
- [ ] Mantenir la Via Làctia difusa al Pas 10 i sumar-la una sola vegada.
- [ ] Usar GAMBONS i ESO/SkyCalc com a referències externes; no vendoritzar codi/datasets incompatibles.

## Criteri de sortida

`naturalMoonless` és espectral, componentitzat, versionat i no conté Lluna ni skyglow artificial; cada component pot ser `available/unavailable` sense falsejar la resta.

## Proves i evidències obligatòries

- [ ] airglow baix/nominal/alt i dependència zenital/temporal definida;
- [ ] geometries eclíptiques diverses per zodiacal;
- [ ] conservació `resolved + unresolved` sense duplicar estrelles;
- [ ] regressió contra ordres de magnitud/estructura angular de referències externes.
- [ ] Evidències reproduïbles sota `docs/evidencies/pas7.61/`.
- [ ] `tools/validate_docs.py` i regressions afectades en verd abans de completar.

## Fora d'abast

Química completa de la termosfera, incorporar codi GPL d'ESO o nous catàlegs sense llicència auditada.

## Instrucció per a Codex

airglow + zodiacal + integrated starlight → `NaturalNightSkyState` espectral → `SkyRadianceComposer`; Pas 10 continua sent propietari de la Via Làctia difusa. Respectar `simulated|physical`, la separació 7.1–7.50 / 7.51+, les unitats i les llicències. No donar per implementat un contracte buit.

## Treball pendent

- [ ] Completar tasques, proves i evidències abans de moure aquest document a `completat/`.
