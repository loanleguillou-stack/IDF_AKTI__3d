# ============================================
# APP STREAMLIT — CARTE IDF BÂTIMENTS 2.5D
# ============================================

import streamlit as st
import pydeck as pdk
import geopandas as gpd


# ============================================
# 🔐 SÉCURITÉ VIA TOKEN
# ============================================

SECRET_TOKEN = "IDF_MAP_2025_SUPERSECRET"

params = st.experimental_get_query_params()
token = params.get("token", [""])[0]

if token != SECRET_TOKEN:
    st.warning("Accès restreint. Ajoute ?token=IDF_MAP_2025_SUPERSECRET à l’URL.")
    st.stop()


# ============================================
# ⚙️ CONFIG STREAMLIT
# ============================================

st.set_page_config(page_title="IDF Activités – Carte 2.5D", layout="wide")
st.title("🏢 Carte 2.5D – Bâtiments d’activités en Île-de-France")


# ============================================
# 📥 CHARGEMENT DES DONNÉES
# ============================================

@st.cache_data
def load_data():
    gdf = gpd.read_file("bdnb_IDF_FINAL_CLEAN_WITH_LATLON.gpkg")
    gdf = gdf.to_crs(4326)

    # Nouvelle colonne arrondie
    gdf["surface_arrondie"] = gdf["surface_sol_m2"].round().astype(int)

    return gdf

gdf = load_data()


# ============================================
# 🔍 SIDEBAR — FILTRES
# ============================================

st.sidebar.header("🔍 Filtres")

# DEP
departements = sorted(gdf["departement"].dropna().unique())
departement_choice = st.sidebar.multiselect(
    "Départements", options=departements, default=departements
)

# ANNÉE
annees_valides = gdf["annee_construction"].dropna()
if not annees_valides.empty:
    annee_min = int(annees_valides.min())
    annee_max = int(annees_valides.max())
else:
    annee_min, annee_max = 1900, 2025

annee_range = st.sidebar.slider(
    "Année de construction",
    min_value=annee_min,
    max_value=annee_max,
    value=(annee_min, annee_max),
)

# SURFACE
surface_range = st.sidebar.slider(
    "Surface au sol (m²)",
    min_value=float(gdf.surface_sol_m2.min()),
    max_value=float(gdf.surface_sol_m2.max()),
    value=(float(gdf.surface_sol_m2.min()), float(gdf.surface_sol_m2.max())),
)

# HAUTEUR
hauteur_range = st.sidebar.slider(
    "Hauteur (m)",
    min_value=float(gdf.hauteur_m.min()),
    max_value=float(gdf.hauteur_m.max()),
    value=(float(gdf.hauteur_m.min()), float(gdf.hauteur_m.max())),
)

# PROPRIÉTAIRE
proprio_list = sorted(gdf["proprietaire_denomination"].dropna().unique())
proprio_choice = st.sidebar.multiselect(
    "Propriétaire", options=proprio_list, default=proprio_list
)


# ============================================
# 🧮 APPLICATION DES FILTRES
# ============================================


gdf_filtered = gdf.copy()

# Filtre département
gdf_filtered = gdf_filtered[gdf_filtered["departement"].isin(departement_choice)]

# Filtre année si disponible
gdf_filtered = gdf_filtered[
    gdf_filtered["annee_construction"].isna() |
    gdf_filtered["annee_construction"].between(annee_range[0], annee_range[1], inclusive="both")
]

# Filtre surface
gdf_filtered = gdf_filtered[
    gdf_filtered["surface_sol_m2"].isna() |
    gdf_filtered["surface_sol_m2"].between(surface_range[0], surface_range[1], inclusive="both")
]

# Filtre hauteur
gdf_filtered = gdf_filtered[
    gdf_filtered["hauteur_m"].isna() |
    gdf_filtered["hauteur_m"].between(hauteur_range[0], hauteur_range[1], inclusive="both")
]

# Filtre propriétaire
gdf_filtered = gdf_filtered[
    gdf_filtered["proprietaire_denomination"].isna() |
    gdf_filtered["proprietaire_denomination"].isin(proprio_choice)
]



# ============================================
# 🧭 VUE INITIALE
# ============================================

view = pdk.ViewState(
    longitude=gdf["lon"].mean(),
    latitude=gdf["lat"].mean(),
    zoom=10,
    pitch=50,
)


# ============================================
# 🏷️ TOOLTIP (corrigé)
# ============================================

tooltip = {
    "html": """
    <b>Surface au sol :</b> {surface_arrondie} m²<br>
    <b>Hauteur :</b> {hauteur_m} m<br>
    <b>Année de construction :</b> {annee_construction}<br>
    <b>Propriétaire :</b> {proprietaire_denomination}<br>
    <b>Adresse :</b> {libelle_adresse}
    """,
    "style": {"backgroundColor": "black", "color": "white"}
}


# ============================================
# 🗺️ FOND DE CARTE
# ============================================

st.sidebar.subheader("🗺️ Fond de carte")

basemap_choice = st.sidebar.selectbox(
    "Choisir le fond :",
    ["Clair (Positron)", "Sombre (Darkmatter)"]
)

if basemap_choice == "Clair (Positron)":
    basemap = "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
else:
    basemap = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"


# ============================================
# 🚗 ROUTES — GEOJSON (couleurs dynamiques)
# ============================================

roads_path = r"C:\Users\loanl\OneDrive\Bureau\Cartographie bâtiment d'activités IDF\output\rrir_national_iledefrance_wgs84 (1).geojson"
roads = gpd.read_file(roads_path).to_crs(4326)

# Couleur dynamique selon le fond
route_color = "[0, 0, 0]" if basemap_choice == "Clair (Positron)" else "[255, 255, 255]"

roads_layer = pdk.Layer(
    "GeoJsonLayer",
    roads.__geo_interface__,
    stroked=True,
    filled=False,
    get_line_color=route_color,
    get_line_width=40,
    opacity=1.0,
    pickable=False,
)


# ============================================
# 🏢 BÂTIMENTS (vert foncé BNP + filtres)
# ============================================

batiments_layer = pdk.Layer(
    "GeoJsonLayer",
    gdf_filtered.__geo_interface__,
    opacity=0.85,
    stroked=False,
    filled=True,
    extruded=True,
    get_elevation="properties.hauteur_m",
    get_fill_color="[0, 95, 60, 220]",  # 🌿 Vert BNP
    pickable=True,
)


# ============================================
# 🧩 ASSEMBLAGE FINAL
# ============================================

deck = pdk.Deck(
    layers=[roads_layer, batiments_layer],
    initial_view_state=view,
    tooltip=tooltip,
    map_style=basemap,
)

st.pydeck_chart(deck)

st.success("Carte interactive chargée avec succès 🚀")

