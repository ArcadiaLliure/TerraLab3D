# Idea pendent de madurar — Rius (hidrografia lineal)

> Estat: **per madurar**. No forma part de l'ordre executable fins que es resolguin les preguntes obertes.

> Origen: pluja d'idees TerraLab3D, dins el bloc de GeoNames/hidrografia. Es va intentar resoldre amb GeoNames i **es va descartar aquesta via explícitament** durant la mateixa conversa.

## Què s'ha decidit ja

- **GeoNames NO serveix per a rius**: només dona un punt per entitat, no segueix el traçat del curs fluvial. Vàlid per a pobles, cims, llacs i embassaments (aquests sí són puntuals); **no vàlid per a rius**.
- Es necessita **geometria vectorial lineal**: cada riu ha de venir com a `LineString`/`MultiLineString` amb identificador i nom, perquè TerraLab3D sàpiga per on discorre realment el Tajo, l'Ebre o un rierol, en lloc de tenir només una coordenada representativa.
- Això permetria etiquetar correctament: no repetir "Riu Tajo" cada pocs metres, sinó calcular un o diversos punts d'etiquetatge sobre la geometria **visible**, segons zoom i longitud del tram (un tram curt → una etiqueta centrada; centenars de km visibles → nom repetit de manera espaiada).
- Flux conceptual acordat:
  ```
  Ràster de superfície → aquí hi ha aigua/llera
  Vector hidrogràfic → aquesta llera concreta és el riu Ebre, geometria exacta, nom, categoria (riu/rierol/canal)
  ```
- Si en el futur hi ha carreteres vectorials en altres contextos del projecte, es podria reaprofitar bona part de la infraestructura: càrrega per AOI, simplificació per LOD, retallat (clipping), etiquetes sobre línies i cache espacial.
- **Llacs i embassaments** (a diferència dels rius) **sí** es poden representar com a punt amb GeoNames, igual que pobles i cims — això podria incorporar-se com una ampliació del [pas 37](../pendent/pas37-geonames-empaquetat.md) sense esperar la solució de rius.

## Per què encara no és una fase concreta

Falta, com a mínim:
- triar una **font vectorial mundial d'hidrografia amb llicència d'ús comercial** (explícitament pendent de buscar);
- decidir el motor de simplificació/LOD per a geometria lineal llarga;
- decidir l'algorisme de posicionament d'etiquetes sobre un tram visible.

## Preguntes obertes

1. Quina font vectorial d'hidrografia mundial és lliure per a ús comercial?
2. Es reaprofita la mateixa infraestructura de carreteres vectorials (si existeix o s'arriba a construir) o es fa un subsistema propi?
3. Com es calcula el punt (o punts) d'etiquetatge òptim segons el tram visible?

## Relació amb el pla i altres idees

Cap directa; podria beneficiar-se de la infraestructura de carreteres vectorials si el projecte n'incorpora en el futur. Llacs/embassaments poden seguir el patró del [pas 37](../pendent/pas37-geonames-empaquetat.md) sense esperar aquesta idea.
