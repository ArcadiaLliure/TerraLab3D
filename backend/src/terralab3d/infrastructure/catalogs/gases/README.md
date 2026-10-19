# Absorció gasosa offline del Pas 7.10

O3 de Serdyuchenko, Gorshelev, Weber i Burrows, [Zenodo, DOI 10.5281/zenodo.5793207](https://zenodo.org/records/5793207), **CC BY 4.0** segons les metadades API consultades el 2026-10-19. Referències: Gorshelev et al., *AMT* 7, 609–624 (2014), DOI 10.5194/amt-7-609-2014; Serdyuchenko et al., *AMT* 7, 625–636 (2014), DOI 10.5194/amt-7-625-2014. [Llicència](https://creativecommons.org/licenses/by/4.0/).

El [manifest](manifest.json) identifica l'original descarregat, l'atribució, els checksums i totes les transformacions. Es conserva sense pèrdua el retall visible 380–780 nm a 0,01 nm i temperatures 203–293 K. La columna publicada de 193 K té 69 valors negatius visibles: s'exclou aquell domini, sense modificar ni retallar aquests valors a zero. No s'extrapolen temperatures, longituds d'ona ni composicions.

`o3-serdyuchenko-visible-raw.npz` és la referència fina; `o3-serdyuchenko-visible-lut.csv` és la LUT de 0,5 nm. Ambdues expressen secció eficaç en **m²/molècula**, λ de **buit en nm**, i T en K. Ordre tèrmic ascendent 203, 213, …, 293 K. La LUT interpola linealment en λ i T; no parametriza dependència de pressió. La incertesa experimental del dataset és separada de l'error numèric de discretització i no es declara resolta per superar 0,01 mag.

Des de l'arrel, amb l'original Zenodo descarregat, es poden reproduir els assets en una carpeta temporal:

```powershell
python tools/prepare_ozone_step7_10.py --original ruta/SerdyuchenkoGorshelev5digits_latest.dat --output .runtime-ozone-reproduction
```

El runtime consumeix una composició prescrita amb perfil explícit per espècie/tile i cobertura vertical. Aquest catàleg acredita O3; no acredita absorció d'O2, H2O, NO2 ni un espectre complet de l'aire terrestre real. Un perfil absent o una espècie sense LUT produeixen error. B2 desactiva gasos amb un estat diagnòstic explícit. Cap petició descarrega dades automàticament.
