# ============================================
# APP STREAMLIT — CARTE IDF BÂTIMENTS 2.5D
# COMPATIBLE STREAMLIT CLOUD (sans GeoPandas)
# ============================================

import streamlit as st
import pydeck as pdk
import json
import numpy as np


# ============================================
# 🔐 SÉCURITÉ VIA TOKEN
# ============================================

SECRET_TOKEN = "IDF_MAP_2025_SUPERSECRET"

params = st.experimental_get_query_params()
token = params.get("token", [""])[0]

if token != SECRET_TOKEN:
    st.warning("Accès restreint. Ajoute ?token=IDF_MAP_2025_SUPERSECRET dans l’URL.")
    st.stop()


# ============================================
# ⚙️ CONFIG STREAMLIT
# ============================================

st.set_page_config(page_title="IDF Activités – Carte 2.5D", layout="wide")
st.title("🏢 Carte 2.5D – Bâtiments d’activités en Île-de-France")


# ============================================
# 📥 CHARGEMENT DONNÉES GEOJSON (sans geopandas)
# ============================================

@st.cache_data
def load_geojson(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


batiments = load_geojson("bdnb_IDF_FINAL_CLEAN_WITH_LATLON.geojson")
routes = load_geojson("rrir_national_iledefrance_wgs84 (1).geojson")


# ============================================
# 🧭 CALCUL DU CENTRE DE LA VUE
# ============================================

coords = []

for feat in batiments["features"]:
    geom = feat["geometry"]
    if geom["type"] == "Polygon":
        coords.extend(geom["coordinates"][0])
    elif geom["type"] == "MultiPolygon":
        for polygon in geom["coordinates"]:
            coords.extend(polygon[0])

coord_arr = np.array(coords)
lon_mean, lat_mean = np.mean(coord_arr[:, 0]), np.mean(coord_arr[:, 1])


view = pdk.ViewState(
    longitude=lon_mean,
    latitude=lat_mean,
    zoom=10,
    pitch=50,
)


# ============================================
# 🗺️ CHOIX FOND DE CARTE (SIDEBAR)
# ============================================

st.sidebar.subheader("🗺️ Fond de carte")

basemap_choice = st.sidebar.selectbox(
    "Choisir le fond :",
    ["Clair (Positron)", "Sombre (Darkmatter)"]
)

if basemap_choice == "Clair (Positron)":
    basemap = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
    routes_color = "[0, 0, 0]"
else:
    basemap = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
    routes_color = "[255, 255, 255]"


# ============================================
# 🏢 FILTRES (année construction / surface)
# ============================================

filtered_features = []
for f in batiments["features"]:

    props = f["properties"]

    year = props.get("annee_construction")
    surf = props.get("surface_sol_m2", 0)

    # 1️⃣ Filtre surface (obligatoire)
    if surf < surface_min:
        continue

    # 2️⃣ Filtre année uniquement si elle existe
    if year is not None:
        if not (year_range[0] <= year <= year_range[1]):
            continue

    # 3️⃣ Sinon on garde le bâtiment
    filtered_features.append(f)



surface_min = st.sidebar.number_input("Surface minimum (m²)", 0, 1000000, 0)

# Filtrage des features
filtered_features = []
for f in batiments["features"]:

    props = f["properties"]

    year = props.get("annee_construction")
    surf = props.get("surface_sol_m2", 0)

    if year is None:
        continue

    if year_range[0] <= year <= year_range[1] and surf >= surface_min:
        filtered_features.append(f)

batiments_filtered = {
    "type": "FeatureCollection",
    "features": filtered_features
}


# ============================================
# 🏷️ TOOLTIP
# ============================================

tooltip = {
    "html": """
    <b>Surface au sol :</b> {surface_sol_m2} m²<br>
    <b>Hauteur :</b> {hauteur_m} m<br>
    <b>Année de construction :</b> {annee_construction}<br>
    <b>Propriétaire :</b> {proprietaire_denomination}<br>
    <b>Adresse :</b> {libelle_adresse}
    """,
    "style": {"backgroundColor": "black", "color": "white"}
}


# ============================================
# 🚗 LAYER ROUTES
# ============================================

routes_layer = pdk.Layer(
    "GeoJsonLayer",
    routes,
    stroked=True,
    filled=False,
    get_line_color=routes_color,
    get_line_width=30,
    opacity=1.0,
    pickable=False,
)


# ============================================
# 🏢 LAYER BÂTIMENTS 2.5D
# ============================================

batiments_layer = pdk.Layer(
    "GeoJsonLayer",
    batiments_filtered,
    opacity=0.9,
    stroked=False,
    filled=True,
    extruded=True,
    get_elevation="properties.hauteur_m * 1.5",
    get_fill_color="[1, 89, 38, 200]",   # vert foncé BNP 💚
    pickable=True,
)


# ============================================
# 🧩 ASSEMBLAGE FINAL
# ============================================

deck = pdk.Deck(
    layers=[routes_layer, batiments_layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style=basemap,
)

st.pydeck_chart(deck)

st.success("🚀 Carte interactive chargée avec succès !")
