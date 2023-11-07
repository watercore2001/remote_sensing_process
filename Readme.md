# Process Remote Sensing Data For Deep Learning V1.2

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
|  |  |-- label1.shp
|  |  |-- label2.shp
|  |  |-- label3.shp
|  |  |-- false.shp
|  |  |-- unsure.shp
|  |-- scene folder
...
```
There are some important restrictions on input.
- The name of every scene folder follows a specific format, known as the scene ID. 
For example, a scene folder's name may be T50SNG_20230921T052151.
- Labeling features in different scene shapefile should avoid overlapping area.
otherwise, it will result in duplicated samples within the different scenes.
- The shapefile file should use the same Coordinate Reference System (CRS) as the satellite image. 
- The shapefile file should not contain any invalid or null geometry.

### 2. Run
After Setup Environment, There is a command `supervise_dataset` in your conda environment.
```angular2html
conda activate process
supervise_dataset --help
# then you will see
usage: supervise_dataset [-h] -i INPUT_FOLDER -o OUTPUT_FOLDER -b {B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B11,B12} [{B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B11,B12} ...] [-s | --use_stack | --no-use_stack] -c {object,slide,file}
                         [--window_size WINDOW_SIZE] [--window_overlap_size WINDOW_OVERLAP_SIZE]

options:
  -h, --help            show this help message and exit
  -i INPUT_FOLDER, --input_folder INPUT_FOLDER
                        Input label folder.
  -o OUTPUT_FOLDER, --output_folder OUTPUT_FOLDER
  -b {B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B11,B12} [{B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B11,B12} ...], --bands {B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B11,B12} [{B01,B02,B03,B04,B05,B06,B07,B08,B8A,B09,B11,B12} ...]
                        These bands will be downloaded and subsequently stacked in the order of your input if the -s flag is chosen.
  -s, --use_stack, --no-use_stack
                        If stack or not.
  -c {object,slide,file}, --cropper {object,slide,file}
                        There are three cropper.
  --window_size WINDOW_SIZE
                        This will be used if you choose object cropper and slide cropper.
  --window_overlap_size WINDOW_OVERLAP_SIZE
                        This will be used if you choose slide cropper.
```

## Self-supervise Task: generate dataset by sentinel-2 data



