# ============================================
# APP STREAMLIT — CARTE IDF BÂTIMENTS 2.5D
# CLOUD READY (no GeoPandas)
# ============================================

import streamlit as st
import pydeck as pdk
import json
import numpy as np
import os

# ---------- Security (URL token) ----------
SECRET_TOKEN = "IDF_MAP_2025_SUPERSECRET"
params = st.experimental_get_query_params()
token = params.get("token", [""])[0]
if token != SECRET_TOKEN:
    st.warning("Accès restreint. Ajoute ?token=IDF_MAP_2025_SUPERSECRET dans l’URL.")
    st.stop()

# ---------- Page config ----------
st.set_page_config(page_title="IDF Activités – Carte 2.5D", layout="wide")
st.title("🏢 Carte 2.5D – Bâtiments d’activités en Île-de-France")

# ---------- Helpers ----------
@st.cache_data
def load_geojson(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def safe_float(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

# ---------- Load data ----------
BATI_FILE = "bdnb_IDF_FINAL_CLEAN_WITH_LATLON.geojson"
ROADS_FILE = "rrir_national_iledefrance_wgs84 (1).geojson"

try:
    batiments = load_geojson(BATI_FILE)
except FileNotFoundError:
    st.error(f"Fichier introuvable : {BATI_FILE}")
    st.stop()

roads = None
if os.path.exists(ROADS_FILE):
    try:
        roads = load_geojson(ROADS_FILE)
    except Exception:
        roads = None  # on ignore les erreurs de routes

# ---------- Compute map center ----------
coords = []
for feat in batiments.get("features", []):
    geom = feat.get("geometry", {})
    if not geom:
        continue
    gtype = geom.get("type")
    if gtype == "Polygon":
        coords.extend(geom["coordinates"][0])
    elif gtype == "MultiPolygon":
        for polygon in geom["coordinates"]:
            coords.extend(polygon[0])

if coords:
    coord_arr = np.array(coords, dtype="float64")
    lon_mean, lat_mean = float(np.mean(coord_arr[:, 0])), float(np.mean(coord_arr[:, 1]))
else:
    # fallback center IDF
    lon_mean, lat_mean = 2.35, 48.85

view = pdk.ViewState(longitude=lon_mean, latitude=lat_mean, zoom=10, pitch=50)

# ---------- Basemap ----------
st.sidebar.subheader("🗺️ Fond de carte")
basemap_choice = st.sidebar.selectbox("Choisir le fond :", ["Clair (Positron)", "Sombre (Darkmatter)"])
if basemap_choice == "Clair (Positron)":
    basemap = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    routes_color = "[0, 0, 0]"
else:
    basemap = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    routes_color = "[255, 255, 255]"

# ---------- Filters ----------
st.sidebar.subheader("🎚️ Filtres")
min_year, max_year = 1900, 2030
year_range = st.sidebar.slider("Année de construction", min_year, max_year, (min_year, max_year))
surface_min = st.sidebar.number_input("Surface minimum (m²)", min_value=0, max_value=1_000_000, value=0)

include_no_year = st.sidebar.checkbox("Inclure les bâtiments sans année", value=True)

# ---------- Apply filters (tolerant to NA) ----------
filtered_features = []
for f in batiments.get("features", []):
    props = f.get("properties", {})

    # Surface (treat missing as 0)
    surf = safe_float(props.get("surface_sol_m2"), default=0.0)
    if surf is None or surf < float(surface_min):
        continue

    # Year (filter only if we have a valid number)
    year = props.get("annee_construction")
    year_val = None
    if year is not None:
        year_val = safe_float(year)
    if year_val is None:
        # no year information
        if not include_no_year:
            continue
    else:
        if not (year_range[0] <= year_val <= year_range[1]):
            continue

    filtered_features.append(f)

batiments_filtered = {"type": "FeatureCollection", "features": filtered_features}

# ---------- Tooltip ----------
tooltip = {
    "html": """
    <b>Surface au sol :</b> {surface_sol_m2} m²<br>
    <b>Hauteur :</b> {hauteur_m} m<br>
    <b>Année de construction :</b> {annee_construction}<br>
    <b>Propriétaire :</b> {proprietaire_denomination}<br>
    <b>Adresse :</b> {libelle_adresse}
    """,
    "style": {"backgroundColor": "black", "color": "white"},
}

# ---------- Layers ----------
layers = []

if roads:
    roads_layer = pdk.Layer(
        "GeoJsonLayer",
        roads,
        stroked=True,
        filled=False,
        get_line_color=routes_color,
        get_line_width=30,
        opacity=1.0,
        pickable=False,
    )
    layers.append(roads_layer)

batiments_layer = pdk.Layer(
    "GeoJsonLayer",
    batiments_filtered,
    opacity=0.9,
    stroked=False,
    filled=True,
    extruded=True,
    get_elevation="properties.hauteur_m * 1.5",
    get_fill_color="[1, 89, 38, 200]",  # vert foncé BNP
    pickable=True,
)
layers.append(batiments_layer)

# ---------- Deck ----------
deck = pdk.Deck(layers=layers, initial_view_state=view, tooltip=tooltip, map_style=basemap)
st.pydeck_chart(deck)
st.success("🚀 Carte interactive chargée avec succès !")
