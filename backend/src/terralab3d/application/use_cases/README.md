# Casos d’ús per responsabilitat

Cada mòdul coordina una capacitat funcional i depèn exclusivament de models, serveis de domini i ports. No conté fórmules científiques ni coneix adaptadors o APIs gràfiques.

## PENDENTS

- [ ] Definir precondicions i esdeveniments de cada operació.
- [ ] Establir política de cancel·lació i last-request-wins quan pertoqui.
- [ ] Afegir proves amb ports falsos i estat immutable.
