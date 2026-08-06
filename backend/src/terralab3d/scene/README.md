# Escena retinguda renderer-neutral

## Propòsit

Representar entitats, components, recursos persistents i operacions incrementals sense conèixer Three.js. L’escena és el contracte de presentació; no és propietària de la ciència.

## Categories de canvi

1. **Recursos estàtics:** Gaia base, textures, fonts i malles estables.
2. **Recursos ocasionals:** tiles, extensió de catàleg, canvi de superfície.
3. **Estat per tick:** cossos, atmosfera, hora sideral i visibilitat.
4. **Estat per frame:** càmera i interpolació local al frontend.

## Regles

- Un component referencia recursos per identificador i versió.
- Un delta només conté diferències respecte de la generació anterior.
- Un snapshot complet només s’utilitza per arrencada o recuperació.
- La disposició de recursos és explícita i atribuïda a un propietari.
