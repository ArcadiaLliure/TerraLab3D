# Adaptador de vista Three.js

## Propòsit

Mantenir una escena 3D persistent, aplicar deltes, conservar recursos GPU, renderitzar i retornar picking real.

## Responsabilitats

- Crear i destruir renderer, escena i càmera.
- Aplicar canvis incrementals.
- Interpolar càmera i transformacions visuals.
- Gestionar buffers, textures, materials i shaders.
- Fer picking i retornar identificadors tipats.

## Prohibicions

- No executar astronomia, fotometria, selecció de catàlegs ni mostreig DEM.
- No reconstruir l’escena completa quan canvia el temps o la càmera.
