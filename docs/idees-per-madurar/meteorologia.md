# Meteorologia

> Estat: **per madurar**. Aquesta capacitat no forma part de l'ordre executable del pla.

## Motivació

TerraLab3D ja té models de clima, un component d'escena i una interfície de renderer, però no hi ha una vertical meteorològica connectada. Abans de reprendre-la cal decidir quin problema de producte resol i com es relaciona amb el rellotge de simulació.

## Punt de partida reutilitzable

- Models: [`climate/models.py`](../../backend/src/terralab3d/domain/climate/models.py) i [`climate/calculations.py`](../../backend/src/terralab3d/domain/climate/calculations.py).
- Esquema d'escena: [`components.py`](../../backend/src/terralab3d/scene/components.py).
- Esquelet d'integració: [`weather/adapter.py`](../../backend/src/terralab3d/infrastructure/adapters/weather/adapter.py).
- Renderers previstos: [`WeatherLayerRenderer.ts`](../../frontend/src/view/three/layers/WeatherLayerRenderer.ts) i [`AtmosphereRenderer.ts`](../../frontend/src/view/three/AtmosphereRenderer.ts).
- Capacitat relacionada ja completada: [Pas 7 — cel i atmosfera](../completat/pas7.md).

L'existència d'aquests esquelets no aprova el seu contracte ni obliga a conservar-los quan la idea maduri.

## Decisions pendents

1. La capa ha de representar el temps real actual, dades històriques coherents amb la data simulada o només condicions d'observació configurables?
2. Quin és el resultat prioritari: informació meteorològica, degradació astronòmica de la visibilitat o simulació visual de núvols i precipitació?
3. Quins proveïdors, llicències, límits d'ús, política de caché i identificació del client són acceptables?
4. Com es comunica la diferència entre dada remota, dada antiga, estat parcial i fallback sense presentar una simulació com una observació real?
5. Quin fallback offline és científicament honest i quines entrades el fan reproduïble?
6. Quins efectes entren en el primer lliurable: extinció, transparència, boira, núvols, pluja, neu o vent?
7. Quin pressupost de CPU/GPU, partícules, textures i actualització manté la càmera i el timeline fluids?
8. Com s'activa, es desactiva i es combina aquesta capacitat amb atmosfera, contaminació lumínica i el futur gestor de capes?

## Condició de maduresa

La idea podrà tornar al backlog quan estiguin aprovats el cas d'ús, l'autoritat temporal, les fonts i llicències, la semàntica del fallback, el primer abast visual, la integració amb les capes existents i els pressupostos de recursos. En aquell moment s'haurà de verificar de nou el codi real i redactar una vertical executable amb proves i criteri de sortida.

## Relació amb el pla

Es relaciona amb el [Pas 7 — cel i atmosfera](../completat/pas7.md) i el [Pas 25 — gestor de capes](../pendent/pas25-gestor-capes.md), però no els bloqueja ni forma part de l'homologació del pas 38 mentre mantingui l'estat `per madurar`.
