# Spatially cumulative sum algorithm for change detection
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) 
[![Black badge](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## About 

This dasboard application based on the [sepal-ui](https://sepal-ui.readthedocs.io/en/latest/) framework, provides a user-friendly interface for the use of the spatially cumulative sum algorithm for time-series change detection as proposed by [Manogaran & Lopez](https://www.sciencedirect.com/science/article/abs/pii/S004579061730811X?via%3Dihub). Its implementation has been taken from the [SERVIR SAR handbook](https://servirglobal.net/Global/Articles/Article/2674/sar-handbook-comprehensive-methodologies-for-forest-monitoring-and-biomass-estimation) and has been optimised to run on GPU instances.

## Input

The module can be run with any single-band time-series (optical or SAR) generated through the SEPAL recipes menu. The module asks to provide the high-level folder.

## Output

The resulting output file can be found at:
- `~/module_results/cumsum/[name_of_output_folder]/cumsum_result.tif`

The output file is a 3-band raster that contains the date of change (Band 1), its confidence (Band 2) and the magnitude (Band 3).

## Contribute

first download the repository to your own sepal account 

```
git clone https://github.com/buddyvolly/cumsum_change.git
```

Then in the `cumsum_change` folder, launch the `ui.ipynb` notebook and run it with voila.

> :warning: If for some reason the sepal_ui module doesn't work on your instance, you can run the `no_ui.ipynb` file as a notebook using `kernel->run all`
