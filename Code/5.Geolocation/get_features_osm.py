import osmnx as ox
import pandas as pd
# -------------------------
# Load input CSV
# -------------------------
df = pd.read_excel("Data/Data_hand_normalized.xlsx")
df = df.dropna(subset=["Entity_normed"])
df = df[df["Entity_normed"] != "Sachsens"]

PLACE_NAME = "Dresden, Germany"
# Get city center point
city_point = ox.geocode(PLACE_NAME)

# radius in meters
SEARCH_RADIUS = 15000

# Keep track of all found entity names
found_entities = set()

# -------------------------
# Safe export helper
# -------------------------
def safe_export(gdf, csv_path, geojson_path):
    """
    Prevents 'ValueError: cannot convert float NaN to integer'
    by converting problematic columns before saving.
    """

    if gdf is None or len(gdf) == 0:
        print(f"Skipping export: {geojson_path} (empty dataset)")
        return

    gdf = gdf.copy()

    # Convert integer columns with NaN to float
    for col in gdf.columns:
        if pd.api.types.is_integer_dtype(gdf[col]):
            gdf[col] = gdf[col].astype("float")

    # Fill object NaNs with empty string (safer for GeoJSON)
    obj_cols = gdf.select_dtypes(include=["object"]).columns
    gdf[obj_cols] = gdf[obj_cols].fillna("")

    # Save
    gdf.to_csv(csv_path)
    gdf.to_file(geojson_path, driver="GeoJSON")

# -------------------------
# SURROUNDING TOWNS / VILLAGES
# -------------------------
town_tags = {
    "place": ["town", "village", "city"]
}

towns = ox.features_from_point(city_point, town_tags, dist=SEARCH_RADIUS)

if "name" in towns.columns:
    valid_entities = df.loc[df["Entity_normed"] != "Dresden", "Entity_normed"]
    towns = towns[towns["name"].isin(valid_entities)]
    found_entities.update(towns["name"].unique())

safe_export(
    towns,
    "Data/osm_features/towns.csv",
    "Data/osm_features/towns.geojson"
)

print("Towns / villages found:", len(towns))

# -------------------------
# STREET NETWORK (edges)
# -------------------------
graph = ox.graph_from_place(PLACE_NAME)
nodes, edges = ox.graph_to_gdfs(graph)

edges = edges[edges["name"].notna()]
streets = edges[edges["name"].isin(df["Entity_normed"])]

found_entities.update(streets["name"].unique())

safe_export(
    streets,
    "Data/osm_features/streets.csv",
    "Data/osm_features/streets.geojson"
)

print("Streets found:", len(streets))

# -------------------------
# CHURCHES
# -------------------------
church_tags = {
    "amenity": "place_of_worship",
    "building": ["church", "chapel", "cathedral"]
}

churches = ox.features_from_place(PLACE_NAME, church_tags)

if "name" in churches.columns:
    churches = churches[churches["name"].isin(df["Entity_normed"])]
    found_entities.update(churches["name"].unique())

safe_export(
    churches,
    "Data/osm_features/churches.csv",
    "Data/osm_features/churches.geojson"
)

print("Churches found:", len(churches))

# -------------------------
# SQUARES
# -------------------------
square_tags = {"place": "square"}
squares = ox.features_from_place(PLACE_NAME, square_tags)

if "name" in squares.columns:
    squares = squares[squares["name"].isin(df["Entity_normed"])]
    found_entities.update(squares["name"].unique())

safe_export(
    squares,
    "Data/osm_features/squares.csv",
    "Data/osm_features/squares.geojson"
)

print("Squares found:", len(squares))

# -------------------------
# BRIDGES
# -------------------------
bridge_tags = {"bridge": True}
bridges = ox.features_from_place(PLACE_NAME, bridge_tags)

if "name" in bridges.columns:
    bridges = bridges[bridges["name"].isin(df["Entity_normed"])]
    found_entities.update(bridges["name"].unique())

safe_export(
    bridges,
    "Data/osm_features/bridges.csv",
    "Data/osm_features/bridges.geojson"
)

print("Bridges found:", len(bridges))

# -------------------------
# BUILDINGS
# -------------------------
building_tags = {"building": True}
buildings = ox.features_from_place(PLACE_NAME, building_tags)

if "name" in buildings.columns:
    buildings = buildings[buildings["name"].isin(df["Entity_normed"])]
    found_entities.update(buildings["name"].unique())

safe_export(
    buildings,
    "Data/osm_features/buildings.csv",
    "Data/osm_features/buildings.geojson"
)
print("Buildings found:", len(buildings))

# -------------------------
# HISTORIC BUILDINGS
# -------------------------

historic_tags = {
    "historic": True
}

historic_buildings = ox.features_from_place(PLACE_NAME, historic_tags)

# Optional filtering by your dataset names
if "name" in historic_buildings.columns:
    historic_buildings = historic_buildings[
        historic_buildings["name"].notna()
    ]

    # Fuzzy matching will be applied later (do NOT filter strictly here)
    found_entities.update(historic_buildings["name"].dropna().unique())

safe_export(
    historic_buildings,
    "Data/osm_features/historic_buildings.csv",
    "Data/osm_features/historic_buildings.geojson"
)

print("Historic buildings found:", len(historic_buildings))

# -------------------------
# RIVERS
# -------------------------
river_tags = {"waterway": ["river", "stream", "canal"]}
rivers = ox.features_from_place(PLACE_NAME, river_tags)

if "name" in rivers.columns:
    rivers = rivers[rivers["name"].isin(df["Entity_normed"])]
    found_entities.update(rivers["name"].unique())

safe_export(
    rivers,
    "Data/osm_features/rivers.csv",
    "Data/osm_features/rivers.geojson"
)

print("Rivers found:", len(rivers))

water_tags = {
    "natural": ["water", "wetland"],
    "water": ["lake", "reservoir"]
}

water = ox.features_from_place(PLACE_NAME, water_tags)

if "name" in water.columns:
    water = water[water["name"].isin(df["Entity_normed"])]
    found_entities.update(water["name"].unique())

safe_export(
    water,
    "Data/osm_features/water.csv",
    "Data/osm_features/water.geojson"
)

print("Water bodies found:", len(water))

# -------------------------
# GREEN AREAS / PARKS
# -------------------------
green_tags = {
    "leisure": ["park", "garden", "recreation_ground"],
    "landuse": ["grass", "forest"]
}

parks = ox.features_from_place(PLACE_NAME, green_tags)

if "name" in parks.columns:
    parks = parks[parks["name"].isin(df["Entity_normed"])]
    found_entities.update(parks["name"].unique())

safe_export(
    parks,
    "Data/osm_features/parks.csv",
    "Data/osm_features/parks.geojson"
)

print("Parks / green areas found:", len(parks))

# -------------------------
# CITY DISTRICTS / QUARTERS
# -------------------------
district_tags = {
    "boundary": "administrative",
    "place": ["neighbourhood", "suburb", "quarter"]
}

districts = ox.features_from_place(PLACE_NAME, district_tags)

if "name" in districts.columns:
    districts = districts[districts["name"].isin(df["Entity_normed"])]
    found_entities.update(districts["name"].unique())

safe_export(
    districts,
    "Data/osm_features/districts.csv",
    "Data/osm_features/districts.geojson"
)

print("Districts / neighborhoods found:", len(districts))

# -------------------------
# Add OSM match column to CSV
# -------------------------
all_osm_names = set(found_entities)

df["osm_feature_found"] = df["Entity_normed"].isin(all_osm_names)

# Ensure Dresden is always treated as having no OSM feature
df.loc[df["Entity_normed"] == "Dresden", "osm_feature_found"] = False

df.to_csv(
    "Data/places_dresden_combined_with_sentences_with_osm_flag.csv",
    index=False,
    sep="|"
)

print("Matched entities:", len(all_osm_names))
print("Rows with OSM match:", df["osm_feature_found"].sum())
print("Updated CSV saved as places_dresden_combined_with_sentences_with_osm_flag.csv")

print("All boundaries exported successfully.")
print("Done.")
