import osmnx as ox
import pandas as pd

# -------------------------
# 1. Load input CSV
# -------------------------
df = pd.read_csv("Data/Geolocation_Metadata/places_dresden_combined_with_sentences.csv", sep="|")

PLACE_NAME = "Dresden, Germany"

# Keep track of all found entity names
found_entities = set()

# -------------------------
# 2. STREET NETWORK (edges)
# -------------------------
graph = ox.graph_from_place(PLACE_NAME)
nodes, edges = ox.graph_to_gdfs(graph)

edges = edges[edges["name"].notna()]
streets = edges[edges["name"].isin(df["geocode_query"])]

found_entities.update(streets["name"].unique())

streets.to_csv("osm_features/streets.csv")
streets.to_file("osm_features/streets.geojson", driver="GeoJSON")

print("Streets found:", len(streets))

# -------------------------
# 3. SQUARES
# -------------------------
square_tags = {"place": "square"}
squares = ox.features_from_place(PLACE_NAME, square_tags)

if "name" in squares.columns:
    squares = squares[squares["name"].isin(df["geocode_query"])]
    found_entities.update(squares["name"].unique())

squares.to_csv("osm_features/squares.csv")
squares.to_file("osm_features/squares.geojson", driver="GeoJSON")

print("Squares found:", len(squares))

# -------------------------
# 4. BRIDGES
# -------------------------
bridge_tags = {"bridge": True}
bridges = ox.features_from_place(PLACE_NAME, bridge_tags)

if "name" in bridges.columns:
    bridges = bridges[bridges["name"].isin(df["geocode_query"])]
    found_entities.update(bridges["name"].unique())

bridges.to_csv("osm_features/bridges.csv")
bridges.to_file("osm_features/bridges.geojson", driver="GeoJSON")

print("Bridges found:", len(bridges))

# -------------------------
# 5. BUILDINGS
# -------------------------
building_tags = {"building": True}
buildings = ox.features_from_place(PLACE_NAME, building_tags)

if "name" in buildings.columns:
    buildings = buildings[buildings["name"].isin(df["geocode_query"])]
    found_entities.update(buildings["name"].unique())

buildings.to_csv("osm_features/buildings.csv")
buildings.to_file("osm_features/buildings.geojson", driver="GeoJSON")

print("Buildings found:", len(buildings))

# -------------------------
# 6. RIVERS
# -------------------------
river_tags = {"waterway": ["river", "stream", "canal"]}
rivers = ox.features_from_place(PLACE_NAME, river_tags)

if "name" in rivers.columns:
    rivers = rivers[rivers["name"].isin(df["geocode_query"])]
    found_entities.update(rivers["name"].unique())

rivers.to_csv("osm_features/rivers.csv")
rivers.to_file("osm_features/rivers.geojson", driver="GeoJSON")

print("Rivers found:", len(rivers))

# -------------------------
# 7. Add OSM match column to copy of CSV
# -------------------------

df["osm_feature_found"] = df["geocode_query"].isin(found_entities)

df.to_csv("places_dresden_combined_with_sentences_with_osm_flag.csv", index=False, sep="|")

print("Matched entities:", len(found_entities))
print("Updated CSV saved as places_dresden_combined_with_sentences_with_osm_flag.csv")

import osmnx as ox
import geopandas as gpd
import pandas as pd

# --------------------------------------------------
# SETTINGS
# --------------------------------------------------
PLACE_NAME = "Dresden, Germany"
OUTPUT_FOLDER = "osm_features/"

# --------------------------------------------------
# HELPER FUNCTION
# --------------------------------------------------
def export_boundary(query_name, filename, simplify_tolerance=0.0001):
    print(f"Downloading: {query_name}")

    gdf = ox.geocode_to_gdf(query_name)

    # Keep only polygon geometries
    gdf = gdf[gdf.geometry.type.isin(["Polygon", "MultiPolygon"])]

    # Dissolve into single geometry
    gdf = gdf.dissolve()

    # Optional simplification (important for web maps)
    gdf["geometry"] = gdf.simplify(simplify_tolerance)

    gdf.to_file(
        OUTPUT_FOLDER + filename,
        driver="GeoJSON"
    )

    print(f"Saved: {filename}")
    print("CRS:", gdf.crs)
    print("-" * 40)


# ==================================================
# 1 FULL BOUNDARY OF DRESDEN
# ==================================================

export_boundary(
    "Dresden, Germany",
    "dresden_full_boundary.geojson"
)


# ==================================================
# 2 INNER HISTORICAL CORE
# ==================================================

innere_altstadt = ox.geocode_to_gdf("Innere Altstadt, Dresden, Germany")
inner_old = innere_altstadt[innere_altstadt.geometry.type.isin(["Polygon", "MultiPolygon"])]
inner_old = inner_old.dissolve()
inner_old["geometry"] = inner_old.simplify(0.0001)

inner_old.to_file(
    OUTPUT_FOLDER + "innere_altstadt.geojson",
    driver="GeoJSON"
)

print("Saved: innere_altstadt.geojson")

innere_neustadt = ox.geocode_to_gdf("Innere Neustadt, Dresden, Germany")
inner_new = innere_neustadt[innere_neustadt.geometry.type.isin(["Polygon", "MultiPolygon"])]
inner_new = inner_new.dissolve()
inner_new["geometry"] = inner_new.simplify(0.0001)

inner_new.to_file(
    OUTPUT_FOLDER + "innere_neustadt.geojson",
    driver="GeoJSON"
)

print("Saved: innere_neustadt.geojson")

historical_core = gpd.GeoDataFrame(
    pd.concat([innere_altstadt, innere_neustadt], ignore_index=True),
    crs=innere_altstadt.crs
)

historical_core = historical_core[
    historical_core.geometry.type.isin(["Polygon", "MultiPolygon"])
]

historical_core = historical_core.dissolve()
historical_core["geometry"] = historical_core.simplify(0.00005)

historical_core.to_file(
    OUTPUT_FOLDER + "dresden_neustadt_altstadt.geojson",
    driver="GeoJSON"
)

print("Saved: dresden_neustadt_altstadt.geojson")
print("-" * 40)

print("All boundaries exported successfully.")
print("Done.")