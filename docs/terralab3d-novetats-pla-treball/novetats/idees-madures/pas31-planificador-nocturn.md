# Pas 31 — Planificador nocturn integrat a la barra temporal

> Estat: **proposta nova — idea madura**
> Origen: pluja d'idees TerraLab3D, bloc "Planificador nocturno integrado".
> Depèn de: Pas 28 (`ObservableObject`), Pas 30 (font d'objectes «Afegir al pla»).

## Resultat funcional palpable

Sobre la mateixa barra temporal existent apareix una banda amb blocs editables: cada observació planificada és un bloc que es pot arrossegar, allargar/escurçar, eliminar (amb "Desfer") i que mostra la seva qualitat d'observació amb un codi de colors i puntuació 0–100, avisant de solapaments i de trànsits de meridià.

## Context i decisions preses

- **No** és una pantalla separada: és una **banda integrada sobre la barra temporal** existent.
- Cada objecte és un bloc temporal amb interacció directa:
  - vora esquerra → modifica l'inici;
  - vora dreta → modifica el final;
  - centre → desplaça tot el bloc conservant la durada;
  - petita **X** en una cantonada → elimina;
  - després d'eliminar → avís temporal **"Desfer"**.
- Es pot afegir un objecte al pla des de: picking sobre el firmament, cercador, fitxa de l'objecte, "El millor d'aquesta nit" (Pas 30). Una única semàntica a tot arreu: **«Afegir al pla»**.
- **Qualitat dins del bloc:** el propi bloc mostra la qualitat/viabilitat al llarg del temps amb color — vermell ≈ dolenta/impossible, groc ≈ mediocre, verd ≈ bona — més una etiqueta amb la **puntuació de visibilitat 0–100** (esquema provisional: 0–35 vermell, 35–80 groc, 80–100 verd).
- **Solapaments:** es permeten però s'indiquen gràficament amb una trama/banda de conflicte (no el mateix vermell de visibilitat), amb feedback en temps real durant l'arrossegament i *snapping* suau a l'inici/final d'altres blocs.
- **Planificació automàtica:** botó **«Suggerir planificació»**; TerraLab3D usa la puntuació de visibilitat per omplir automàticament una proposta de nit sencera, que l'usuari pot després moure/ampliar/reduir/eliminar/substituir. No cal justificació pedagògica de per què s'ha triat cada objecte: l'usuari objectiu ja sap astronomia, n'hi ha prou de mostrar la puntuació.
- **Meridian flip dins del pla:** per a muntures equatorials, el trànsit pel meridià apareix com un **esdeveniment dins del bloc** (marca ◆ amb l'hora del trànsit). El planificador **avisa**; l'automatització mecànica del gir queda fora d'abast (vegeu idea pendent d'integració amb muntures).

## Objectiu

Construir el planificador com una extensió de la barra temporal existent, amb blocs manipulables directament i puntuació de visibilitat derivada d'`ObservableObject`.

## Tasques

- [ ] Afegir la banda de planificació sobre la barra temporal existent (sense crear una pantalla separada).
- [ ] Model de bloc: objecte, hora d'inici, hora de final, puntuació de visibilitat derivada.
- [ ] Interacció d'arrossegament: vora esquerra/dreta (redimensionar), centre (desplaçar), X (eliminar) + "Desfer".
- [ ] Codi de colors del bloc segons puntuació (vermell/groc/verd) i etiqueta numèrica 0–100.
- [ ] Detecció i renderitzat visual de solapaments (trama/banda diferenciada del vermell de visibilitat), amb feedback durant l'arrossegament i snapping als límits d'altres blocs.
- [ ] Acció «Afegir al pla» disponible des de picking, cercador, fitxa d'objecte i "El millor d'aquesta nit" (Pas 30).
- [ ] Marca visual de trànsit de meridià dins del bloc, amb l'hora corresponent.
- [ ] Botó «Suggerir planificació»: generar automàticament una proposta de nit completa a partir de la puntuació de visibilitat.
- [ ] Persistència del pla de la nit (per si es tanca i es reobre TerraLab3D).

## Criteri de sortida

Es pot construir una nit d'observació completa arrossegant blocs, amb avisos visuals de solapament i de trànsit de meridià; «Suggerir planificació» genera una proposta coherent sense intervenció manual; els canvis es desfan amb «Desfer» sense pèrdua de dades.

## Evidència obligatòria

- [ ] Vídeo curt d'arrossegament, redimensionament i eliminació/desfer d'un bloc.
- [ ] Captura amb dos blocs solapats mostrant la trama de conflicte.
- [ ] Captura d'un bloc amb marca de trànsit de meridià.
- [ ] Captura del resultat de «Suggerir planificació» per a una nit sencera.

## Fora d'abast del pas

Automatització mecànica del meridian flip i control real de muntura (idea immadura, vegeu `docs/novetats/idees-per-madurar/integracio-amb-muntures.md`).

## Prompt per a Codex

```
Implementa el Pas 31 (Planificador nocturn) descrit a
docs/novetats/idees-madures/pas31-planificador-nocturn.md sobre main, després dels Pas 28 i Pas 30.
Afegeix una banda de blocs editables directament sobre la barra temporal existent (no una pantalla
nova): arrossegament per vores/centre, X + Desfer, codi de colors per puntuació de visibilitat 0-100
(vermell/groc/verd amb llindars 35/80), detecció visual de solapaments amb trama diferenciada, marca
de trànsit de meridià, i el botó "Suggerir planificació" que omple automàticament la nit segons
puntuació de visibilitat calculada via ObservableObject (Pas 28). Connecta "Afegir al pla" des del
picking, el cercador, la fitxa d'objecte i el panell "El millor d'aquesta nit" (Pas 30).
```
