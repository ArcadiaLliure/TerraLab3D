# Documentació de TerraLab3D

La documentació es divideix entre normes transversals i passos funcionals. La classificació es basa en l’estat observable del repositori, les proves i els informes de validació, no en les caselles històriques del pla original.

- [Normes d’arquitectura i execució](normes_arquitectura.md)

## Passos completats

- [Pas 1 — Entorn 3D executable, càmera 360° i bridge Python ↔ Three.js](completat/pas1.md)
- [Pas 2 — Ubicació geogràfica de l’observador i orientació local](completat/pas2.md)
- [Pas 3 — Rellotge de simulació, temps sideral i moviment visible de la volta celeste](completat/pas3.md)
- [Pas 3.5 — Càmera translacional, mode caminar i mode avió](completat/pas3.5.md)
- [Pas 4 — Grid celeste, brúixola, etiquetes i HUD astronòmic](completat/pas4.md)
- [Pas 5 — Camp estel·lar Gaia real, fallback i buffers persistents](completat/pas5.md)
- [Pas 6 — Sistema de picking estel·lar precís](completat/pas6.md)
- [Pas 7 — Cel diürn/nocturn, crepuscle, atmosfera visual, contaminació lumínica, Bortle i magnitud límit](completat/pas7.md)
- [Pas 8 — Sol, Lluna i planetes amb posicions i aparença reals](completat/pas8.md)
- [Pas 8.5 — Superfície lunar LRO/LOLA, orientació física i libració real](completat/pas8.5.md)
- [Pas 8.6 — Planetes texturitzats, orientació física, anells i tots els satèl·lits naturals planetaris](completat/pas8.6.md)
- [Pas 8.7 — Il·luminació física de l’escena: Sol, Lluna, cel i materials PBR](completat/pas8.7.md)
- [Pas 9 — Eclipsis, ocultacions, separacions i trajectòries](completat/pas9.md)
- [Pas 10 — Via Làctia i pols galàctica Planck](completat/pas10.md)
- [Pas 11 — Cel profund NGC/IC](completat/pas11.md)
- [Pas 12 — Cerca astronòmica, focus i seguiment](completat/pas12.md)
- [Pas 13 — Picking real, hover, selecció i inspecció d’objectes](completat/pas13.md)
- [Pas 14 — Traces circumpolars i exposició temporal](completat/pas14.md)
- [Pas 15 — Elevació real, perfil d’horitzó i oclusió celeste](completat/pas15.md)
- [Pas 16 — Terreny tridimensional retingut, tiles, LOD i picking de superfície](completat/pas16.md)

## Passos parcialment implementats

- [Pas 23 — Capes, datasets, assistent de dades, preferències i feedback](pendent/pas23.md)

## Passos pendents

~~- [Pas 17 — Ortofoto, cobertura categòrica i estils de superfície](pendent/pas17.md)~~ (NO S'INCORPORA A TERRALAB3D)
- [Pas 18 — Meteorologia real, fallback i efectes atmosfèrics](pendent/pas18.md) (AJORNAT)
- [Pas 19 — Telescopi, ocular, sensors i enquadrament instrumental](pendent/pas19.md)
- [Pas 20 — Simulació fotogràfica, senyal, soroll i llarga exposició](pendent/pas20.md)
- [Pas 21 — Regla, quadrat, rectangle i cercle amb edició](pendent/pas21.md)
- [Pas 22 — Constel·lacions editables amb snapping, grups i persistència](pendent/pas22.md)
- [Pas 24 — Homologació integral, recuperació, rendiment i independència de producte](pendent/pas24.md)

## Evidències i dades de referència

- `manifests/`: manifests reproduïbles de recursos científics.
- `reference-scenarios/`: escenaris i captures de comparació visual.
- [Taxonomia TLST](TLST.md)
- [Vertical TLST](TLST-vertical.md)
- [Gestor de refinaments TLST](tlst-refinement-manager.md)
