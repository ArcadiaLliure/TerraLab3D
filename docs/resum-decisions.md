# Resum de decisions arquitectòniques

1. **Projecte independent:** TerraLab3D no depèn del runtime ni del renderer de TerraLab.
2. **Domini científic per capacitats:** cada paquet separa models, càlculs i serveis.
3. **Aplicació per casos d’ús:** cap controlador monolític concentra totes les responsabilitats.
4. **Escena retinguda:** Three.js conserva entitats i recursos; Python publica deltes.
5. **Recursos binaris versionats:** Gaia, terreny i textures no viatgen com JSON/Base64.
6. **Càmera local:** navegar o interpolar no força càlculs científics ni retransmissions.
7. **Picking real:** la vista retorna impactes tipats i l’aplicació decideix la selecció.
8. **TerraLab com a referència:** es migren fórmules, comportaments, fixtures i dades, no la seva arquitectura acoblada.
9. **Paritat demostrable:** cada funcionalitat requereix proves, mètriques o validació visual.
10. **Català documental:** README, ADR, plans, docstrings i comentaris humans s’escriuen en català.
