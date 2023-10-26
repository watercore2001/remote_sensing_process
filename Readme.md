# Process Remote Sensing Data For Deep Learning

## Setup Environment
```angular2html
#1. install required packages by conda
conda create -n process python=3.10
conda activate process
conda install gdal rasterio geopandas -c conda-forge

#2. install project by pip
git clone git@github.com:watercore2001/remote_sensing_process.git
cd ./remote_sensing_process
pip install .
```

## Supervise Task: generate dataset by label geojson 
### 1. Prepare Input Data
```angular2html
|-- Input Folder
|  |-- scene folder
|  |  |-- label1.geojson
|  |  |-- label2.geojson
|  |  |-- label3.geojson
|  |  |-- false.geojson
|  |  |-- unsure.geojson
|  |-- scene folder
...
```
There are some important restrictions on input.
- The name of every scene folder follows a specific format, known as the scene ID. 
For example, a scene folder's name may be T50SNG_20230921T052151.
- Labeling features in different scene GeoJSON should avoid overlapping area.
otherwise, it will result in duplicated samples within the different scenes.
- The GeoJSON file should use the same Coordinate Reference System (CRS) as the satellite image. 
- The GeoJSON file should not contain any invalid or null geometry.

### 2. Run



## Self-supervise Task: generate dataset by sentinel-2 data



