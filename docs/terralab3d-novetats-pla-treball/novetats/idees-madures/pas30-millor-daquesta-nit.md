# Pas 30 — "El millor d'aquesta nit" (llistat filtrable d'objectes recomanats)

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc «Lo mejor de esta noche».
> Depèn de: Pas 28 (`ObservableObject`).

## Resultat funcional palpable

Un panell dedicat mostra, per a la ubicació i data actuals, els objectes més interessants a observar aquesta nit: tipus tarjeta amb gràfic d'alçada en V invertida, hores de visibilitat, magnitud i mida angular, amb filtres multiselecció tipus Excel i un botó «Afegir al pla» a cada resultat.

## Context i decisions preses

- Llistat/pantalla amb els objectes més interessants segons ubicació i data.
- Gràfic d'alçada/visibilitat en forma de **V invertida** (puja i baixa al llarg de la nit).
- Dades per objecte: hora d'inici i final de visibilitat, alçada màxima, mida angular, tipus d'objecte, magnitud.
- **Filtres multiselecció tipus Excel**, per columna, amb possibilitat de combinar filtres de diverses columnes alhora.
- Botó **«Afegir al pla»** directament des de cada resultat (connecta amb el Pas 31, planificador).
- Ubicació a la UI: **no** dins del quadre de cerca (és una recomanació, no una cerca). Es col·loca com una **targeta visual compacta** a la zona dreta de la interfície, a la part superior del bloc de controls (on ja hi ha els botons de capes), amb una imatge dinàmica de l'objecte més destacat de la nit. En clicar-la s'obre el panell dedicat, reutilitzant el mateix patró lateral que el cercador. Des de la cerca avançada hi ha un enllaç discret («Vols veure les recomanacions d'aquesta nit?») cap a aquest panell.
- Per a imatges: en la primera versió, icones propis o miniatures generades pel mateix TerraLab3D (no fotografies externes, evitar problemes de llicència); més endavant es pot revisar si hi ha fonts lliures.

## Objectiu

Construir el panell «El millor d'aquesta nit» com a consumidor de `ObservableObject` (Pas 28), amb taula/targetes filtrables i integració amb el planificador.

## Tasques

- [ ] Calcular, per a la nit actual i la ubicació de l'observador, el conjunt d'objectes rellevants (llindars de magnitud, alçada mínima, tipus d'objecte a incloure).
- [ ] Dissenyar la targeta d'objecte: nom, tipus, magnitud, mida angular, hores de visibilitat, gràfic en V invertida.
- [ ] Implementar filtres multiselecció per columna (tipus, alçada, magnitud, instrument recomanat).
- [ ] Botó «Afegir al pla» a cada targeta.
- [ ] Accés directe des de la UI: targeta compacta a la zona dreta superior del panell de capes, amb imatge dinàmica.
- [ ] Enllaç discret des de la cerca avançada cap al panell.
- [ ] En clicar una fila: centrar càmera, activar trajectòria i overlay de l'objecte (reutilitzant Pas 28).
- [ ] Generar icones/miniatures pròpies per objecte (renderitzades per TerraLab3D, no fotografia externa).

## Criteri de sortida

El panell mostra una llista coherent i filtrable d'objectes per a la nit i ubicació actuals; els filtres es poden combinar; clicar un objecte el centra i n'activa la trajectòria; el botó «Afegir al pla» crea una entrada consumible pel planificador.

## Evidència obligatòria

- [ ] Captura del panell amb almenys 10 objectes i el gràfic en V invertida.
- [ ] Captura amb filtres multiselecció combinats aplicats.
- [ ] Captura de la targeta d'accés a la zona dreta de la UI.

## Fora d'abast del pas

La implementació interna del planificador (Pas 31); només cal que «Afegir al pla» generi l'esdeveniment que aquell mòdul consumirà.

## Prompt per a Codex

```
Implementa el Pas 30 ("El millor d'aquesta nit") descrit a
docs/novetats/idees-madures/pas30-millor-daquesta-nit.md sobre main, després del Pas 28. Crea el
panell filtrable (tipus Excel, multiselecció per columna) que consumeix ObservableObject per calcular
visibilitat i alçada de cada objecte, amb gràfic en V invertida per fila. Col·loca l'accés com una
targeta visual compacta a la zona dreta de la UI, a sobre del bloc de capes (no dins del cercador),
amb un enllaç discret des de la cerca avançada. Genera miniatures pròpies amb el renderer de
TerraLab3D, no facis servir imatges externes.
```
