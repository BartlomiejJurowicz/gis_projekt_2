import streamlit as st
import geopandas as gpd
import pandas as pd
from streamlit_folium import st_folium
import folium
from folium.raster_layers import ImageOverlay
import os
import tempfile
import numpy as np
import matplotlib.cm as cm

# Import funkcji obliczeniowej
try:
    from processing import calculate_ndvi_and_stats
except ImportError:
    from app.processing import calculate_ndvi_and_stats

st.set_page_config(page_title="Copernicus NDVI Analyzer", layout="wide")

# 1. TWOJA INSTRUKCJA (Niebieska ramka - bez zmian)
st.title("🛰️ Analizator Indeksu NDVI (Sentinel-2)")
st.info("""
### 📘 Instrukcja krok po kroku:
1. **Przygotuj Wektor:** Wejdź na [geojson.io](https://geojson.io/), narysuj obszary (np. pola, lasy) i zapisz plik jako **GeoJSON**. Pamiętaj o dodaniu kolumny `id` w tabeli atrybutów.
2. **Pobierz Dane Satelitarne:** Wejdź na [Copernicus Browser](https://browser.dataspace.copernicus.eu/). 
   - Znajdź swój obszar, wybierz **Sentinel-2** (małe zachmurzenie).
   - W sekcji **Download -> Analytical** wybierz format **TIFF (16-bit)**.
   - Pobierz oddzielnie pasmo **B04** (Red) oraz pasmo **B08** (NIR).
3. **Wgraj Pliki:** Użyj poniższych pól, aby załadować przygotowane dane.
4. **Analiza:** Kliknij przycisk 'Uruchom analizę', aby obliczyć NDVI i wyświetlić wyniki.

Przykładowe dane znjadziesz w w app/data/
""")

# 2. SEKCJA WGrywania plików
st.subheader("📂 Załaduj dane")
col1, col2, col3 = st.columns(3)
with col1:
    vector_file = st.file_uploader("1. Wektor (GeoJSON)", type=['geojson'])
with col2:
    red_file = st.file_uploader("2. Pasmo Red (B04)", type=['tif', 'tiff'])
with col3:
    nir_file = st.file_uploader("3. Pasmo NIR (B08)", type=['tif', 'tiff'])

if 'results' not in st.session_state:
    st.session_state['results'] = None
    st.session_state['ndvi_raster'] = None

# Przyciski akcji
btn_col1, btn_col2, _ = st.columns([1, 1, 4])
with btn_col1:
    run_analysis = st.button("🚀 Uruchom analizę NDVI", type="primary", use_container_width=True)
with btn_col2:
    if st.button("🗑️ Wyczyść wyniki", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# 3. LOGIKA ANALIZY Z DYNAMICZNĄ SKALĄ RASTRA
if run_analysis and vector_file and red_file and nir_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        vec_path = os.path.join(tmpdir, "vec.geojson")
        red_path = os.path.join(tmpdir, "red.tif")
        nir_path = os.path.join(tmpdir, "nir.tif")

        with open(vec_path, "wb") as f:
            f.write(vector_file.getbuffer())
        with open(red_path, "wb") as f:
            f.write(red_file.getbuffer())
        with open(nir_path, "wb") as f:
            f.write(nir_file.getbuffer())

        try:
            with st.spinner("Przetwarzanie danych..."):
                res_gdf = calculate_ndvi_and_stats(vec_path, red_path, nir_path)

                import rasterio

                with rasterio.open(red_path) as src:
                    red = src.read(1).astype('float32')
                    bounds = [[src.bounds.bottom, src.bounds.left], [src.bounds.top, src.bounds.right]]
                with rasterio.open(nir_path) as src:
                    nir = src.read(1).astype('float32')

                # Dynamiczne wyliczenie NDVI
                ndvi_array = (nir - red) / (nir + red + 1e-10)

                # DYNAMICZNA SKALA: Bierzemy min i max z Twojego zdjęcia
                v_min, v_max = np.nanmin(ndvi_array), np.nanmax(ndvi_array)
                # Normalizacja do zakresu 0-1 dla kolorowania
                norm_ndvi = (ndvi_array - v_min) / (v_max - v_min + 1e-10)

                color_map = cm.get_cmap('RdYlGn')
                st.session_state['results'] = res_gdf
                st.session_state['ndvi_raster'] = color_map(norm_ndvi)
                st.session_state['raster_bounds'] = bounds
                st.session_state['v_range'] = (v_min, v_max)
            st.success("Analiza zakończona!")
        except Exception as e:
            st.error(f"Błąd: {e}")

# 4. WYNIKI - MAPA (2/3) i LEGENDA (1/3)
if st.session_state['results'] is not None:
    st.divider()
    m_col, l_col = st.columns([2, 1])

    with m_col:
        st.subheader("🗺️ Wizualizacja NDVI")
        res_gdf = st.session_state['results']
        if res_gdf.crs is None: res_gdf = res_gdf.set_crs(epsg=4326)
        map_gdf = res_gdf.to_crs(epsg=4326)

        center = [map_gdf.geometry.centroid.y.mean(), map_gdf.geometry.centroid.x.mean()]
        m = folium.Map(location=center, zoom_start=14)
        folium.TileLayer('OpenStreetMap').add_to(m)

        if st.session_state['ndvi_raster'] is not None:
            ImageOverlay(
                image=st.session_state['ndvi_raster'],
                bounds=st.session_state['raster_bounds'],
                opacity=0.8,  # Większa widoczność kolorów
                name="Piksele NDVI"
            ).add_to(m)

        folium.GeoJson(
            map_gdf,
            tooltip=folium.GeoJsonTooltip(fields=['id', 'mean'], aliases=['ID:', 'Średnie NDVI:']),
            style_function=lambda x: {'fillColor': 'none', 'color': 'blue', 'weight': 3}
        ).add_to(m)

        st_folium(m, width=900, height=550, key="map")

    with l_col:
        st.subheader("🎨 Legenda kolorów (Z zakresu zdjęcia)")
        v_min, v_max = st.session_state.get('v_range', (-1, 1))

        st.write(f"Zakres NDVI na tym zdjęciu: **{v_min:.2f} do {v_max:.2f}**")

        st.markdown(f"""
        <div style="background: linear-gradient(to right, red, yellow, green); height: 30px; width: 100%; border-radius: 5px;"></div>
        <div style="display: flex; justify-content: space-between;">
            <span>{v_min:.2f} (Najniższe)</span>
            <span>{(v_min + v_max) / 2:.2f}</span>
            <span>{v_max:.2f} (Najwyższe)</span>
        </div>
        <br>
        <p>🔴 <b>Niskie wartości:</b> Tereny zabudowane, drogi, goła ziemia.</p>
        <p>🟡 <b>Średnie wartości:</b> Rzadka roślinność, trawy, uprawy.</p>
        <p>🟢 <b>Wysokie wartości:</b> Lasy, gęsta roślinność, zdrowe uprawy.</p>
        """, unsafe_allow_html=True)

    # TABELA
    st.divider()
    st.subheader("📊 Wyniki w tabeli")
    st.dataframe(pd.DataFrame(st.session_state['results'].drop(columns='geometry')), use_container_width=True)