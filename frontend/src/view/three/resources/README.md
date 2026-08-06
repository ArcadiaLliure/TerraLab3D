# Recursos GPU i transport binari

## Propòsit

Separar el transport de bytes, el registre de recursos Three.js, el versionat i la disposició. Els catàlegs Gaia, les malles, els índexs i les textures han de romandre residents mentre no canviï la seva versió.

## PENDENTS

- [ ] Definir el mecanisme de transport real (`ArrayBuffer` transferible, memòria compartida o fitxer mmap).
- [ ] Implementar ACK de versió i recuperació després de reinici del host.
- [ ] Mesurar bytes transferits per canvi de segon i per moviment de càmera.
