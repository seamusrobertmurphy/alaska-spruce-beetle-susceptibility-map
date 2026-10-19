# Spruce beetle susceptibility map of Alaska

A 90 m map of the spruce stands most at risk in the next spruce beetle outbreak, for forest managers. Version 1.0, built 18 October 2026 from the code in the manuscript "A spruce beetle susceptibility map of Alaska using Sentinel-1 radar and crown-scale mortality data in the Susitna valley" (Murphy, 2026, submitted to Ecological Indicators). The code that made every file here is in the manuscript, in the `statewide` and `statewide-release` chunks of `01.manuscript/manuscript.qmd` at https://github.com/seamusrobertmurphy/deep-learn-alaska-spruce-beetle.

## What it shows

Spruce beetle outbreaks in Alaska kill the largest spruce first, so the tallest stands of large spruce are the ones most at risk. Radar backscatter measures stand height. Every Sentinel-1 radar scene over Alaska from October 2014 to December 2016, before the current outbreak reached the Susitna valley, was pooled into one map of pre-outbreak backscatter. Where that backscatter is at or above -8.44 dB, the stand is classed susceptible. The threshold was set on 34,990 dead and 6,774 living forest cells of the Zwieback et al. (2024) severity map of the Susitna valley, where it classed 91 per cent of the killed stands and 76 per cent of the spared stands correctly, an overall accuracy of 89 per cent (area under the curve 0.86, Cohen's kappa 0.61). Against the aerial detection survey the map ranked attacked above unattacked forest with an area under the curve of 0.70 on the Kenai Peninsula and 0.70 in the Matanuska-Susitna Borough, 0.61 in the Interior, and 0.44 in the Copper River basin, where the stands are short and open and the map should not be used; the canopy height band ranks them there instead.

Across 906,521 km² of forest in Alaska, 29 per cent is at or above the threshold, 62 per cent on the Kenai Peninsula, 48 in the Matanuska-Susitna Borough, 50 in the Valdez-Cordova census area and 27 in the Interior.

The map is of stand structure, not of beetles. It says which stands are tall and large, the kind the beetle has killed first in every recorded Alaska outbreak, and it has been validated only where the beetle has been. It is the hazard half of a stand rating, to be read with the beetle's current position from the aerial detection survey.

## The files

| File | Contents |
|---|---|
| `spruce_susceptibility_alaska_90m_class.tif` | The map managers need. One band, 8-bit, values 1 to 4 (see below), 0 outside Alaska. 29 MB. |
| `spruce_susceptibility_alaska_90m.tif` | The four measured bands behind it, so that you can set your own threshold. 16-bit integers at 100 times the value, with the scale factor 0.01 written into the file. 859 MB. |
| `spruce_susceptibility_alaska_90m_class.qml` | A QGIS style for the class map, with the legend below. |
| `README.md` | This file. |
| `LICENSE.txt` | CC BY 4.0. |

Both GeoTIFFs are Cloud Optimized GeoTIFFs with internal overviews, on the Alaska Albers projection (EPSG:3338), 90 m cells, 29,376 columns by 23,500 rows, with the top left corner at x = -1,040,580, y = 2,557,800 metres. They open directly in QGIS, ArcGIS Pro, R and Python with their projection.

Class values in `spruce_susceptibility_alaska_90m_class.tif`:

| Value | Class |
|---|---|
| 0 | Outside Alaska (no data) |
| 1 | No forest, a 90 m cell with no 10 m cell of 5 m canopy height or more |
| 2 | Forest below the threshold, backscatter under -8.44 dB |
| 3 | Susceptible, forest with backscatter at or above -8.44 dB, the tall large-spruce stands |
| 4 | Forest that no radar scene covered in October 2014 to December 2016 |

Bands in `spruce_susceptibility_alaska_90m.tif`, every one stored as an integer at 100 times the value, with no data as -32768 where the cell holds no forest or lies outside Alaska:

| Band | Name | Meaning | Real unit |
|---|---|---|---|
| 1 | VV | Mean Sentinel-1 VV backscatter, October 2014 to December 2016, slope corrected and brought to a 38 degree incidence angle (-0.125 dB per degree), averaged in linear power over every scene | decibels, divide by 100 |
| 2 | scenes | Number of scenes averaged in the cell (median 57) | count, divide by 100 |
| 3 | height | Mean ETH Zurich canopy height of 2020 of the 10 m cells | metres, divide by 100 |
| 4 | forest | Share of the 90 m cell whose 10 m cells have canopy height of 5 m or more | fraction, divide by 100 |

QGIS, ArcGIS Pro and rasterio read the scale factor and show the real units. Plain array reads give the stored integers, so divide by 100. A cell is susceptible where band 1 is at or above -844 (that is -8.44 dB) and band 4 is above 0. The same rule on the height band, 17.4 m, gave the height version of the map in the manuscript.

## Opening it

QGIS. Drag either file into the map. For the class map, right click the layer, Properties, Symbology, Style, Load Style, and choose the `.qml` file.

ArcGIS Pro. Add Data, choose the file. For the class map use Unique Values symbology on the four values with the legend above.

R.

```r
library(terra)
cls <- rast("spruce_susceptibility_alaska_90m_class.tif")
full <- rast("spruce_susceptibility_alaska_90m.tif")  # terra applies the scale factor, so values are in dB, count, m and fraction
plot(cls)
```

Python.

```python
import rasterio
with rasterio.open("spruce_susceptibility_alaska_90m.tif") as src:
    vv = src.read(1) * src.scales[0]  # decibels
```

Google Earth Engine. Both layers are public assets, so no download is needed.

```js
var full = ee.Image("projects/vvb-checks/assets/spruce_susceptibility_alaska_90m");  // four Int16 bands at 100 times the value
var cls = ee.Image("projects/vvb-checks/assets/spruce_susceptibility_alaska_90m_class");  // one Byte band, classes 1 to 4 as above
Map.addLayer(cls, {min: 1, max: 4, palette: ["f0f0f0", "a1d99b", "d7301f", "9e9ac8"]}, "Susceptibility class");
Map.addLayer(full.select("VV").divide(100), {min: -12, max: -6}, "VV (dB)");
```

## Method in brief

Sentinel-1 ground range detected scenes (Earth Engine `COPERNICUS/S1_GRD`) were corrected for terrain slope, and the fall of backscatter with incidence angle was fitted on 150 scenes drawn at random and removed, so that scenes of every orbit could be averaged. The mean over scenes was taken in linear power and converted to decibels at the 90 m level of each scene's image pyramid. Canopy height is the ETH Zurich global canopy height map of 2020 (Lang et al. 2023, Earth Engine `users/nlang/ETH_GlobalCanopyHeight_2020_10m_v1`); forest is a 10 m cell of 5 m or more. The state boundary is the United States Census Bureau TIGER/Line 2018 polygon (`TIGER/2018/States`). The map was validated as made, on the cells of the Zwieback et al. (2024) severity map and against the aerial detection survey in four regions. Full methods, validation tables and the literature behind the height effect are in the manuscript.

## Limits

The map was validated where the beetle has been, the Susitna valley, the Kenai Peninsula and the Matanuska-Susitna Borough. In the Copper River basin the backscatter did not rank attacked above unattacked forest, and the height band should be used there. The radar record before 2017 did not cover every part of the state evenly; the scenes band gives the count behind each cell, and class 4 marks forest no scene covered. Cells are 90 m, so a stand smaller than about a hectare is not resolved. The product is a snapshot of structure in 2014 to 2016 and 2020; stands cut, burned or killed since then are not updated.

## Citation

Murphy, S. R. (2026). Spruce beetle susceptibility map of Alaska, 90 m, version 1.0 [data set]. https://github.com/seamusrobertmurphy/deep-learn-alaska-spruce-beetle/releases/tag/map-v1.0. Derived from Copernicus Sentinel-1 and Lang et al. (2023). Manuscript: Murphy, S. R. (2026). A spruce beetle susceptibility map of Alaska using Sentinel-1 radar and crown-scale mortality data in the Susitna valley. Submitted to Ecological Indicators.

Lang, N., Jetz, W., Schindler, K. and Wegner, J. D. (2023). A high-resolution canopy height model of the Earth. Nature Ecology and Evolution 7, 1778 to 1789. https://doi.org/10.1038/s41559-023-02206-6

Zwieback, S., Young-Robertson, J., Robertson, M., Tian, Y., Chang, Q., Morris, M., White, J. and Moan, J. (2024). Low-severity spruce beetle infestation mapped from high-resolution satellite imagery with a convolutional network. ISPRS Journal of Photogrammetry and Remote Sensing 212, 412 to 421. https://doi.org/10.1016/j.isprsjprs.2024.05.013

## Licence and contact

CC BY 4.0, see LICENSE.txt. Seamus Robert Murphy, seamusrobertmurphy@gmail.com. Problems with the files can be reported as issues on the GitHub repository.
