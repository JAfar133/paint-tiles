from osgeo import gdal, osr
import numpy as np
import sys
import subprocess
from config import *


def copy_georeferencing(grib2_dataset, tif_dataset):
    gt = grib2_dataset.GetGeoTransform()
    tif_dataset.SetGeoTransform(gt)
    # tif_dataset.SetProjection(grib2_dataset.GetProjection())


def rgb_to_tif(rgb_image, output_path, model):
    if rgb_image is None:
        logger.warning("Data not available for the specified parameter number.")
        return

    if rgb_image.ndim == 2:
        rgb_image = np.expand_dims(rgb_image, axis=-1)
    if rgb_image.shape[2] == 1:
        rgb_image = np.repeat(rgb_image, 3, axis=2)
    enlarged_rgb = np.repeat(rgb_image, 2, axis=1)
    enlarged_rgb = np.repeat(enlarged_rgb, 2, axis=0)

    rows, cols, _ = enlarged_rgb.shape

    driver = gdal.GetDriverByName('GTiff')

    dataset = driver.Create(output_path, cols, rows, 3, gdal.GDT_Byte)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)  # Use WGS 84
    dataset.SetProjection(srs.ExportToWkt())

    geotransform = (-180, 360 / cols, 0, 90, 0, -180 / rows)
    dataset.SetGeoTransform(geotransform)
    if model == 'GFS':
        shifted_rgb = np.roll(enlarged_rgb, shift=-1, axis=0)

        for i in range(3):
            band = dataset.GetRasterBand(i + 1)
            band.WriteArray(shifted_rgb[:, :cols // 2, i], xoff=cols // 2)

        for i in range(3):
            band = dataset.GetRasterBand(i + 1)
            band.WriteArray(shifted_rgb[:, cols // 2:, i])

    else:
        for i in range(3):
            band = dataset.GetRasterBand(i + 1)
            shifted_rgb = np.roll(enlarged_rgb[:, :, i], shift=-1, axis=1)
            shifted_rgb = np.roll(shifted_rgb, shift=-1, axis=0)
            band.WriteArray(shifted_rgb)


def create_tiles(input_tif, output_folder, zoom_levels="0-3"):
    output_tif = f'{input_tif}.temp.tif'
    try:
        os.remove(output_tif)
    except OSError:
        pass
    subprocess.run(['gdalwarp', '-r', 'bilinear', input_tif, output_tif],
                   stdout=subprocess.DEVNULL)
    gdal2tiles = '/usr/bin/gdal2tiles.py'
    command = [
        'python',
        gdal2tiles,
        '-z', zoom_levels,
        '-w', 'none',
        '-n',
        '-r', 'bilinear',
        output_tif,
        output_folder
    ]
    subprocess.run(command, stdout=subprocess.DEVNULL, check=True)
    logger.debug(f"Тайлы сохранены по пути {output_folder}")
    try:
        os.remove(input_tif)
        os.remove(output_tif)
    except OSError:
        pass

