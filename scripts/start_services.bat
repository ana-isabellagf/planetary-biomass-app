@echo off
cd /d "%~dp0..\app"
start cmd /k "conda activate fastapi-env && uvicorn biomass_api:app --reload"
cd /d "%~dp0..\streamlit_app"
start cmd /k "conda activate fastapi-env && streamlit run biomass_viewer.py"
