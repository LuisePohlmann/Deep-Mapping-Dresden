import osmnx as ox
import pandas as pd
from rapidfuzz import process, fuzz

# -------------------------
# Load input CSV
# -------------------------
df = pd.read_csv("Data/Geolocation_Metadata/places_dresden_combined_with_sentences.csv", sep="|")

PLACE_NAME = "Dresden, Germany"

# Keep track of all found entity names
found_entities = set()

#--------------------------
# Fuzzy matching
#--------------------------
def fuzzy_match_entities(query_list, candidate_list, threshold=80):
    """
    Fuzzy matches historical spellings to OSM names.

    Returns list of matched names.
    """

    matches = []

    for query in query_list:

        if pd.isna(query):
            continue

        result = process.extractOne(
            query,
            candidate_list,
            scorer=fuzz.token_sort_ratio
        )

        if result and result[1] >= threshold:
            matches.append(result[0])

    return list(set(matches))

# -------------------------
# STREET NETWORK (edges)
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
# SQUARES
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
# BRIDGES
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
# BUILDINGS
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

historic_buildings.to_csv("osm_features/historic_buildings.csv")
historic_buildings.to_file(
    "osm_features/historic_buildings.geojson",
    driver="GeoJSON"
)

print("Historic buildings found:", len(historic_buildings))

# -------------------------
# RIVERS
# -------------------------
river_tags = {"waterway": ["river", "stream", "canal"]}
rivers = ox.features_from_place(PLACE_NAME, river_tags)

if "name" in rivers.columns:
    rivers = rivers[rivers["name"].isin(df["geocode_query"])]
    found_entities.update(rivers["name"].unique())

rivers.to_csv("osm_features/rivers.csv")
rivers.to_file("osm_features/rivers.geojson", driver="GeoJSON")

print("Rivers found:", len(rivers))

water_tags = {
    "natural": ["water", "wetland"],
    "water": ["lake", "reservoir"]
}

water = ox.features_from_place(PLACE_NAME, water_tags)

if "name" in water.columns:
    water = water[water["name"].isin(df["geocode_query"])]
    found_entities.update(water["name"].unique())

water.to_csv("osm_features/water.csv")
water.to_file("osm_features/water.geojson", driver="GeoJSON")

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
    parks = parks[parks["name"].isin(df["geocode_query"])]
    found_entities.update(parks["name"].unique())

parks.to_csv("osm_features/parks.csv")
parks.to_file("osm_features/parks.geojson", driver="GeoJSON")

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
    districts = districts[districts["name"].isin(df["geocode_query"])]
    found_entities.update(districts["name"].unique())

districts.to_csv("osm_features/districts.csv")
districts.to_file("osm_features/districts.geojson", driver="GeoJSON")

print("Districts / neighborhoods found:", len(districts))

# -------------------------
# Add OSM match column to copy of CSV
# -------------------------
all_osm_names = list(found_entities)
df_unique_queries = df["geocode_query"].dropna().unique()

fuzzy_matches = fuzzy_match_entities(
    df_unique_queries,
    all_osm_names,
    threshold=85   # increase = stricter matching
)

df["osm_feature_found"] = df["geocode_query"].apply(
    lambda x: x in fuzzy_matches
)

df.to_csv("places_dresden_combined_with_sentences_with_osm_flag.csv", index=False, sep="|")

print("Matched entities:", len(found_entities))
print("Updated CSV saved as places_dresden_combined_with_sentences_with_osm_flag.csv")

print("All boundaries exported successfully.")
print("Done.")