# Capacitat `galactic` — Via Làctia i pols Planck

Aquest paquet fixa els contractes científics purs de les capes galàctiques:
marc ICRF/J2000 o galàctic, projecció, orientació equirectangular, aparença i
matriu IAU 2000 ICRS→galàctic.

La Via Làctia NASA ja és ICRF/J2000 i no passa per la transformació galàctica.
La transformació només permet mostrejar el derivat Planck, que conserva el marc
galàctic del FITS. Observador i temps no es recalculen aquí: ambdues capes
consumeixen el mateix `CelestialFrameTransform` que Gaia.

Aquest marc equatorial→horitzó local sí depèn de la latitud i del temps sideral
local (data, hora i longitud). Per tant, la inclinació de la banda i la posició
del nucli emergeixen de la geometria astronòmica: a Barcelona el nucli queda
sota l'horitzó durant una nit d'hivern i reapareix a les nits d'estiu. El
renderer no activa la capa fins que aquest marc local és vàlid.

`galactic_visibility_factor` combina contínuament brillantor del cel i Bortle.
No hi ha condicionals d’estació, hemisferi, dia/nit ni posició manual del nucli.

El paquet no importa filesystem, xarxa, workers, DOM, Three.js ni WebGL. La
descàrrega/processament pertany a infraestructura i la composició de textures,
blending, airmass i lifecycle GPU pertany al renderer.
