# Idea pendent de madurar — Integració amb muntures (ASCOM/Alpaca/INDI) i meridian flip automàtic

> Origen: pluja d'idees TerraLab3D, blocs "Integración futura con monturas" i "Gestión avanzada del meridian flip". Marcat explícitament com a **idea immadura, aparcada deliberadament**.

## Què s'ha decidit ja

- TerraLab3D **no crearia drivers propis**: es comportaria com a **client** de protocols existents.
- Tecnologies possibles: **ASCOM** (avui recomana usar-se via **Alpaca**, HTTP i més modern) o **INDI**.
- Evolució per capes, en aquest ordre:
  1. simulació (calcular trajectòries i plans, sense controlar res) — **això ja existeix / és el Pas 31**;
  2. mode només lectura: llegir on apunta la muntura real i reflectir-ho a TerraLab3D;
  3. enviar un GoTo senzill a un objecte des de TerraLab3D;
  4. fer captura;
  5. plate solving de la captura obtinguda (reaprofitant el Pas 27);
  6. corregir l'apuntat automàticament a partir del resultat del plate solving;
  7. finalment, automatitzar sessions completes (a l'estil ASIAIR/NINA).
- **Punt important aclarit durant la conversa:** TerraLab3D no té cap limitació conceptual per fer això —eines com ASIAIR ho fan perquè estan connectades a la muntura i en coneixen els ajustos. La diferència és només fins a quin punt es vol integrar amb el maquinari, no una limitació de disseny.
- **Meridian flip:** la part astronòmica (calcular quan es produeix el trànsit pel meridià local) ja es pot calcular i ja està resolta a nivell d'avís dins el planificador (Pas 31, "marca ◆" i avís). L'**automatització mecànica** del gir real de la muntura depèn de la configuració de cada muntura concreta i, eventualment, d'aquesta mateixa integració amb maquinari — per tant queda **fora d'abast fins que hi hagi integració de muntura**.

## Per què encara no és una fase concreta

Falta decidir, com a mínim:
- si es prioritza Alpaca sobre ASCOM/INDI per simplicitat d'implementació (HTTP vs. protocols natius);
- l'abast de la v1 d'integració (només lectura? GoTo bàsic? correcció automàtica completa?);
- els límits de seguretat que cal imposar abans de permetre que TerraLab3D enviï comandes a maquinari real (confirmacions, límits de moviment, etc.).

## Preguntes obertes

1. Alpaca, ASCOM natiu o INDI: amb quin es comença?
2. Quina és la primera capa realista a implementar (probablement només-lectura, capa 2 de la llista)?
3. Quins límits de seguretat calen abans de permetre enviar un GoTo real a maquinari?

## Relació amb altres idees pendents

Plate solving (Pas 27, ja madur) — és la peça que fa útil la correcció d'apuntat un cop hi hagi integració de muntura. Planificador nocturn (Pas 31, ja madur) — ja cobreix l'avís de meridian flip; només l'automatització mecànica queda aquí.
