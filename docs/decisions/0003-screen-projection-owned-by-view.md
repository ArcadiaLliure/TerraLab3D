# ADR 0003 — La projecció de pantalla pertany a la vista

## Decisió

El domini transforma coordenades astronòmiques i produeix direccions o geometria de món. La càmera i la projecció a píxels pertanyen a Three.js.

## Conseqüències

No es migren les projeccions QPainter com a propietat del model. Les eines reben coordenades celestes i el frontend resol la projecció interactiva.
