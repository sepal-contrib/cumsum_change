This dasboard application based on the [sepal-ui](https://sepal-ui.readthedocs.io/en/latest/) framework, provides a user-friendly interface for the use of the spatially cumulative sum change detection algorithm as proposed by [Manogaran & Lopez](https://www.sciencedirect.com/science/article/abs/pii/S004579061730811X?via%3Dihub). Its implementation has been taken from the [SERVIR SAR handbook](https://servirglobal.net/Global/Articles/Article/2674/sar-handbook-comprehensive-methodologies-for-forest-monitoring-and-biomass-estimation) and has been optimised to run on GPU instances.

## Input

The module can be run with any single-band time-series (optical or SAR) generated through the SEPAL recipes menu. 

## Output

The resulting output file can be found at:
- `~/module_results/cumsum/[name_of_output_folder]/cumsum_result.tif`

The output file is a 3-band raster that contains the date of change (Band 1), its confidence (Band 2) and the magnitude (Band 3).

