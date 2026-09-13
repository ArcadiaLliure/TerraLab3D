# Novetats TerraLab3D — pla de treball

Aquest bloc recull el pla de treball detallat sorgit de la pluja d'idees sobre
noves funcionalitats de TerraLab3D (converses del 2 al 11 de setembre de
2026), aplicat a partir de la branca `main`. Segueix el mateix format que
`docs/completat/` i `docs/pendent/` (un document per pas, amb objectiu,
tasques, criteri de sortida i evidència obligatòria), però es manté en una
carpeta pròpia perquè és un pla **nou i independent** del backlog original
(Pas 1–24): la numeració continua a partir de **Pas 25** per no col·lidir.

## Estructura

- **`idees-madures/`** — 25 fases (Pas 25 a Pas 49), cadascuna una
  funcionalitat prou definida a la pluja d'idees per convertir-se
  directament en una tasca d'implementació, amb el mateix nivell de detall
  que un pas del pla original.
- **`idees-per-madurar/`** — 12 dossiers de definició (no fases de tasques)
  per a idees que van sortir a la pluja d'idees però que encara necessiten
  decisions de disseny, investigació de dades/llicències o prioritat abans
  de poder-se convertir en un pas. Cada dossier documenta què ja s'ha
  decidit, per què encara no és una fase, i quines preguntes cal resoldre.

## Ordre recomanat d'implementació (idees madures)

El pla es pot executar per blocs funcionals, en gran part independents entre
si; dins de cada bloc, respecteu l'ordre numèric per les dependències
indicades a cada document:

1. **Observació i astrofotografia** — Pas 25 a 27
   (modes òptics → simulador fotogràfic → plate solving)
2. **Trajectòries, planificació i efemèrides** — Pas 28 a 36
   (objecte observable → constel·lacions / "el millor d'aquesta nit" /
   planificador → motor d'efemèrides → cercador multipestanya →
   previsualitzacions → eclipsis → esdeveniments propis)
3. **Requisits transversals d'experiència d'usuari** — Pas 37 i 38
   (càrrega progressiva de terreny; el viatge com a transició real).
   Es poden abordar en paral·lel amb qualsevol altre bloc.
4. **Nou Gestor de Capes** — Pas 39 a 46
   (esquelet Cel/Terra → Sistema Solar → Espai profund → sistema de
   descàrregues → Elevació → Superfície → refinament ràster → TLST)
5. **Nomenclàtor de terreny (GeoNames)** — Pas 47 a 49
   (assentaments → cims → distribució com a dada base empaquetada)

## Idees pendents de madurar (no bloquegen el pla anterior)

| Dossier | Bloqueja |
|---|---|
| `go-in-superficies-planetaries.md` | Requereix backend de malla 3D nou |
| `navegacio-lliure-sistema-solar.md` | Requereix `transicio-terreny-planeta-esferic.md` |
| `nau-3d-tercera-persona.md` | Depèn de `navegacio-lliure-sistema-solar.md` |
| `transicio-terreny-planeta-esferic.md` | Bloquejant per a Go In i navegació lliure |
| `representacio-del-sol.md` | Depèn de navegació lliure |
| `satellits-de-jupiter.md` | Podria resoldre's via Pas 32 un cop decidida la UI |
| `cometes.md` | Aparcat expressament; s'integraria via Pas 28/32 |
| `integracio-amb-muntures.md` | Aparcat expressament; útil un cop hi hagi Pas 27 |
| `cinturo-kuiper-nuvol-oort.md` | Sense cap decisió; la menys madura de totes |
| `rius.md` | Falta trobar font vectorial amb llicència comercial |
| `cartografia-lunar.md` | Falta investigar productes USGS |
| `base-de-dades-camares-sensors.md` | Millora opcional, no bloqueja el Pas 26 |

## Prompt mestre per a Codex (visió de conjunt)

Cada pas madur inclou el seu propi prompt llest per enganxar a Codex. Per
començar una sessió de treball sobre tot el bloc, es pot fer servir aquest
prompt d'orientació general:

```
Estàs treballant sobre la branca main de TerraLab3D. Hi ha un pla de treball
nou a docs/novetats/, complementari al backlog existent a docs/completat/ i
docs/pendent/. Llegeix primer docs/novetats/README.md per entendre l'ordre
recomanat de blocs, i docs/normes_arquitectura.md per a les convencions del
projecte. Cada document a docs/novetats/idees-madures/pasNN-*.md conté:
context i decisions ja preses a la pluja d'idees original, una llista de
tasques, un criteri de sortida i l'evidència obligatòria a aportar. Implementa
els passos en l'ordre indicat pel README (per blocs, respectant les
dependències citades a cada document), un pas complet i verificat abans de
passar al següent. No inventis decisions de disseny que no apareguin al
document del pas: si et falta un detall, consulta si existeix un dossier
relacionat a docs/novetats/idees-per-madurar/ abans de suposar res. No
toquis els fitxers de docs/novetats/idees-per-madurar/: són idees encara
sense prou definició i no s'han d'implementar fins que es converteixin en un
pas dins idees-madures/.
```

## Font

Aquest pla es basa íntegrament en la transcripció d'una conversa de
brainstorming (ChatGPT, converses del 2 al 11 de setembre de 2026, exportada
per l'usuari) sobre noves funcionalitats per fer TerraLab3D més
comercialitzable. Cap decisió reflectida en aquests documents s'ha inventat;
tot prové de compromisos explícits presos durant aquella conversa.
