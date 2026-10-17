# Pas 7.1 — Skyglow físic: contracte científic v1, dades i política d'acceptació

> **Estat:** completat (contracte documental). **Estat funcional:** skyglow físic no implementat. **Origen:** planificat. **Abast vigent:** dades, decisions inicials i política d'acceptació prèvies a 7.2 i 7.3. **Pla canònic:** [pla executable](../../skyglow/19-pla-executable-codex.md).

## Descripció funcional

No hi ha encara una capacitat nova d'usuari. El cel visual del [pas 7](pas7.md) continua essent el comportament observable; el skyglow físic encara no és operatiu.

## Fonts a consultar

- [Fitxa NASA LAADS VNP46A2.002](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2), producte/release i qualitat; consultada el 2026-10-17.
- [Guia Black Marble Collection 2](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf), capes, unitats i flags; consultada el 2026-10-17.
- [Especificació de fitxer v2.0.4](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VNP46A2_v2.0.fs), atributs i procedència; consultada el 2026-10-17.
- [Política LAADS](https://ladsweb.modaps.eosdis.nasa.gov/learn), ús i redistribució; consultada el 2026-10-17.
- [Coesfeld et al. 2020](https://doi.org/10.3390/s20113287), punt zero en dades DNB; consultat el 2026-10-17, sense transferir la seva correcció a VNP46A2.
- [Decisions obertes](../../skyglow/18-decisions-obertes.md), [dades i llicències](../../skyglow/10-datasets-llicencies.md) i [benchmark B0–B7](../../skyglow/07-benchmark-b0-b7.md), llegits el 2026-10-17.

## Objectiu

Versionar el perfil científic amb producte VNP46, unitats, qualitat, política temporal, radiància baixa, oracle, límits d'abast i **política preregistrada d'acceptació V1**. Els valors numèrics es fixen al primer gate que els aplica, amb evidència pròpia; 7.1 deixa resoltes les decisions necessàries per iniciar 7.2 i 7.3.

## Dependències

**Depèn de:**

- [Pas 7 — cel i atmosfera visuals](pas7.md).
- [Pas 22.5 — normalització documental](pas22.5-normalitzacio-documental.md).
- [Pas 23 — constel·lacions](pas23-constellacions.md).

**En depenen:**

- [Pas 7.2 — adaptador VNP46](pas7.2-vnp46-observation-adapter.md), i transitivament 7.3–7.28.

## Codi existent a reutilitzar

- **Repositori actual:** [domini de contaminació lumínica](../../../backend/src/terralab3d/domain/light_pollution/) només per distingir el llegat empíric; [esquemes del bridge](../../../contracts/schemas/) per a convencions de versionat. Cap adaptador VNP46 funcional verificat.
- **Projectes de referència autoritzats:** cap codi extern copiat. Les fonts NASA es consulten com a documentació i dades amb la política indicada.

## Flux tècnic

Font oficial → [auditoria de fonts](../../evidencies/pas7.1/auditoria-fonts.md) → [manifest `skyglow-v1-profile`](../../skyglow/skyglow-v1-profile.json) → validació del contracte i de la política → pas 7.2. El manifest congela `VNP46A2.002`, processament estàndard, la capa diària `DNB_BRDF-Corrected_NTL` sense ompliment de buits, unitat `nW cm⁻² sr⁻¹`, QA 0 per a mostres candidates i 1–5 per a diagnòstics. Els atributs del grànul són autoritatius; una discrepància es posa en quarantena.

La política `LOW-RAD` conserva el valor cru: fill i negatius no entren a inferència; zero no prova emissió nul·la; els positius petits no reben un llindar de detecció inventat. `DNB-2017` prohibeix una correcció universal i deixa les comparacions febles pre/post-2017 sense homologació producte-específica. El model de mesura DNB continua identificat com a `BAND_INTEGRATED`; la seva implementació i la RSR real corresponen a 7.3.

`S1` és `SG-REF` propi del skyglow, sense dependència de 7.65. `F5` requereix contrast offline amb un oracle de dispersió d'ordre superior abans d'afirmar el biaix single-scattering. `F7` fixa radi adaptatiu per cota d'error. `F6` queda fora de v1 mentre no s'exposi una magnitud perceptiva nocturna única.

`V1` congela la regla, no els valors: cap llindar PASS/FAIL s'ajusta després de veure el resultat del candidat que ha de validar. Cada valor requereix mètrica, unitat, domini, categoria d'origen, referència verificable, justificació, propietari, moment de congelació i revisió del perfil. Els orígens admesos són literatura o font metrològica, incertesa demostrada d'un oracle, requisit de producte aprovat o criteri de convergència justificat científicament. Una constant només «raonable» queda prohibida. L'absència d'un valor bloqueja exclusivament el primer pas que necessita aplicar-ne el PASS/FAIL.

El pressupost espectral es preregistra a 7.4 abans de seleccionar el `SpectralBandSet`; la tolerància zenital runtime↔SG-REF, a 7.12 abans de la comparació decisòria, amb convergència/incertesa de 7.6; els criteris empírics, a 7.17 abans d'avaluar el conjunt reservat, incorporant incerteses instrumental, de dades i del model; els SLO aprovats de TerraLab3D, a 7.22 abans de decidir LUT/precomputació/FFT. El pas 7.28 només consumeix criteris congelats.

## Errors, cancel·lació i recursos

Un manifest sense política V1 preregistrada no supera 7.1; els llindars encara nuls són explícits i bloquejaran el primer gate que els apliqui. Els grànuls incompatibles, sense qualitat o amb unitats desconegudes es posaran en quarantena en 7.2; no s'aplicarà clipping ni correcció de stray light duplicada. Aquest pas no descarrega dades, no usa GPU i no té operacions llargues que necessitin cancel·lació.

## Tasques

- [x] Fixar producte/release, política temporal, llicència, unitats i flags autoritatius (`DATA-VNP46`).
- [x] Fixar `LOW-RAD` i `DNB-2017` sense clipping ni correcció implícita.
- [x] Preregistrar la política `V1`, els orígens obligatoris, la prohibició d'ajust retrospectiu i la ubicació de cada gate numèric.
- [x] Decidir `S1=SG-REF` i `F5` com a comparació offline amb un oracle d'ordre superior; 7.6 implementarà i validarà l'oracle.
- [x] Fixar `F7` per cota d'error i `F6` com a no bloquejant per a v1.
- [x] Crear manifest versionat llegible pels passos posteriors, amb `acceptanceProfile.status=policy_preregistered` i valors pendents als seus gates.

## Criteri de sortida

El manifest ha de tenir `acceptanceProfile.status=policy_preregistered` i les decisions `DATA-VNP46`, `LOW-RAD`, `DNB-2017`, `S1`, `F5`, `F7` i abast `F6` suficients per a 7.2 i 7.3. Els valors V1 necessiten origen i valor abans del primer gate que els apliqui, no a 7.1. Aquest criteri està satisfet documentalment; [7.2](pas7.2-vnp46-observation-adapter.md) també s'ha completat posteriorment.

## Proves i evidències obligatòries

- [x] Comprovar que el manifest JSON es pot llegir i que reflecteix la política preregistrada; veure [validació reproduïble](../../evidencies/pas7.1/validacio-contracte.txt).
- [x] Verificar en fonts oficials producte, unitats, qualitat i drets; veure [auditoria de fonts](../../evidencies/pas7.1/auditoria-fonts.md).
- [x] Verificar l'estructura de la política, els gates i l'absència de llindars inventats; no s'han executat comparacions PASS/FAIL numèriques.
- [x] Verificar el criteri de sortida i traslladar el pas a `completat/`.

**Resultats verificats:** consulta documental i validació JSON del 2026-10-17; [auditoria de fonts](../../evidencies/pas7.1/auditoria-fonts.md) i [validació del contracte](../../evidencies/pas7.1/validacio-contracte.txt). No s'ha descarregat un grànul, ni executat el kernel ni cap benchmark científic.

## Fora d'abast

Adaptador HDF5 (7.2), RSR/normalització DNB (7.3), bandes espectrals (7.4), inferència d'emissió (7.5) i transport (7.6+). No fixar un llindar TerraLab3D a partir de l'objectiu de detecció de VNP46.

## Instrucció per a Codex

Continua a 7.2 amb el contracte de dades i la política V1 congelats. Registra els valors numèrics només als gates designats, abans dels seus resultats decisoris, amb font i propietari; si manca justificació, bloqueja aquell gate sense retrobloquejar 7.1–7.3.

## Treball pendent

Cap tasca pendent del Pas 7.1. Els valors PASS/FAIL pendents pertanyen als gates 7.4, 7.12, 7.17 i 7.22; els criteris particulars de passos intermedis es preregistraran abans de la seva primera aplicació segons la mateixa política. El pas 7.28 els consumirà sense modificar-los.
