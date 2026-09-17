# Pas 35 — Pestanya d'eclipsis

> **Estat:** parcial. **Estat funcional:** parcial. **Origen:** planificat. **Abast vigent:** pestanya d'eclipsis, integració observable i persistència associada.

## Descripció funcional

El cercador mostra `[ Objectes ] [ Efemèrides ] [ Eclipsis ]`; la tercera pestanya llista eclipsis calculats, en descriu tipus i visibilitat des de l'observador i situa tota l'aplicació a l'instant clau amb un clic.

## Fonts a consultar

- [TerraLab al commit auditat `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`](https://github.com/ArcadiaLliure/TerraLab/tree/1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d): oracle autoritzat de comportament.

Decisions tancades de referència:
- Aquest pas no reimplementa ni bifurca la geometria del pas 9.
- La consulta sempre declara rang temporal, observador i filtre “visibles des d'aquí” o “tots”.
- Cada fila mostra solar/lunar, total/parcial/anular quan apliqui, instant clau, fases disponibles i visibilitat local.
- “Anar a la data” actualitza el rellotge global una sola vegada i conserva el resultat seleccionat.
- La miniatura és opcional i, si s'activa, consumeix el pas 34; la llista funciona sense ella.

## Objectiu

Completar la vertical de «pestanya d'eclipsis» de punta a punta, mantenint la separació de responsabilitats, contractes tipats i integració amb el renderer Three.js sense anticipar capacitats posteriors.

## Dependències

**Depèn de:**
- [Pas 9 — Eclipsis, ocultacions, separacions i trajectòries](../completat/pas9.md)
- [Pas 33 — Cercador d'objectes i efemèrides](pas33-cercador-objectes-efemerides.md)
- [Pas 34 — Miniatures i animacions d'efemèrides](pas34-previsualitzacions-efemerides.md)

**En depenen:**
- [Pas 38 — Homologació final, recuperació i rendiment](pas38-homologacio-final.md)

## Codi existent a reutilitzar

- **Repositori actual:** - Domini: [`eclipses/models.py`](../../../backend/src/terralab3d/domain/eclipses/models.py), [`eclipses/calculations.py`](../../../backend/src/terralab3d/domain/eclipses/calculations.py) i [`eclipses/services.py`](../../../backend/src/terralab3d/domain/eclipses/services.py).
- Aplicació: [`astronomical_events.py`](../../../backend/src/terralab3d/application/astronomical_events.py) i [`ports/astronomical_events.py`](../../../backend/src/terralab3d/application/ports/astronomical_events.py).
- UI/contracts: [`SearchPanel.ts`](../../../frontend/src/view/ui/panels/SearchPanel.ts), [`SearchWidget.ts`](../../../frontend/src/view/ui/components/SearchWidget.ts) i [`astronomical_event_contracts.ts`](../../../frontend/src/contracts/astronomical_event_contracts.ts).
- Proves: [`test_astronomical_events_step9.py`](../../../backend/tests/test_astronomical_events_step9.py) i [`astronomical_events_step9.test.ts`](../../../frontend/src/tests/astronomical_events_step9.test.ts).
- **Projectes de referència autoritzats:** TerraLab (commit `1fbcf088a0bfc1f832fc0f2a8ba2808e3e783a7d`).

## Flux tècnic

Tab Eclipsis + rang + observador → consulta del pas 9 → resultats versionats → filtre de visibilitat → files tipades → comanda global de temps i selecció.

## Errors, cancel·lació i recursos

- Canviar rang, filtre o ubicació cancel·la la consulta anterior i descarta respostes tardanes.
- Kernel absent o error de càlcul es mostra com a error de recurs/càlcul, no com una llista buida.
- Les miniatures es cancel·len/disposen segons el pas 34; la resta de la pestanya no depèn d'elles.

## Tasques

- [x] El pas 9 cerca i refina eclipsis solars/lunars amb SPICE.
- [x] El pas 33 defineix el contenidor multipestanya i l'acció atòmica “anar a la data”.
- [ ] No hi ha encara llista dedicada, filtres de visibilitat ni navegació UI d'eclipsis.
- [ ] Afegir tab, estat propi, presets de rang i filtres solar/lunar/visibilitat.
- [ ] Adaptar els resultats del pas 9 al view-model del cercador sense perdre fases ni procedència.
- [ ] Calcular l'indicador de visibilitat local reutilitzant observador i horitzó existents.
- [ ] Connectar consulta paginada/cancel·lable i acció “anar a la data”.
- [ ] Incorporar miniatura només si el pas 34 és disponible, amb placeholder estable en cas contrari.
- [ ] Afegir buits, errors de kernel i rang sense resultats com a estats diferenciats.

## Criteri de sortida

La pestanya llista i filtra eclipsis verificats pel motor existent, diferencia absència de resultats i error, i situa rellotge/escena exactament a l'instant seleccionat.

## Proves i evidències obligatòries

- [ ] Eclipsi solar i lunar coneguts, visible i no visible des de dues ubicacions.
- [ ] Rang buit, rang invàlid, canvi ràpid d'observador i error de kernel.
- [ ] Exactitud d'“anar a la data” i preservació de selecció/tab.
- [ ] Regressió de les proves científiques del pas 9.
- [ ] Llista d'un període conegut contrastada amb fixtures/font autoritativa.
- [ ] Captures dels filtres visible/tots i d'un eclipsi lunar/solar.
- [ ] Vídeo d'“anar a la data”.
- [ ] Resultat sense regressions de la suite del pas 9.

## Fora d'abast

Modificar el càlcul geomètric d'eclipsis o fer una animació especial diferent del pas 34.

## Instrucció per a Codex

Afegeix la tercera pestanya sobre el cercador del pas 33 i consumeix directament el motor del pas 9. No reimplementis SPICE; concentra't en consulta, visibilitat, estats UI i salt atòmic al temps.

## Treball pendent

- [ ] Completar totes les tasques i evidències d'aquest pas abans de tancar el criteri de sortida.
