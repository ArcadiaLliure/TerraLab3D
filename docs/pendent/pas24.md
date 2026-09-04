# Pas 24 — Homologació integral, recuperació, rendiment i independència de producte

> Estat: **pendent**
> Conserva l’especificació original i encara requereix completar el criteri de sortida.

## Resultat funcional palpable

TerraLab3D cobreix totes les funcionalitats acordades, és independent de TerraLab en execució, es recupera de fallades i compleix pressupostos científics i gràfics.

## Fonts TerraLab a consultar

- Tot `E:\Desarrollo\TerraLab` com a referència funcional
- `tests/architecture`, regressions offscreen i benchmarks de TerraLab
- `benchmarks/*` i `tools/dev/*`
- Documentació i fixtures generats durant els passos 1–23

## Objectiu

Completar aquesta vertical funcional de punta a punta, mantenint la separació de responsabilitats i sense anticipar funcionalitats posteriors que no siguin imprescindibles.

## Tasques

- [ ] Executar la matriu completa de les 24 funcionalitats amb evidència per fila.
- [ ] Comparar ubicacions, dates, càmeres, capes, datasets i instruments equivalents.
- [ ] Comparar valors científics amb toleràncies explícites.
- [ ] Comparar captures per semàntica visual i llegibilitat, no per píxel idèntic.
- [ ] Executar proves manuals de pan, zoom, timeline, realtime, cerca, picking, scope, terreny, eines i shutdown.
- [ ] Definir pressupostos de frame P50/P95, CPU, GPU, RSS, bridge, draw calls i càrrega.
- [ ] Perfilar càmera, canvi d’un segon, salt temporal, càrrega Gaia, tile DEM, superfície i scope dens.
- [ ] Eliminar reconstruccions, còpies i allocations que superin pressupost.
- [ ] Implementar recuperació després de perdre el context WebGL.
- [ ] Implementar reinici del frontend i resync des d’un snapshot autoritatiu.
- [ ] Fer idempotents start, suspend, resume, restart i close.
- [ ] Verificar dispose de tots els recursos GPU i tancament de workers/handles.
- [ ] Eliminar mocks, adapters temporals, flags de migració i rutes legacy.
- [ ] Eliminar qualsevol dependència executiva de `E:\Desarrollo\TerraLab`.
- [ ] Documentar procedència i llicència dels algoritmes/datasets migrats.
- [ ] Congelar versions de contractes, schemas i formats persistents.
- [ ] Publicar guia d’usuari, guia de dades, guia de desenvolupament i troubleshooting.
- [ ] Documentar diferències intencionals i obtenir acceptació explícita.

## Criteri de sortida

Cap funcionalitat queda sense evidència; la ciència compleix toleràncies; la UI cobreix els fluxos de treball de TerraLab; Three.js manté una escena persistent; el producte arrenca, es recupera i es tanca netament; no depèn del renderer QPainter ni del repositori TerraLab.

## Evidència obligatòria

- [ ] Informe final de paritat funcional i científica.
- [ ] Quadre de pressupostos i resultats P50/P95.
- [ ] Captures i vídeos de tots els fluxos de treball principals.
- [ ] Informe de recursos GPU, RSS, bytes del bridge i còpies.
- [ ] Prova de pèrdua de context, desconnexió i restart.
- [ ] Llista zero de funcionalitats sense propietari o sense evidència.

## Fora d’abast del pas

No queda cap pas funcional pendent dins de l’abast d’homologació.
