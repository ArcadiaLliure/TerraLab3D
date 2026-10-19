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

## SciPy — quadratura de referència offline (Pas 7.6)

Dependència SciPy ≥1.15 per `integrate.quad_vec` i contrasts analítics `special.exp1`; versió verificada 1.16.2. Copyright (c) 2001–2002 Enthought, Inc.; 2003, SciPy Developers. Llicència BSD-3-Clause comprovada a les metadades de la distribució instal·lada. No s’ha copiat ni modificat codi de SciPy: la distribució de la dependència conserva els seus fitxers LICENSE i avisos dels components inclosos. Cap codi extern LPTRAN incorporat.

## Seccions eficaces d'O3 (Pas 7.10)

Serdyuchenko A., Gorshelev V., Weber M., Burrows J.P., dataset [10.5281/zenodo.5793207](https://doi.org/10.5281/zenodo.5793207), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), llicència comprovada a l'API Zenodo el 2026-10-19. Dades originals visibles i LUT derivada a `infrastructure/catalogs/gases/`, amb atribució, unitats, transformacions, restriccions i checksums al manifest i README. Retall 380–780 nm i 203–293 K; conversió cm² a m² i mostreig de LUT 0,5 nm. Cap codi extern copiat. Referències científiques: Gorshelev et al., AMT 7,609–624 (2014), DOI 10.5194/amt-7-609-2014; Serdyuchenko et al., AMT 7,625–636 (2014), DOI 10.5194/amt-7-625-2014.
