# Biomass Analysis App with Streamlit & FastAPI

This application allows users to upload a shapefile (`.zip`) and explore aboveground biomass trends using the **Microsoft Planetary Computer** and custom spatial queries from a **PostGIS** database. It is composed of:

- A **FastAPI** backend that handles file uploads, spatial analysis, and biomass extraction
- A **Streamlit** frontend that visualizes the results, including maps and time series
- Integration with [Planetary Computer](https://planetarycomputer.microsoft.com/) for biomass data

---

## How It Works

1. User uploads a shapefile via Streamlit UI
2. Streamlit sends the shapefile to a FastAPI endpoint
3. The backend:
   - Clips biomass rasters using the AOI
   - Computes mean biomass by year
   - Queries spatial metadata (country, ecological zone, protected areas) from PostGIS
4. The results are returned and visualized on the map and time series chart

---

## Project Structure

```
planetary-biomass-app/
├── app/
│   └── biomass_api.py              # FastAPI backend service
├── streamlit_app/
│   └── biomass_viewer.py           # Streamlit interface
├── scripts/
│   └── start_services.bat          # Starts both services (API + Streamlit)
├── data/
│   └── boundaries.zip              # Example shapefile (zipped)
├── requirements.txt                # Project dependencies
└── README.md
```

---

## How to Run

### 1. Create and activate environment

```bash
conda create -n fastapi-env python=3.12
conda activate fastapi-env
pip install -r requirements.txt
```

### 2. Launch the application

Use the batch script:

```bash
scripts/start_services.bat
```

This will:
- Start FastAPI at `http://localhost:8000`
- Open Streamlit UI at `http://localhost:8501`

---

## Example Result

- Biomass values from the **Chloris-biomass** dataset (2003–2019)
- Map rendered with **Esri World Imagery** and uploaded AOI
- Time series plot generated from mean biomass per year
- Additional info:
  - Country name
  - Ecological zone
  - Overlapping protected areas

---

## Data Sources

- **Microsoft Planetary Computer** — [Chloris-biomass](https://planetarycomputer.microsoft.com/catalog/chloris-biomass)
- **PostGIS** — Spatial layers: countries, protected areas, ecological zones

> The Chloris biomass data is accessed under the Planetary Computer terms of use and is subject to the license terms of the respective dataset providers.

---

## Author

**Ana Isabella Guimarães Ferreira**  
🌱 GIS and Remote Sensing Specialist  
📧 aisabellaguimaraesf@gmail.com  
🔗 [LinkedIn](https://www.linkedin.com/in/ana-isabella-g-ferreira)

---

## License

This project is licensed under the [MIT License](LICENSE).