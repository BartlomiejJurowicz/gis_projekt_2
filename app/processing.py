import geopandas as gpd
import rasterio
import numpy as np
from rasterstats import zonal_stats
import os


def calculate_ndvi_and_stats(vector_path, red_path, nir_path):
    # 1. Wczytanie pasm
    with rasterio.open(red_path) as red_src:
        red = red_src.read(1).astype('float32')
        transform = red_src.transform
        crs = red_src.crs
        profile = red_src.profile

    with rasterio.open(nir_path) as nir_src:
        nir = nir_src.read(1).astype('float32')

    # 2. Obliczenie NDVI
    ndvi = (nir - red) / (nir + red + 1e-10)

    # 3. Zapisanie tymczasowego rastra NDVI
    # W Dockerze używamy /tmp/ bo mamy do niego uprawnienia
    ndvi_tmp_path = "/tmp/result_ndvi.tif"
    profile.update(dtype=rasterio.float32, count=1)
    with rasterio.open(ndvi_tmp_path, 'w', **profile) as dst:
        dst.write(ndvi, 1)

    # 4. Wczytanie wektora
    gdf = gpd.read_file(vector_path)
    if gdf.crs != crs:
        gdf = gdf.to_crs(crs)

    # 5. Obliczenie statystyk - przekazujemy GDF i ścieżkę do rastra
    # Używamy bezpośrednio obiektu gdf, aby uniknąć błędów fiona
    stats = zonal_stats(
        gdf,
        ndvi_tmp_path,
        stats="mean",
        geojson_out=True
    )

    return gpd.GeoDataFrame.from_features(stats)