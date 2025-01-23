# Process Remote Sensing Data For Deep Learning V3 20250121

## Setup Environment
```angular2html
#step1. install required packages by conda
conda create -n process python=3.10
conda activate process
conda install gdal rasterio

#step2. install project by pip
git clone git@github.com:watercore2001/remote_sensing_process.git
cd ./remote_sensing_process
pip install .
```

## Self-supervise Task: generate dataset by sentinel-2 data
```angular2html
un_supervise_dataset --help
```

## Supervise Task: generate dataset by label shapefile

### 1. Prepare Input Data
```angular2html
|-- input folder
|  |-- scene folder1
|  |  |-- gt
|  |  |  |-- 1
|  |  |  |  |-- region1.shp
|  |  |  |  |-- region2.shp
|  |  |  |-- 2
|  |  |  |  |-- region3.shp
|  |  |  |  |-- region4.shp
|  |  |-- img
|  |  |  |-- B01.tif
|  |  |  |-- B02.tif
|  |  |  |-- B03.tif
|  |  |-- window [optional]
|  |  |  |-- window.shp
|  |-- scene folder2
...
```
Folder gt contains different label folder i which means value i in final dataset. 
Folder label i contains different region.

There are some important restrictions on input.
- 后续的程序提供了自动下载影像的功能，使用下载功能要求每一景文件夹的文件名满足特定格式，目前支持下面两种格式
  - T50SNG_20230921T052151
  - S2A_49SGV_20211024_0_L2A
- Labeling features in different scene shapefile should avoid overlapping area.
otherwise, it will result in duplicated samples within the different scenes.
- The shapefile file should use the same Coordinate Reference System (CRS) as the satellite image. 
- The shapefile file should NOT contain any invalid or null geometry.
- 对于同一个label（例如 1）下的多个shapefilefile，如果数量太多，会导致在运行时需要较大的内存。 因此建议手动进行合并以减少shapefile数量


### 2. `Optional` Generate window for select sample region

After Setup Environment, there is a command `cli_window` in conda environment.

这个命令基于已有的shapefile文件产生窗口，后续可以针对这个产生的窗口进行手动修改。

```angular2html
cli_window -h for more details.
# example
-i data -a B04 -c slide --window_size 256 --window_overlap_size 0
```

-a 表示用于参考的影像，该影像提供空间范围和空间分辨率，建议使用一个10m的波段即可。

产生的结果会自动放在每一景文件夹下，例如 window_20250113_1515 后面是代码执行的时间。
增加这个时间是为了当再次运行此代码产生窗口时，不会发生重名冲突



### 3. Run
After Setup Environment, there is a command `cli_dataset` in conda environment.

建议使用 file cropper. 即使用一个文件来产生窗口，这要求存在 window/window.shp 文件，这和之前是一致的

```angular2html
cli_dataset -h for more detail
example
-i data -o output -b B04 B08 B11 -a B04 -c file -s -p 80 20 0
```

### Output Dataset
```angular2html
|-- Output folder
|  |-- train
|  |  |-- img
|  |  |  |-- scene_folder
|  |  |  |  |-- 1.tif
|  |  |-- gt
|  |  |  |-- scene_folder
|  |  |  |  |-- 1.tif

|  |-- val
|  |  |-- img...
|  |  |-- gt...
...
```





