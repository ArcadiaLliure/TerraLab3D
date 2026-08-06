# Ports propietat de l’aplicació

Els ports descriuen allò que els casos d’ús necessiten de l’exterior: catàlegs, efemèrides, elevacions, clima, datasets, persistència, transport binari, tasques i telemetria.

Les signatures han d’utilitzar DTO tipats. Les implementacions concretes viuen a `infrastructure/adapters`.

## PENDENTS

- [ ] Eliminar qualsevol retorn `object` residual abans d’implementar un adaptador.
- [ ] Documentar lifecycle, cancel·lació i errors de cada port.
- [ ] Associar cada port a una o més files de la matriu de paritat.
