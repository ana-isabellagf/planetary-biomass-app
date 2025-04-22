from fastapi import FastAPI, UploadFile, Form, File
from fastapi.responses import FileResponse, JSONResponse
from shapely.geometry import shape
import geopandas as gpd
from pystac_client import Client
import planetary_computer
from sqlalchemy import create_engine, text
import rioxarray
import tempfile
import zipfile
import os

# PostgreSQL connection string
engine = create_engine("postgresql://postgres:admin@localhost:5432/ecohub_test")

app = FastAPI()

def read_shapefile(upload_file: UploadFile):
    # Extract zipped shapefile
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, upload_file.filename)
        with open(zip_path, "wb") as f:
            f.write(upload_file.file.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        # Read with geopandas
        shp_files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
        if not shp_files:
            raise ValueError("Invalid shapefile or missing .shp file")
        return gpd.read_file(shp_files[0])

def get_spatial_info(gdf, engine):
    gdf = gdf.to_crs("EPSG:4326")
    geom_wkt = gdf.geometry.unary_union.wkt

    with engine.connect() as conn:
        # País
        pais = conn.execute(text("""
            SELECT name FROM country_name
            WHERE ST_Intersects(ST_GeomFromText(:geometry, 4326), geometry)
            LIMIT 1
        """), {"geometry": geom_wkt}).scalar()

        # Zona ecológica
        zona = conn.execute(text("""
            SELECT gez_name FROM ecological_zone
            WHERE ST_Intersects(ST_GeomFromText(:geometry, 4326), geometry)
            LIMIT 1
        """), {"geometry": geom_wkt}).scalar()

        # Áreas protegidas
        protegidas = conn.execute(text("""
            SELECT desig_eng FROM protected_areas
            WHERE ST_Intersects(ST_GeomFromText(:geometry, 4326), geometry)
            LIMIT 5
        """), {"geometry": geom_wkt}).fetchall()

    return {
        "pais": pais or "Não identificado",
        "zona_ecologica": zona or "Não identificado",
        "areas_protegidas": [p[0] for p in protegidas] if protegidas else []
    }

@app.post("/generate-report")
async def generate_report(
    shapefile: UploadFile = File(...)
):
    # 1. Read uploaded shapefile
    gdf = read_shapefile(shapefile)
    gdf = gdf.to_crs("EPSG:4326")

    # 2. Connect to STAC catalog
    catalog = Client.open(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        modifier=planetary_computer.sign_inplace
    )

    # 3. Search for biomass data (chloris)
    daterange = {"interval": ["2015-06-30T00:00:00Z", "2019-07-30T00:00:00Z"]}
    search = catalog.search(filter_lang="cql2-json", filter={
        "op": "and",
        "args": [
            {"op": "anyinteracts", "args": [{"property": "datetime"}, daterange]},
            {"op": "=", "args": [{"property": "collection"}, "chloris-biomass"]}
        ]
    })

    items = list(search.items())
    if not items:
        return {"error": "No image found for this area."}

    item = items[0]
    asset_href = planetary_computer.sign(item.assets["biomass"].href)

    # 4. Open and reproject raster
    raster = rioxarray.open_rasterio(asset_href, masked=True)
    raster = raster.rio.reproject("EPSG:4326")

    # 5. Clip raster with buffered geometry
    gdf_buffered = gdf.buffer(0.09)
    clipped = raster.rio.clip(gdf_buffered.geometry)

    # 6. Save clipped raster as GeoTIFF
    with tempfile.NamedTemporaryFile(suffix=".tif", delete=False) as tmpfile:
        clipped.rio.to_raster(tmpfile.name)

        # 7. Get extra spatial info from PostGIS
        info = get_spatial_info(gdf, engine)

        return {
            "tif_path": tmpfile.name,
            "pais": info["pais"],
            "zona_ecologica": info["zona_ecologica"],
            "areas_protegidas": info["areas_protegidas"]
        }