import numpy as np
import rasterio
from rasterio.transform import from_origin
import geopandas as gpd
from shapely.geometry import Polygon

# 1. Tworzymy sztuczny RASTER (TIFF) - 100x100 pikseli
data = np.random.randint(0, 255, (100, 100)).astype('uint8')
transform = from_origin(19.0, 50.5, 0.01, 0.01) # Współrzędne w okolicach Opola ;)

with rasterio.open('app/data/test_raster.tif', 'w', driver='GTiff',
                   height=100, width=100, count=1, dtype='uint8',
                   crs='EPSG:4326', transform=transform) as dst:
    dst.write(data, 1)

# 2. Tworzymy sztuczny WEKTOR (GeoJSON) - kwadrat na środku rastra
poly = Polygon([(19.2, 50.2), (19.8, 50.2), (19.8, 50.8), (19.2, 50.8)])
gdf = gpd.GeoDataFrame([{'geometry': poly, 'id': 1}], crs='EPSG:4326')
gdf.to_file('app/data/test_vector.geojson', driver='GeoJSON')

print("Pliki testowe utworzone w app/data/")