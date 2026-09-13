# Pas 38 — El viatge com a transició real (substitueix pantalles de càrrega)

> Estat: **proposta nova — idea madura, requisit transversal**
> Origen: pluja d'idees TerraLab3D, "Idea descartada" + "Requisits transversals d'experiència d'usuari".

## Resultat funcional palpable

Quan cal esperar que es preparin els recursos d'un altre cos (per exemple, en viatjar de la Terra a la Lluna), l'usuari no veu cap pantalla de càrrega: segueix viatjant realment per la simulació mentre els recursos es preparen en segon pla.

## Context i decisions preses

- **Idea descartada explícitament:** una pantalla de càrrega decorativa d'una nau aterrant a la Terra. **No es farà.**
- La solució adoptada: **el viatge és la pròpia transició.** Si es va de la Terra a la Lluna, l'usuari veu realment allunyar-se la Terra, créixer la Lluna, canviar el firmament des de la posició de l'observador, i continuar fins arribar a la destinació.
- No és una pantalla de loading disfressada de cap manera.
- Depèn conceptualment de la navegació lliure pel Sistema Solar (encara en maduració, vegeu idea pendent corresponent) però el requisit de "no pantalles de càrrega decoratives" és ja una decisió ferma i aplicable des d'ara a qualsevol transició llarga existent.

## Objectiu

Establir com a norma de producte que cap transició llarga es resolgui amb una pantalla de càrrega decorativa, i preparar la infraestructura perquè el viatge (quan existeixi la navegació espacial) serveixi de transició real.

## Tasques

- [ ] Auditar les transicions llargues actuals de TerraLab3D (canvis d'ubicació, salts temporals grans, canvis de cos) i documentar quines mostren actualment una pantalla d'espera.
- [ ] Definir el contracte tècnic: mentre es preparen recursos pesats en segon pla, la simulació ha de continuar sent interactiva i visualment coherent (encara que sigui a baixa resolució, gràcies al Pas 37).
- [ ] Eliminar/substituir qualsevol pantalla de càrrega decorativa existent per aquest patró on sigui tècnicament viable amb l'estat actual del projecte.
- [ ] Deixar documentat el requisit com a criteri d'acceptació per a la futura navegació espacial (perquè el "Go In" i el viatge lliure el compleixin per disseny des del principi).

## Criteri de sortida

Cap flux de l'aplicació mostra una pantalla de càrrega purament decorativa; les transicions llargues mantenen interactivitat visual real durant la preparació de recursos.

## Evidència obligatòria

- [ ] Inventari de transicions llargues auditades, amb l'estat "abans/després" de cadascuna.
- [ ] Vídeo d'una transició llarga real mostrant interactivitat contínua.

## Fora d'abast del pas

La navegació lliure pel Sistema Solar i el "Go In" complet (idees encara en maduració).

## Prompt per a Codex

```
Implementa el Pas 38 (El viatge com a transició real) descrit a
docs/novetats/idees-madures/pas38-viatge-com-transicio-real.md sobre main. Audita les transicions
llargues actuals de TerraLab3D i elimina qualsevol pantalla de càrrega purament decorativa,
substituint-la pel patró "la simulació continua sent interactiva mentre es preparen recursos en
segon pla" (aprofitant el Pas 37 de càrrega progressiva). Documenta aquest requisit com a criteri
d'acceptació explícit per a futures funcionalitats de navegació espacial.
```
