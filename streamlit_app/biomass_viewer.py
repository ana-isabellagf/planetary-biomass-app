import streamlit as st
import requests
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import zipfile
import tempfile
import os
import numpy as np
import rioxarray
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from shapely.geometry import box
import xarray as xr
import planetary_computer
from pystac_client import Client

st.set_page_config(page_title="Biomass Viewer", layout="centered")
st.title("🌿 Biomass Visualization")
st.markdown("Upload a compressed shapefile (.zip) with your area of interest to explore biomass trends using satellite data.")

# Apply pixelated rendering style
st.markdown(
    """
    <style>
    .no-interpolation {
        image-rendering: pixelated;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Shapefile upload
uploaded_file = st.file_uploader("Select the shapefile (.zip):", type="zip")

if uploaded_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, uploaded_file.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]

        if not shp_files:
            st.error(".shp file not found in the uploaded .zip.")
        else:
            gdf = gpd.read_file(shp_files[0])
            gdf_proj = gdf.to_crs(epsg=4326)

            # Reproject to metric system (area in m²)
            gdf_metric = gdf.to_crs(epsg=32619)
            area_ha = gdf_metric.geometry.area.sum() / 10000
            gdf_proj = gdf.to_crs(epsg=4326)

            # Send to FastAPI
            st.subheader("📤 Request to API and biomass map rendering")
            st.info("⏳ Retrieving spatial information and biomass time series...")

            try:
                response = requests.post("http://localhost:8000/generate-report", files={"shapefile": uploaded_file})

                if response.status_code == 200:
                    result = response.json()

                    pais = result["pais"]
                    zona = result["zona_ecologica"]
                    protegidas = result["areas_protegidas"]

                    st.success("✅ Spatial data successfully retrieved!")

                    st.subheader("📊 Geometry Summary")
                    st.write(f"**Approximate area:** {area_ha:.2f} hectares")
                    st.write(f"**Country:** {pais}")
                    st.write(f"**Ecological zone:** {zona}")
                    if protegidas:
                        st.write("**Intersecting protected areas:**")
                        for nome in protegidas:
                            st.markdown(f"- {nome}")
                    else:
                        st.write("_No protected areas intersect the uploaded geometry._")

                    # 🌍 Show base map only with satellite basemap
                    st.subheader("🗺️ Map view of your area")
                    centroid = gdf_proj.geometry.centroid.iloc[0]
                    center_lat, center_lon = centroid.y, centroid.x
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=None)

                    # Adiciona o tile da Esri
                    folium.TileLayer(
                        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                        attr="Tiles © Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community",
                        name="Esri World Imagery"
                    ).add_to(m)

                    folium.GeoJson(
                        gdf,
                        name="Area of Interest",
                        style_function=lambda x: {
                            "color": "blue",
                            "weight": 2,
                            "fill": False,
                            "fillOpacity": 0
                        }
                    ).add_to(m)

                    folium.LayerControl().add_to(m)
                    st_folium(m, width=700, height=500)

                    # 📈 Biomass time series plot from Planetary Computer
                    st.subheader("📈 Biomass over time (2003–2019)")

                    bounds = gdf_proj.total_bounds  # minx, miny, maxx, maxy
                    bbox = box(*bounds)
                    aoi = gpd.GeoDataFrame(geometry=[bbox], crs="EPSG:4326")

                    catalog = Client.open(
                        "https://planetarycomputer.microsoft.com/api/stac/v1",
                        modifier=planetary_computer.sign_inplace
                    )

                    search = catalog.search(
                        collections=["chloris-biomass"],
                        intersects=bbox,
                        query={"datetime": {"gte": "2002-01-01", "lte": "2020-12-31"}}
                    )

                    items = list(search.get_all_items())
                    if not items:
                        st.warning("⚠️ No biomass data found for this area.")
                    else:
                        biomass_by_year = {}
                        for item in items:
                            year = item.datetime.year
                            if year not in biomass_by_year:
                                asset_href = planetary_computer.sign(item.assets["biomass"].href)
                                ds = rioxarray.open_rasterio(asset_href, masked=True).squeeze()
                                ds = ds.rio.reproject("EPSG:4326")
                                clipped = ds.rio.clip(gdf_proj.geometry, gdf_proj.crs)
                                mean_val = float(clipped.mean().values)
                                biomass_by_year[year] = mean_val

                        # Sort and plot
                        sorted_years = sorted(biomass_by_year.keys())
                        values = [biomass_by_year[yr] for yr in sorted_years]

                        fig, ax = plt.subplots()
                        ax.plot(sorted_years, values, marker="o", markersize=2, color="blue", linewidth=0.4)
                        ax.set_title("Average Aboveground Biomass")
                        ax.set_xlabel("Year")
                        ax.set_ylabel("Biomass (tonnes)")
                        ax.yaxis.grid(True, linewidth=0.3)
                        ax.xaxis.grid(False)
                        
                        st.pyplot(fig)

                else:
                    st.error(f"Error {response.status_code}: {response.text}")

            except requests.exceptions.ConnectionError:
                st.error("❌ Could not connect to the FastAPI server. Make sure it is running at http://localhost:8000")
else:
    st.warning("⬆️ Please upload a .zip file containing your shapefile.")