# Idees per madurar

> Estat de tots els dossiers d'aquest directori: **per madurar**.

Aquestes idees no formen part de l'ordre executable dels passos 17–38. Conserven context i preguntes útils, però encara falta una decisió que canviaria materialment la implementació. Codex no les ha d'executar quan se li demani continuar el [pla de millores](../README.md).

| Dossier | Decisió pendent principal | Condició per considerar-lo madur | Pas madur relacionat |
|---|---|---|---|
| [Base de dades de càmeres/sensors](base-de-dades-camares-sensors.md) | Font, llicència, manteniment i esquema del catàleg. | Dataset redistribuïble i política de versió/actualització tancats. | [19 — modes d'observació instrumental](../pendent/pas19-modes-optics.md) |
| [Cartografia lunar](cartografia-lunar.md) | Abast de capes, font USGS i UX de selecció. | Fonts/llicències, resolucions i resultat funcional prioritzat. | [25 — gestor de capes](../pendent/pas25-gestor-capes.md) |
| [Cinturó de Kuiper i núvol d'Oort](cinturo-kuiper-nuvol-oort.md) | Representació científica vs. divulgativa i escala. | Model de dades, incertesa i interacció observables definits. | [26 — recursos del Sistema Solar](../pendent/pas26-recursos-sistema-solar.md) |
| [Cometes](cometes.md) | Catàleg, actualització orbital, esdeveniments i model observable. | Font/versionat, propagació, UI i toleràncies resolts. | [22 — observables](../pendent/pas22-trajectories-visibilitat.md), [32 — efemèrides](../pendent/pas32-motor-efemerides.md) |
| [“Go In” a superfícies planetàries](go-in-superficies-planetaries.md) | Quins cossos, dades, LOD i transició local/global. | Primer cos pilot, dataset i contracte de streaming decidits. | [17 — superfície progressiva](../completat/pas17-superficie-progressiva.md), [38 — transicions](../pendent/pas38-homologacio-final.md) |
| [Integració amb muntures](integracio-amb-muntures.md) | Protocols/maquinari suportats i límits de seguretat. | Matriu ASCOM/Alpaca/INDI, simulador, interlocks i recuperació tancats. | [30 — plate solving](../pendent/pas30-plate-solving.md), [31 — planificador](../pendent/pas31-millor-nit-planificador.md) |
| [Meteorologia](meteorologia.md) | Finalitat de producte, autoritat temporal, proveïdor, fallback i fidelitat visual. | Cas d'ús, fonts/llicències, relació amb el temps simulat i pressupost gràfic aprovats. | [7 — atmosfera](../completat/pas7.md), [25 — gestor de capes](../pendent/pas25-gestor-capes.md) |
| [Nau 3D i HUD](nau-3d-tercera-persona.md) | Física, escala, controls, col·lisions i finalitat de producte. | Model de navegació i experiència observable aprovats. | [38 — transicions](../pendent/pas38-homologacio-final.md) |
| [Navegació lliure pel Sistema Solar](navegacio-lliure-sistema-solar.md) | Navegació física, escala, temps, referencials i precisió. | Contracte de simulació i controls validat amb un recorregut pilot. | [26 — vista solar](../pendent/pas26-recursos-sistema-solar.md) |
| [Representació del Sol](representacio-del-sol.md) | Fonts, capes, actualització i nivell de fidelitat. | Dataset redistribuïble i visualització científica mínima fixats. | [26 — recursos del Sistema Solar](../pendent/pas26-recursos-sistema-solar.md) |
| [Rius](rius.md) | Font vectorial, hidrografia, simplificació i estil. | Proveïdor/llicència, format, LOD i criteri visual resolts. | [29 — superfície semàntica](../pendent/pas29-superficie-semantica.md), [37 — nomenclàtor](../pendent/pas37-geonames-empaquetat.md) |
| [Satèl·lits de Júpiter](satellits-de-jupiter.md) | Tipus d'esdeveniment, prioritat i ubicació UI. | Catàleg de fenòmens, càlcul, toleràncies i UX acordats. | [26 — vista solar](../pendent/pas26-recursos-sistema-solar.md), [32 — efemèrides](../pendent/pas32-motor-efemerides.md) |
| [Transició terreny → planeta esfèric](transicio-terreny-planeta-esferic.md) | Representació global, LOD i continuïtat entre sistemes. | Prototip amb referencials, dades i pressupost sense salts acceptat. | [17 — superfície progressiva](../completat/pas17-superficie-progressiva.md), [38 — transicions](../pendent/pas38-homologacio-final.md) |

## Protocol de promoció

Una idea només pot entrar al backlog madur quan:

1. totes les preguntes obertes que alteren arquitectura, dades o UX tenen una decisió;
2. resultat funcional, dependències, dades/llicències, errors, cancel·lació, recursos i fora d'abast són explícits;
3. s'ha inspeccionat el codi real i s'han identificat fitxers reutilitzables;
4. proves, criteri de sortida i evidències són verificables;
5. se li assigna un pas posterior al 38, s'afegeix al [README del pla](../README.md) i el dossier es converteix en l'especificació executable corresponent.
