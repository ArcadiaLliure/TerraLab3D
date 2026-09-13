# Pas 18 — Meteorologia real, fallback i efectes atmosfèrics

> Estat: **pendent**. Hi ha models, component d'escena i interfície de renderer, però no una vertical meteorològica executable.

## Estat actual verificat

- [x] Existeixen `ClimateState`, `WeatherComponent` i fronteres previstes per adaptador i renderer.
- [x] L'atmosfera, el cel i la il·luminació ja disposen de camins incrementals que es poden modular.
- [ ] L'adaptador meteorològic llença `NotImplementedError` i el renderer és només una interfície.

## Resultat funcional

La capa meteorològica mostra condicions remotes normalitzades o un fallback determinista, representa núvols, boira, pluja o neu i modifica de manera coherent la transparència del cel sense bloquejar la simulació.

## Dependències

- [Pas 7 — cel, atmosfera i contaminació lumínica](../completat/pas7.md).
- [Pas 8.7 — il·luminació física](../completat/pas8.7.md).
- [Normes d'arquitectura](../normes_arquitectura.md).

## Decisions tancades

- MET Norway és una integració d'infraestructura darrere un port; el domini només rep estat meteorològic normalitzat.
- El fallback és reproduïble amb llavor, ubicació i slot temporal explícits; mai depèn d'aleatorietat global.
- La meteorologia visual no altera les efemèrides ni els catàlegs: produeix paràmetres d'extinció, boira i recursos visuals.
- Desactivar la capa suspèn o allibera recursos costosos i conserva la resta de l'escena.

## Codi existent a reutilitzar

- Models: [`climate/models.py`](../../backend/src/terralab3d/domain/climate/models.py) i [`climate/calculations.py`](../../backend/src/terralab3d/domain/climate/calculations.py).
- Esquema d'escena: [`components.py`](../../backend/src/terralab3d/scene/components.py).
- Adaptador pendent: [`weather/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/weather/adapter.py).
- Renderers: [`WeatherLayerRenderer.ts`](../../frontend/src/view/three/layers/WeatherLayerRenderer.ts) i [`AtmosphereRenderer.ts`](../../frontend/src/view/three/AtmosphereRenderer.ts).
- Oracle TerraLab: [sistema meteorològic](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/weather/system.py) i [proveïdor MET Norway](https://github.com/ArcadiaLliure/TerraLab/blob/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d/TerraLab/weather/metno_provider.py).

## Treball pendent

- [ ] Tancar `ClimateState`: cobertura per capes, humitat, visibilitat, boira, precipitació, vent, slot i qualitat.
- [ ] Implementar MET Norway amb User-Agent, timeout, caché, normalització i errors contextualitzats.
- [ ] Implementar fallback determinista i transicions suaus entre remot, parcial i fallback.
- [ ] Publicar snapshots versionats; descartar respostes d'una ubicació o slot antics.
- [ ] Implementar núvols/estrats persistents, moviment per vent independent del FPS i boira mètrica.
- [ ] Implementar pluja/neu amb pressupost de partícules i degradació explícita.
- [ ] Aplicar extinció/transparència a estrelles, cel profund, Via Làctia i cossos sense duplicar la lògica científica.
- [ ] Mostrar font, antiguitat, qualitat i fallback amb estabilització anti-flicker.

## Flux tècnic

Activació o canvi d'observador/slot → coordinador latest-wins → port meteorològic → `ClimateState` → snapshot de cel i component visual → uniforms/recursos persistents → render.

## Errors, cancel·lació i recursos

- Xarxa absent o dades parcials degraden a fallback; una cancel·lació o resposta obsoleta no es registra com a fallada.
- Textures, geometries de núvols, partícules i temporitzadors tenen propietari i `dispose` explícit.
- No es fan peticions ni càlculs meteorològics per frame.

## Proves

- Normalització de payloads complets/parcials, expiració de caché, timeout i recuperació.
- Determinisme del fallback per llavor, ubicació i slot.
- Latest-wins al canviar ràpidament d'ubicació.
- Recursos persistents, desactivació i `dispose`.
- Integració visual per cel clar, núvols, boira, pluja i neu.

## Criteri de sortida

La capa informa la seva autoritat, funciona offline, altera visiblement l'escena, transiciona sense parpelleig i manté càmera i timeline fluides.

## Evidències

- [ ] Captures dels cinc estats meteorològics.
- [ ] Prova de xarxa absent i recuperació remota.
- [ ] Mètriques de peticions, càlcul i frame cobert.
- [ ] Informe de recursos abans/després de desactivar la capa.

## Fora d'abast

Predicció meteorològica pròpia i simulació fluidodinàmica de núvols.

## Instrucció per a Codex

Completa la vertical des del port fins al renderer, reutilitzant atmosfera i escena persistent. No implementis ciència meteorològica a Three.js ni substitueixis errors de xarxa per dades aparentment reals.
