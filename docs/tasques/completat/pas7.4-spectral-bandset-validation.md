# Pas 7.4 — Skyglow físic — Oracle espectral fi i homologació del SpectralBandSet v1

> Estat: **completat** per al domini espectral tabulat v1 verificat. **Estat funcional:** component científic reutilitzable, sense skyglow de producte. **Origen:** planificat. **Execució:** seqüencial. **Pla canònic:** [19-pla-executable-codex.md](../../skyglow/19-pla-executable-codex.md).

## Descripció funcional

El producte encara no exposa un skyglow físic nou. L'oracle offline i el `SpectralBandSet` adaptatiu integren les corbes tabulades del domini declarat; `bandSetId` versionat i signatura d'entrada impedeixen reutilitzar resultats de bandes o assets diferents. Això no homologa cap font Black Marble del 2026 ni el transport atmosfèric.

## Fonts a consultar

- [Especificació d'algorismes](../../skyglow/01-especificacio-algorismes.md), [benchmark B0–B7](../../skyglow/07-benchmark-b0-b7.md), [glossari d'unitats](../../skyglow/12-glossari-unitats.md) i [política V1](../../skyglow/skyglow-v1-profile.json), consultats el 2026-10-18.
- [Taules CIE i checksum extern](../../evidencies/pas7.4/cie-asset-manifest.json): LED, HP, L41, V(λ) i XYZ. Assets CC BY-SA 4.0 a la biblioteca externa, consultats i verificats el 2026-10-18.
- [CIE 214:2014](https://cie.co.at/publications/effect-instrumental-bandpass-function-and-measurement-interval-spectral-quantities), fitxa pública consultada el 2026-10-18; descriu errors d'interval/banda, sense pressupost numèric aplicable al producte.
- [RSR diagnòstiques i estat de vinculació L3 de 7.3](../../evidencies/pas7.3/revisio-multisatel-lit.md), consultats el 2026-10-18.
- [Bará, Tapia i Zamorano, 2019](https://pmc.ncbi.nlm.nih.gov/articles/PMC6470928/), taules 1–2 consultades el 2026-10-18; `0,06 mag` de punt zero dels sensors estudiats, context del requisit de producte, no validació VIIRS.
- [Criteri TerraLab3D preregistrat](../../evidencies/pas7.4/criteri-preregistrat-v1.json), aprovat explícitament i congelat abans de l'avaluació.

## Objectiu

Tancar `V3` abans que el nombre de bandes entri al kernel. Fixar mètrica, domini i pressupost numèric d'error espectral amb origen justificat **abans** d'avaluar cap candidat; només llavors seleccionar i versionar el `SpectralBandSet` v1 per error contra l'oracle fi, mai per temps.

## Dependències

**Depèn de:**

- [Pas 7.3 — model de mesura DNB multisatèl·lit](pas7.3-dnb-rsr-measurement.md), completat per al contracte matemàtic i la interpretació L3. Cap RSR de 2026 s'ha homologat com a operador de font.

**En depenen:**

- [Pas 7.5 — SourceModel físic S](pas7.5-source-model-v1.md). La inferència observacional SPD/angular C/H i la seva incertesa no s'anticipen aquí ni es resolen amb S.
- [Pas 7.10 — transport espectral i gasos](../completat/pas7.10-gas-spectral-kernel.md), revalidació del pressupost de bandes en un domini físic nou.
- [Pas 7.14 — projeccions fotomètriques](../pendent/pas7.14-photometric-projections.md), revalidació amb respostes SQM/TESS/CIE.

## Codi existent a reutilitzar

- **Repositori actual:** [operador DNB analític](../../../backend/src/terralab3d/domain/light_pollution/dnb_measurement.py), [repositori RSR amb checksum](../../../backend/src/terralab3d/infrastructure/adapters/light_pollution/viirs_rsr.py), [oracle fi](../../../backend/src/terralab3d/domain/light_pollution/spectral_oracle.py), [bandset adaptatiu](../../../backend/src/terralab3d/domain/light_pollution/spectral_bandset.py) i [avaluació reproduïble](../../../tools/evaluate_spectral_bandset_step7_4.py).
- **Projectes de referència autoritzats:** TerraLab al commit auditat indicat a [normes](../../normes-arquitectura.md); no s'ha identificat cap `SpectralBandSet` homologat reutilitzable.

## Flux tècnic

Taules SPD i resposta amb SHA/procedència → interpolació/extrapolació declarades → partició pels nusos → oracle Gauss–Legendre 8/16/32 i contrast analític Decimal de 50 xifres → criteri [TL3D-SKY-V3-SPECTRAL-001](../../evidencies/pas7.4/criteri-preregistrat-v1.json) congelat → comparació individual de candidats → [bandset d'unió de nusos + Simpson](../../../backend/src/terralab3d/domain/light_pollution/spectral_bandset.py), amb `bandSetId` i `inputSignature`. El màxim és `0,01 mag` per integral positiva resolta; prop de zero es limita l'error absolut a la incertesa numèrica estimada de l'oracle. Les RSR LGS/MGS històriques es tracten només com a diagnòstiques. L'error de quadratura, de bandes i la incertesa instrumental RSR es registren per separat.

## Errors, cancel·lació i recursos

L'oracle i el bandset rebutgen corbes no finites, nusos desordenats, unitats incompatibles i dominis fora del suport quan no hi ha extrapolació declarada. El bandset rebutja una signatura d'entrada obsoleta. El script falla si falten assets externs o discrepen checksums CIE/RSR; no descarrega dades, no modifica el gestor del Pas 24 ni crea un fallback RSR. Càlcul síncron offline, sense GPU ni feina asíncrona; cancel·lació per interrupció del procés.

## Tasques

- [x] Construir una integració espectral fina independent per fixtures i projeccions de sensor.
- [x] Incorporar SPD representatives CIE i casos adversos sintètics, inclosa una línia estreta; les mescles són sintètiques amb normalització explícita.
- [x] Incorporar a l'anàlisi les famílies RSR disponibles de 7.3, amb procedència, estat diagnòstic i sensibilitat visible. Cap RSR operativa del 2026 s'ha promogut.
- [x] Preregistrar `0,01 mag`, mètrica, règim gairebé nul, domini, responsable i origen aprovat **abans** d'avaluar candidats; SHA-256 congelat a l'evidència.
- [x] Avaluar 238 integrals i tres representacions per error científic, sense temps d’execució com a criteri; comparar el màxim de cada cas.
- [x] Seleccionar i versionar `tl3d-sky-v1-knot-union-simpson-1` per al domini declarat: 238/238 PASS, amb criteri de rehomologació a 7.10/7.14.
- [x] Afegir proves golden de `bandSetId`, signatura d'assets i invalidació en canviar nusos o valors.

## Criteri de sortida

`V3` és tancada **només** per a l'operador de corbes tabulades lineals a trossos amb una SPD i fins a dues ponderacions, dins el suport de 380–780 nm i les famílies verificades. La [matriu per cas](../../evidencies/pas7.4/avaluacio-bandset-v1.json) mostra 238/238 PASS del bandset adaptatiu contra l'oracle independent amb el pressupost congelat anteriorment. Un asset o operador nou requereix revalidació; 7.10/7.14 repetiran el gate per transport i projeccions. Cap benchmark de rendiment ha decidit N.

## Proves i evidències obligatòries

- [x] Proves d'integral analítica, línia estreta, unitats i suport: [fitxer](../../../backend/tests/test_spectral_oracle_step7_4.py).
- [x] Manifest oficial, checksums i anàlisi reproduïble: [evidència](../../evidencies/pas7.4/analisi-oracle-i-bloqueig.md) i [JSON](../../evidencies/pas7.4/diagnostic-oracle-cie-rsr.json).
- [x] Regressions del backend amb l'oracle i el bandset: 205 proves superades el 2026-10-18.
- [x] Proves golden/property de bandes i invalidació, més [matriu completa](../../evidencies/pas7.4/homologacio-bandset-v1.md).
- [x] Criteri de sortida verificat en el domini numèric declarat; cap producte skyglow físic s'ha promocionat.

**Resultats verificats:** el 2026-10-18, backend `pytest`: 205/205; Ruff i Pyright sense errors als fitxers nous; CIE 5/5 checksums externs; 238 casos d'integració i contrast Q8/Q16/Q32/Decimal; bandset adaptatiu 238/238 PASS. [Detall, errors separats i límits](../../evidencies/pas7.4/homologacio-bandset-v1.md).

## Fora d'abast

- Inferència física L3→SPD/emissió angular i incertesa estructural: 7.5, 7.16 i 7.17.
- Transport atmosfèric i respostes SQM/TESS operatives: passos posteriors.
- Selecció de N per rendiment o establiment de constants «raonables» sense procedència.

## Instrucció per a Codex

En reprendre el pla, continua a 7.5 sense usar les RSR històriques com a respostes operatives del 2026. A 7.10 i 7.14, revalida el pressupost congelat per a cada operador nou; si falla, versiona el bandset i repeteix l'homologació, sense relaxació retroactiva.

## Treball pendent

Cap dins del domini numèric verificat de 7.4. La font física **definida S** correspon a [7.5](pas7.5-source-model-v1.md); la inferència Black Marble C/H continua a 7.16–7.24. Els operadors nous es revaliden a [7.10](../completat/pas7.10-gas-spectral-kernel.md) i [7.14](../pendent/pas7.14-photometric-projections.md).
