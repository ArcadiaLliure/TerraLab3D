# Programari i dades de tercers

## d3-celestial — traçat visual de constel·lacions

TerraLab3D incorpora una transformació empaquetada dels fitxers
`data/constellations.lines.json` i `data/constellations.json` de d3-celestial,
commit `7e720a3de062059d4c5400a379146a601d9010e0`.

Copyright (c) 2015, Olaf Frohn
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


## Taules espectrals CIE (Pas 7.5.1)

International Commission on Illumination (CIE), Viena, 2018. Dades LED/HP/FL/L41, CMF CIE 1931 2° i V(λ), [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Originals, metadades, DOI, fonts i checksums a `terralab3d/infrastructure/catalogs/spectra/`. Derivats espectrals amb atribució i mateixa llicència; codi separat de la llicència de dades.

## Dades instrumentals de referència fotomètrica (Pas 7.14)

Les [evidències de 7.14](docs/evidencies/pas7.14/fonts-i-models-instrumentals.md) contenen dades de referència, sense homologació instrumental completa. Els [URL, commits i SHA-256](docs/evidencies/pas7.14/fonts-manifest.json) identifiquen cada original.

- SQM CM500: VOTable del SVO Filter Profile Service, digitalització atribuïda a Cinzano2005, figura8. Es conserva la procedència original; no s’empaqueta el PDF del fabricant.
- TESS-W stars1277: mesures de GUAIX/LICA a `licaplot`, commit `0f55129d6a27ccfe489558f1f46d441e278626f6`. Dades originals i forma de resposta derivada sota GPL3, amb [llicència original](docs/evidencies/pas7.14/fonts/licaplot-gpl3-license.txt).
- Responsivitat PIN10D de `lica`, commit `a70ee75f24ef3c9766673a8dbb449147f90a1352`, sota MIT, amb [llicència i atribució originals](docs/evidencies/pas7.14/fonts/lica-license.txt).

No s’incorpora codi d’aquests repositoris. Els models instrumentals són dades de diagnòstic separades del codi propi de projecció i mantenen les limitacions de fosc, suport, FOV i calibratge documentades.

### Dades addicionals de laboratori (represa7.14)

Es conserven quinze fitxers originals de `licaplot/report` i de responsivitat TSL237 al mateix commit fixat, sota la GPL3 ja adjunta. [Manifest amb URL i SHA-256](docs/evidencies/pas7.14/represa-v2/manifest-dades-laboratori-v2.json). Els documents de fabricants, normes ISO/CIE i articles s’han consultat com a fonts; els PDF de consulta no s’empaqueten. Les formulacions de canvi de coordenades i els oracles són codi propi; no s’importa codi de laboratoris.
