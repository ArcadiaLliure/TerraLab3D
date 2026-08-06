# Capa d’aplicació / controlador

## Propòsit

Coordinar casos d’ús, mantenir l’estat de sessió, invocar el domini i els ports, publicar esdeveniments i produir deltes d’escena. Aquesta capa no coneix Qt, Three.js ni adaptadors concrets.

## Responsabilitats

- Observador i elevació.
- Rellotge, temps real i acceleració temporal.
- Capes i dependències.
- Càrrega de catàlegs, terreny i datasets.
- Cerca, selecció, mesures i constel·lacions.
- Òptica i simulació fotogràfica.
- Cicle de vida, cancel·lació i recuperació.

## Estructura

- `commands.py`: intencions tipades entrants.
- `events.py`: resultats, progrés i errors tipats.
- `use_cases/`: coordinació separada per capacitat.
- `ports/`: dependències necessàries definides des de l’aplicació.
- `session.py`: estat autoritatiu immutable.
- `orchestration.py`: reconciliació de sessió a escena.

## Prohibicions

- No importar implementacions d’infraestructura.
- No executar algoritmes científics directament.
- No crear objectes Three.js ni ordres QPainter.
- No serialitzar buffers grans com JSON o Base64.
