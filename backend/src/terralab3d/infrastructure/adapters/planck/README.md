# Adaptador d’infraestructura `planck`

`PlanckDustAdapter` implementa el port `ResourcePostProcessor`. Rep el FITS
HEALPix oficial `COM_CompMap_Dust-GNILC-Model-Opacity_2048_R2.01.fits`, valida
`NSIDE`, `ORDERING`, `COORDSYS=G` i el camp `TAU353`, i genera una cache PNG
equirectangular local.

Convenció del derivat:

```text
u=0     -> l=0°
u creix -> longitud galàctica cap a la dreta
v=0     -> b=+90°
v=1     -> b=-90°
```

El FITS font no es modifica ni se substitueix. El percentil de visualització,
dimensions i metadades de conversió queden registrats amb la instal·lació. La
conversió s’executa fora del bucle de render i el resultat només s’aplica si el
job continua vigent.

Dependències concretes: `astropy`, `hpgeom`, `numpy` i `Pillow`. No hi ha cap
dependència de UI o Three.js.
