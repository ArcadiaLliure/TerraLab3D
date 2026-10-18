# Validació de simulació espectral condicionada — Pas 7.5.1

Data: 2026-10-18. Base inspeccionada: `b7cfaba37da9b08ef265b350243e92e9e902f674`, amb els commits recents 7.3–7.5 i la política posterior S/C/H. Skill `plan` aplicada. No s’ha implementat SG-REF ni transport atmosfèric.

## Resultat científic executable

El grànul real `VJ146A2.A2026256.h18v04.002.2026264085938.h5`, SHA-256 local `2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762`, alimenta ambdues modalitats. Píxel de Barcelona: fila 2067, columna 520, 41,3875° N, 2,1666667° E; `139,34158325195312 nW cm^-2 sr^-1`, QA 0, `QF_Cloud_Mask=34`, neu 0. El lector comprova SHA, nom, dia exacte, plataforma/DOI/versió, unitats i capa corregida no gap-filled. El píxel (0,0) fill es preserva i no genera font.

[Sortida realista completa](barcelona-realista.json), [sortida Kelvin 3.000 K](barcelona-kelvin-3000.json) i [sensibilitat MGS/LGS, SPD i angles](sensibilitat-escenaris.json). Cada modalitat genera sis fonts C: tres mescles base alternatives × dos patrons angulars. Les fonts comparteixen `SourceModel` amb S, porten `sourceMode=CONDITIONAL_L3` i només escala relativa. Es rebutja l’atribució directa de watts a C.

L’ancoratge és una convenció paramètrica explícita de radiància L3 relativa, àrea i direcció zenital hipotètica. La font base, l’observació original, la intervenció SPD i la magnitud conservada queden separades. No s’inverteixen les correccions BRDF/atmosfera de NASA; no hi ha conversió universal L3→potència. Els percentatges són de flux radiant d’escenaris definits, no estadístiques urbanes, recompte de làmpades ni probabilitats.

## Referència RSR i límits

La consulta actual dels catàlegs oficials [NOAA-20](https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php), [NOAA-21](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php) i [SNPP](https://ncc.nesdis.noaa.gov/VIIRS/VIIRSSpectralResponseFunctions.php), juntament amb els README originals dels ZIP instal·lats, confirma la millor referència pública verificada per a la primera connexió: J1 DAWG at-launch V2.1 (novembre 2016), MGS band-average heretada V1, amb LGS fusionada com a contrast. Es preserven membre, hash del ZIP/membre/taula i mode. L’interval instrumental del registre continua acabant el 2017-11-18: no s’ha allargat a 2026.

El README J1 diferencia MGS SpMA i LGS fusionada amb filtre de densitat neutra. El README J2 V2 de juliol 2019 diferencia LGS/MGS GLAMR i recomana MGS com a proxy d’HGS no mesurada. No es trasllada aquest proxy automàticament a J1 ni se substitueix una mitjana de banda per un detector particular. La [validació NASA](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html) aporta evidència d’estabilitat de forma NOAA-20/21 i calibratge mensual; no certifica la correspondència nocturna L3/HGS del píxel. La [guia C2](https://landweb.modaps.eosdis.nasa.gov/data/userguide/BlackMarbleUserGuide_Collection2.0_20241203.pdf) distingeix TOA i L3 corregit.

`resolve_reference` conserva la identitat i les dates i permet l’ús condicionat del mateix sensor/guany; `resolve` conserva el contracte operatiu estricte. Cap font es promou a H. No s’ha verificat una parella històrica Black Marble–RSR amb millor cadena nocturna L3; les referències SNPP antigues es preserven com a contrast. Si MGS no existeix, LGS requereix petició explícita; sense referència verificable del mateix sensor no es fabrica un fallback.

Incerteses de mapping HGS/L3, composició urbana, emissió angular, extrapolació fora del suport i escala absoluta: **no quantificades**. Les alternatives no són intervals de confiança ni sigmes.

## Biblioteca i colorimetria

[Biblioteca de 42 SPD](biblioteca-espectral.json), originals CIE empaquetats amb [manifest verificat](../../../backend/src/terralab3d/infrastructure/catalogs/spectra/manifest.json), metadades, URL, DOI, llicència CC BY-SA 4.0, MD5 publicat i SHA-256. CSV i metadades es comproven en carregar-los. LED B1–B5/BH1/RGB1/V1/V2, HP1–HP5, 27 fluorescents i L41. No s’han fabricat taules absents de mercuri pur, LPS o LED ambre 1.800 K.

CCT calculada dels extrems B1/B5: aproximadament 2.733,4 i 6.597,2 K. Rang UI conservador 2.800–6.500 K. Les SPD intermèdies són mescles radiants convexes de LED de fòsfor adjacents, resolent la CCT resultant en CIE 1960 uv amb CMF CIE 1931 2°. Error numèric objectiu inferior a 0,1 K; control independent amb quadratura densa i cerca en graella del locus. Planck només s’utilitza per al locus de referència, mai per generar una SPD LED.

Es conserven nusos i pics tabulats; les taules HP de 5 nm no adquireixen estructura espectral no publicada. L’energia fora del suport es desconeix; els totals són del domini tabulat. La CCT del sodi LPS es declara no significativa per tecnologia, encara que matemàticament existeixi un punt proper al locus.

Exemple de sensibilitat amb mescla base LED dominant, perfil uniforme i flux fotòpic conservat:

| Intervenció | CCT efectiva | Ràtio DNB MGS | Ràtio DNB LGS |
|---|---:|---:|---:|
| 3.000 K | 2.999,927 K | 1,040634 | 1,037531 |
| 6.500 K | 6.500,064 K | 0,792309 | 0,785388 |

Això és resposta de referència relativa sota hipòtesis, no una nova radiància satel·lital certificada ni brillantor del cel. Demostra que conservar flux fotòpic no conserva DNB. Les proves independents verifiquen també potència radiant, resposta DNB i escala relativa conservades.

El pressupost 0,01 mag i 238/238 de 7.4 no s’han modificat ni estès automàticament a transport nou. 7.10/7.14 revalidaran SPD, interpolacions, mescles i operadors futurs.

## UI i bridge

[Verificació UI](verificacio-ui.json), [captura Kelvin](control-kelvins.png) i [captura realista](simulacio-realista.png) obtingudes amb l’entrypoint real `python -m terralab3d` i `node frontend/tools/verify_skyglow_step7_5_1.mjs`. Navegador Chromium headless, 1280×1000, tacte activat; captures inspeccionades visualment. Estat de prova separat dins el repositori; els recursos opcionals absents utilitzen el fallback visual existent.

Selector realista/K al panell existent; etiqueta superior, lliscant horitzontal, mínim a l’esquerra, màxim a la dreta, valor actual i «Exemple: ...» inferiors comprovats. Teclat Inici/Fi/fletxes, ratolí i tacte activen comandes reals. Les respostes WebSocket de Python contenen configuració, hash, revisió, SPD i CCT efectiva. La família es conserva en moure el cursor. Les respostes velles no sobreescriuen una selecció pendent; la prova de canvis ràpids comprova latest-wins.

`calculationStatus=transport_pending`, `skyRadiance=null`; el renderer no consumeix la configuració espectral per alterar RGB. Les dades Black Marble/RSR del snapshot de configuració són null fins a seleccionar observacions a la futura ruta de producte; les fonts offline sí que les conserven. La connexió a radiància/render continua explícitament pendent i obligatòria a 7.25–7.27.

## Comprovacions executades

- `python -m pytest backend/tests -q -p no:cacheprovider --basetemp=.runtime-skyglow-regression-verified --tb=short`: **247 passed**, amb assets NOAA-20 reals instal·lats; 31 proves noves. Les proves reals declaren skip si aquests assets no estan instal·lats, sense substituir-los per dades inventades.
- `npm.cmd --prefix frontend test`: suite frontend completa superada. `npm.cmd --prefix frontend run typecheck` i `npm.cmd --prefix frontend run build`: superats. Una correcció mínima preexistent a `OverlayLineStyle` resol el booleà opcional `dashed` amb el mateix default efectiu del material.
- Ruff dels mòduls científics/adaptadors nous i afectats, controlador, proves i eines: superat. L’entrypoint conserva **14 incidències Ruff preexistents**, exactament les mateixes que HEAD; [comparació](ruff-entrypoint-comparacio.json). No s’han canviat regles ni amagat diagnòstics.
- Pyright del domini/adaptadors de contaminació lumínica, controlador i CLI: **0 errors, 0 avisos**. Comprovació global: **67 errors i 3 avisos**, mateix multiconjunt de diagnòstics que HEAD; [comparació reproduïble](pyright-global-comparacio.json). No hi ha diagnòstics nous.
- Enllaços Markdown, imatges, dependències del nou pas i comprovació documental: resultat detallat a [auditoria documental](auditoria-documental.txt). Les incidències estructurals heretades d’altres passos continuen identificades; no es declara un PASS integral fictici.

## Reproducció de la connexió real

```powershell
python tools/build_black_marble_sources.py 'I:\TerraLab\data\earth\light-pollution\vj146a2\2026\256\VJ146A2.A2026256.h18v04.002.2026264085938.h5' --sha256 2537a64667a440deb099cf08b47a39744c9127abb742419ce256d38b62d0b762 --date 2026-09-13 --row 2067 --column 520 --rsr-manifest 'I:\TerraLab\data\earth\light-pollution\viirs-rsr\research\noaa-multisat\prepared\noaa-20-diagnostic-rsr.json' --mode kelvin --kelvin 3000 --normalization constant_photopic_flux --output .runtime-kelvin.json
```

Repetir amb `--mode realistic` i un altre output per a l’ensemble realista; `--gain LGS` proporciona contrast explícit. Els assets grans continuen a la biblioteca externa; el CLI no descarrega ni demana credencials. L’adquisició ordinària es manté al Pas 24.

## Represa

7.5 continua completat en S. 7.5.1 es completa en fonts C relatives/configuració/UI, amb limitacions anteriors. **Següent pas: 7.6 SG-REF**, compartit per S/C; cap transport anticipat.
