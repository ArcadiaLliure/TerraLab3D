# Bibliografia primària i fonts oficials

## Modelatge de skyglow

- Cinzano, P.; Falchi, F. (2012). *The propagation of light pollution in the atmosphere*. MNRAS 427, 3337–3357. DOI: 10.1111/j.1365-2966.2012.21884.x. https://academic.oup.com/mnras/article/427/4/3337/973668
- Garstang, R. H. (1986). *Model for artificial night-sky illumination*. PASP 98, 364–375. DOI: 10.1086/131768.
- Falchi, F. et al. (2016). *The new world atlas of artificial night sky brightness*. Science Advances 2:e1600377. DOI: 10.1126/sciadv.1600377. https://pmc.ncbi.nlm.nih.gov/articles/PMC4928945/
- Duriscoe, D. M. (2016). *Photometric indicators of visual night sky quality derived from all-sky brightness maps*. JQSRT 181, 33–45. DOI: 10.1016/j.jqsrt.2016.02.022.
- Kocifaj, M.; Barentine, J. C. (2021). *Air pollution mitigation can reduce the brightness of the night sky in and near cities*. Scientific Reports 11, 14622. https://www.nature.com/articles/s41598-021-94241-1

## Núvols

- Kyba, C. C. M.; Ruhtz, T.; Fischer, J.; Hölker, F. (2011). *Cloud Coverage Acts as an Amplifier for Ecological Light Pollution in Urban Ecosystems*. PLOS ONE 6:e17307. DOI: 10.1371/journal.pone.0017307.

## Transferència radiativa i atmosfera

- Ricchiazzi, P.; Yang, S.; Gautier, C.; Sowle, D. (1998). *SBDART: A Research and Teaching Software Tool for Plane-Parallel Radiative Transfer in the Earth's Atmosphere*. BAMS 79, 2101–2114. DOI: 10.1175/1520-0477(1998)079<2101:SARATS>2.0.CO;2.
- Gordon, I. E. et al. (2026). *The HITRAN2024 molecular spectroscopic database*. JQSRT 353, 109807. DOI: 10.1016/j.jqsrt.2026.109807. https://www.hitran.org/docs/hitran-papers/
- Bodhaine, B. A. et al. (1999). *On Rayleigh Optical Depth Calculations*. Journal of Atmospheric and Oceanic Technology 16, 1854–1861.
- Hansen, J. E.; Travis, L. D. (1974). *Light scattering in planetary atmospheres*. Space Science Reviews 16, 527–610. DOI: 10.1007/BF00168069.
- Henyey, L. C.; Greenstein, J. L. (1941). *Diffuse radiation in the Galaxy*. ApJ 93, 70. DOI: 10.1086/144246.
- Mie, G. (1908). *Beiträge zur Optik trüber Medien, speziell kolloidaler Metallösungen*. Annalen der Physik 330, 377–445. DOI: 10.1002/andp.19083300302.

## VIIRS i llums nocturnes

- NOAA National Calibration Center. *JPSS J1/NOAA-20 VIIRS Relative Spectral Response Functions*. https://ncc.nesdis.noaa.gov/NOAA-20/J1VIIRS_NOAA20_SpectralResponseFunctions.php
- NOAA National Calibration Center. [*JPSS J2/NOAA-21 VIIRS Relative Spectral Response Functions*](https://ncc.nesdis.noaa.gov/NOAA-21/J2VIIRS_SpectralResponseFunctions.php). Paquet DAWG at-launch V2 descarregat i README PDF inspeccionat el 2026-10-18; inclou LGS/MGS i recomana MGS com a proxy HGS sense cota d'error numèrica. Consulteu [SHA-256, membres i límits](../evidencies/pas7.3/revisio-multisatel-lit.md).
- NOAA NCC. *NOAA-20 Standardized Calibration Parameters*. https://ncc.nesdis.noaa.gov/NOAA-20/StandardizedCalibrationParameters.php
- NOAA/NASA. *VIIRS SDR User's Guide* i *Radiometric Calibration ATBD*.
- NOAA National Calibration Center. *VIIRS Relative Spectral Response Functions* i *SNPP VIIRS Modulated RSR Release 1.0*: [catàleg](https://ncc.nesdis.noaa.gov/VIIRS/VIIRSSpectralResponseFunctions.php), [README](https://ncc.nesdis.noaa.gov/documents/documentation/README_Modulated_RSR_Release_1.0) i [taula DNB LGS](https://ncc.nesdis.noaa.gov/documents/documentation/GT_F1_RSR_DNBLGS_v5_response_orbit6557_ccm.dat), consultats el 2026-10-17; ús diagnòstic, no substitueix la RSR efectiva anual de VNP46A2.002.
- NASA MCST. [*L1B LUT History*](https://mcst.gsfc.nasa.gov/l1b-lut-history), paquet NPP V3.1.0.58 i `F-PREDICTED` inspeccionats el 2026-10-18; [NOAA CoastWatch, LUT IDPS](https://coastwatch.noaa.gov/pub/smcd/VIIRS_SDR/SNPP_LUTs/CURRENT_IDPS_LUTs/) amb índex conservat pel cercador però accés directe bloquejat (403). Vegeu la [matriu de fitxers, checksums i límits](../evidencies/pas7.3/recerca-rsr-2026.md).
- NASA. [*Black Marble User Guide Collection 2*](https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/Document%20Archive/Science%20Data%20Product%20Documentation/Black-Marble_v2.0_UG_2024.pdf), [*Black Marble ATBD v1.1*](https://ladsweb.modaps.eosdis.nasa.gov/api/v2/content/archives/Document%20Archive/Science%20Data%20Product%20Documentation/Product%20Generation%20Algorithms/VIIRS_Black_Marble_ATBD_v1.1_July_2020.pdf) i [validació de producte](https://viirsland.gsfc.nasa.gov/Val/BM_Val.html), contrastats el 2026-10-18: cadena L1B/L3 i RSR anual declarada, sense taula numèrica 2026 publicada en aquests documents.
- Román, M. O. et al. (2024). [*Continuity between NASA MODIS Collection 6.1 and VIIRS Collection 2 land products*](https://sites.bu.edu/cliveg/files/2024/01/MODIS-VIIRS-Cont-RSE.pdf), figura 36: corbes RSR comparatives, sense taula numèrica 2026 verificada en aquesta revisió.
- Wang, Z. et al. (2021). [*Quantifying uncertainties in nighttime light retrievals from Suomi-NPP and NOAA-20 VIIRS Day/Night Band data*](https://ntrs.nasa.gov/api/citations/20210017813/downloads/1-s2.0-S0034425721002777-main.pdf), Remote Sensing of Environment 263, 112557. Evidència d'incertesa V001, no pressupost C2 directament transferible.
- NOAA NCC. *ATBD VIIRS Radiometric Calibration* (2013), [§2.1.2.1](https://ncc.nesdis.noaa.gov/documents/documentation/ATBD-VIIRS-RadiometricCal_20131212.pdf#page=38); radiància DNB integrada `W·cm⁻²·sr⁻¹`, consultat el 2026-10-17.
- NASA LAADS. [*VNP46A2 Collection 2*](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VNP46A2), resposta DNB anual Suomi-NPP, consultat el 2026-10-17.
- NASA LAADS. [*VJ146A2 Collection 2*](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ146A2) i [especificació de fitxer v2.0.4](https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/2/VJ146A2_v2.0); [*VJ246A2 Collection 2*](https://ladsweb.modaps.eosdis.nasa.gov/missions-and-measurements/products/VJ246A2). Catàlegs i índexs consultats el 2026-10-18; cap grànul J1/J2 binari obtingut.
- NOAA NESDIS. [*Cessation of Suomi-NPP data to users on/after November 2, 2026*](https://www.nesdis.noaa.gov/news/cessation-of-suomi-national-polar-orbiting-partnership-s-npp-data-users-onafter-november-2-2026); afecta el lliurament NOAA i no acredita el cessament de l'arxiu històric NASA.
- Guenther, B.; Lei, N.; Moeller, C. (2016). [*VIIRS S-NPP Nighttime DNB Spectral Response Function*](https://digitalcommons.usu.edu/calcon/CALCON2016/all2016content/33/), CALCON; la RSR LGS no representa plenament MGS/HGS nocturns, consultat el 2026-10-17.
- Earth Observation Group. *VIIRS Nighttime Lights VNL*. https://eogdata.mines.edu/products/vnl/
- NASA VIIRS Land. *Black Marble VNP46 product suite*. https://viirsland.gsfc.nasa.gov/Products/NASA/BlackMarble.html
- Coesfeld, J.; Kuester, T.; Kuechly, H. U.; Kyba, C. C. M. (2020). *Reducing Variability and Removing Natural Light from Nighttime Satellite Imagery: A Case Study Using the VIIRS DNB*. Sensors 20, 3287. DOI: 10.3390/s20113287. Ús documental: §2.3.1 per la discontinuïtat de punt zero de la sèrie estudiada; la correcció concreta no es generalitza.
- Uprety, S. et al. (2019). *Calibration Improvements in S-NPP VIIRS DNB Sensor Data Record Using Version 2 Reprocessing*. IEEE TGRS 57(12), 9602–9611. DOI: 10.1109/TGRS.2019.2927942. Ús documental: baixa radiància, offset/airglow i processament DNB; aplicabilitat a cada producte VNP46 s'ha de verificar.

## Mesura del cel

- Bará, S. et al. (2019). *Absolute Radiometric Calibration of TESS-W and SQM Night Sky Brightness Sensors*. Sensors 19, 1336. DOI: 10.3390/s19061336.
- CIE (2019). *The Basis of Physical Photometry, 3rd Edition*. CIE 018:2019. DOI: 10.25039/TR.018.2019.
- Bortle, J. E. (2001). *Introducing the Bortle Dark-Sky Scale*. Sky & Telescope, 101(2), 126–129.

## Meteorologia i composició

- ECMWF/C3S. *ERA5*. https://www.ecmwf.int/en/forecasts/dataset/ecmwf-reanalysis-v5
- ECMWF/CAMS. *CAMS global atmospheric composition forecasts*. https://www.ecmwf.int/en/forecasts/datasets/cams-global-atmospheric-composition-forecasts
- Copernicus. *Licence to use Copernicus Products*. https://ads.atmosphere.copernicus.eu/licences/licence-to-use-copernicus-products

## Mètodes numèrics

- Fritsch, F. N.; Carlson, R. E. (1980). *Monotone Piecewise Cubic Interpolation*. SIAM J. Numer. Anal. 17, 238–246. DOI: 10.1137/0717021.

## Notes de verificació

Les atribucions específiques de Cinzano–Falchi sobre 20 coeficients de Legendre, graella 80–100 km i límit horitzontal 120 km constaven com a verificades en la revisió anterior. La §2.1.2.1 de l'ATBD i la unitat integrada DNB `W·cm⁻²·sr⁻¹` s'han verificat directament a 7.3. Continuem sense donar per verificades les Figures 3–4 de Sánchez de Miguel et al. (2017) ni una afirmació concreta de Cinzano–Falchi sobre la precisió de dues dispersions. La redistribució de les taules RSR i els drets de derivats HITRAN continuen pendents de verificació legal específica.

## Referències de SG-REF consultades el 2026-10-18

- [SciPy `quad_vec`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad_vec.html): quadratura vectorial adaptativa GK21 i diagnòstics. Dependència emprada, versió verificada 1.16.2; BSD-3-Clause.
- [Cinzano i Falchi (2012), The propagation of light pollution in the atmosphere](https://arxiv.org/abs/1209.2031): abast de models que incorporen dispersions múltiples. Cap implementació LPTRAN importada ni equivalència completa declarada.
- [Whitney (2011), Monte Carlo Radiative Transfer](https://arxiv.org/abs/1104.4990): referència metodològica de transport estocàstic.
- [NASA (2019), Modeling Atmosphere-Ocean Radiative Transfer: A PACE Mission Perspective](https://ntrs.nasa.gov/api/citations/20190026727/downloads/20190026727.pdf): transport invers detector→font i estimadors locals. SG-REF usa un algorisme escalar propi, amb límits diferents.
