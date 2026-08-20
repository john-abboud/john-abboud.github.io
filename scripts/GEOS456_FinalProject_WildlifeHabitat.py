#-------------------------------------------------------------------------------
# Name:        Final Project: Connecting Wildlife Habitat
# Purpose:     The purpose of this assignment is to incorporate Python functionality
#              learned throughout the semester, including data management,
#              data conversion, selections, spatial analyses using raster datasets,
#              vector datasets and mapping automation using arcpy.
#
# Author:      John Abboud
# Created:     03/08/2026
#-------------------------------------------------------------------------------



# Import the arcpy module
import arcpy
import os
import gc

# Set environment workspace and overwrite properties
arcpy.env.workspace = r"C:\GEOS456\FinalProject"
arcpy.env.overwriteOutput = True

# Root project folder - everything below references this location
root = r"C:\GEOS456\FinalProject"
gdb = os.path.join(root, "KananaskisWildlife.gdb")

# Spatial reference object used throughout the script
# NAD_1983_UTM_Zone_11N - the project's target projection
UTM11N = arcpy.SpatialReference(26911)

# Helper function used after every geoprocessing tool
# prints the first and last message returned by the most recently run tool
def print_messages():
    msgCount = arcpy.GetMessageCount()
    if msgCount > 0:
        print(arcpy.GetMessage(0))
        print(arcpy.GetMessage(msgCount - 1))


# Check if the assignment geodatabase already exists.
# If it exists, delete it prior to making a new one.

print("Checking for an existing KananaskisWildlife.gdb")

arcpy.env.workspace = root

if arcpy.Exists(gdb):
    arcpy.management.Delete(gdb)
    print_messages()
    print("Existing KananaskisWildlife.gdb was found and deleted")
else:
    print("No existing KananaskisWildlife.gdb was found")
print("")


# Create the file geodatabase and feature datasets to store the data

print("Creating KananaskisWildlife.gdb and feature datasets")

arcpy.management.CreateFileGDB(root, "KananaskisWildlife.gdb")
print_messages()
print("KananaskisWildlife.gdb created")
print("")

# Kananaskis = base/context layers, Wildlife = habitat + analysis outputs,
# Reference = administrative/index grids (townships, NTS map sheets)
fds_list = ["Kananaskis", "Wildlife", "Reference"]
for fds in fds_list:
    arcpy.management.CreateFeatureDataset(gdb, fds, UTM11N)
    print_messages()
print("Feature datasets created: Kananaskis, Wildlife, Reference")
print("")


# List of every raw data folder that contains shapefiles for this assignment,
# and dictionary mapping each raw shapefile name to its feature dataset and
# clean output name in the geodatabase

raw_vector_folders = [
    os.path.join(root, "ATS"),
    os.path.join(root, "Kananaskis"),
    os.path.join(root, "Landcover"),
    os.path.join(root, "NTS", "NTS-50"),
    os.path.join(root, "Wildlife")
]

raw_raster_folders = [
    os.path.join(root, "dem")
]

fds_assignment = {
    "KCountry_Bound": ("Kananaskis", "Park_Boundary"),
    "Road":           ("Kananaskis", "Roads"),
    "Trails":         ("Kananaskis", "Trails"),
    "Hydro":          ("Kananaskis", "Hydro"),
    "Transportation": ("Kananaskis", "Transportation"),
    "AB_Landcover":   ("Kananaskis", "AB_Landcover"),
    "Bear_Habitat":   ("Wildlife", "Bear_Habitat"),
    "ESA":            ("Wildlife", "ESA"),
    "AB_Township":    ("Reference", "AB_Township"),
    "NTS50":          ("Reference", "NTS_50")
}


# Import and project all vector layers into the geodatabase.
# Each shapefile's spatial reference is checked at runtime: layers already in
# UTM 11N are copied as-is, everything else is projected.

print("Copying/projecting vector layers into KananaskisWildlife.gdb...")
for folder in raw_vector_folders:
    arcpy.env.workspace = folder
    fcList = arcpy.ListFeatureClasses() or []
    print("Folder:", folder)

    for fc in fcList:
        fcDesc = arcpy.Describe(fc)
        fc_name = os.path.splitext(fc)[0]
        print("    Name:", fc)
        print("        Shape Type:", fcDesc.shapeType)
        print("        Spatial Reference:", fcDesc.spatialReference.name)

        if fc_name not in fds_assignment:
            print(f"        Skipping {fc_name}, no feature dataset assigned")
            continue

        target_fds, out_name = fds_assignment[fc_name]
        out_path = os.path.join(gdb, target_fds, out_name)

        # factoryCode 26911 = NAD83 UTM Zone 11N
        if fcDesc.spatialReference.factoryCode == 26911:
            arcpy.management.CopyFeatures(fc, out_path)
        else:
            arcpy.management.Project(fc, out_path, UTM11N)
        print_messages()
    print("")


# Import and project the DEM into the geodatabase, resampled to 25m

print("Copying/projecting DEM into KananaskisWildlife.gdb...")
for folder in raw_raster_folders:
    arcpy.env.workspace = folder
    rasList = arcpy.ListRasters() or []
    print("Folder:", folder)

    for ras in rasList:
        rasDesc = arcpy.Describe(ras)
        out_path = os.path.join(gdb, "DEM")
        print("    Name:", ras)
        print("        Spatial Reference:", rasDesc.spatialReference.name)
        print("        Cell Size:", rasDesc.meanCellWidth)

        if rasDesc.spatialReference.factoryCode == 26911:
            arcpy.management.CopyRaster(ras, out_path)
        else:
            # BILINEAR resampling for continuous elevation data
            arcpy.management.ProjectRaster(ras, out_path, UTM11N, "BILINEAR", 25)
        print_messages()
    print("")

# Reset the workspace to the geodatabase now that the folder-by-folder import
# loops above are done, so any tool with an unspecified output defaults safely
# into the gdb instead of the last raw data folder
arcpy.env.workspace = gdb


# Clip all layers to the Kananaskis Park Boundary.
# Physical/context layers get a hard Clip. Reference grids (townships, NTS
# sheets) use Select by Location instead, so whole units are kept rather than
# sliced at the boundary edge.

boundary = os.path.join(gdb, "Kananaskis", "Park_Boundary")

print("Clipping vector layers to the park boundary...")

clip_targets = {
    "Kananaskis": ["Roads", "Trails", "Hydro", "Transportation", "AB_Landcover"],
    "Wildlife": ["Bear_Habitat", "ESA"]
}

for fds, layers in clip_targets.items():
    for layer in layers:
        in_fc = os.path.join(gdb, fds, layer)
        out_fc = os.path.join(gdb, fds, layer + "_Clip")
        arcpy.analysis.Clip(in_fc, boundary, out_fc)
        print_messages()
        print(f"    {layer} clipped")
print("")

print("Selecting reference layers that intersect the park boundary...")
ref_layers = ["AB_Township", "NTS_50"]

for layer in ref_layers:
    in_fc = os.path.join(gdb, "Reference", layer)
    lyr_name = layer + "_lyr"
    out_fc = os.path.join(gdb, "Reference", layer + "_Clip")

    arcpy.management.MakeFeatureLayer(in_fc, lyr_name)
    arcpy.management.SelectLayerByLocation(lyr_name, "INTERSECT", boundary)
    arcpy.management.CopyFeatures(lyr_name, out_fc)
    print_messages()
    print(f"    {layer} intersecting features copied")
print("")

# Clip the DEM raster to the boundary's exact shape
print("Clipping DEM to the park boundary...")
dem_in = os.path.join(gdb, "DEM")
dem_out = os.path.join(gdb, "DEM_Clip")
arcpy.management.Clip(dem_in, "#", dem_out, boundary, "#", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
print_messages()
print("DEM clipped")
print("")


# Convert the landcover polygon to a 25m raster, then reclassify using the
# assignment's landcover cost scale (1 = most desirable, 10 = least desirable)

arcpy.CheckOutExtension("Spatial")

print("Converting AB_Landcover_Clip polygon to a 25m raster...")
landcover_clip = os.path.join(gdb, "Kananaskis", "AB_Landcover_Clip")
landcover_raster = os.path.join(gdb, "Landcover_Raster")

arcpy.conversion.PolygonToRaster(
    in_features=landcover_clip,
    value_field="LC_class",
    out_rasterdataset=landcover_raster,
    cell_assignment="MAXIMUM_AREA",
    cellsize=25
)
print_messages()
print("Landcover raster created")
print("")

print("Reclassifying Landcover raster using the assignment's landcover cost scale...")
rcls_landcover_out = os.path.join(gdb, "RCLS_Landcover")

# ABMI code -> rubric scale value
#   20 Water -> 10          50 Shrubland -> 3          210 Coniferous Forest -> 1
#   31 Snow/Ice -> 8         110 Grassland -> 2          220 Broadleaf Forest -> 1
#   32 Rock/Rubble -> 7      120 Agriculture -> 9        230 Mixed Forest -> 1
#   33 Exposed Land -> 6
#   34 Developed -> 10
remap = arcpy.sa.RemapValue([
    [20, 10], [31, 8], [32, 7], [33, 6], [34, 10],
    [50, 3], [110, 2], [120, 9], [210, 1], [220, 1], [230, 1]
])

rcls_landcover = arcpy.sa.Reclassify(landcover_raster, "VALUE", remap, "DATA")
rcls_landcover.save(rcls_landcover_out)
print_messages()
print("Landcover reclassification completed")
print("")


# Terrain ruggedness: Focal Statistics (RANGE, 3x3) on the clipped DEM.
# High values = choppy, uneven terrain; low values = smooth, easy to cross.

print("Calculating terrain ruggedness from DEM_Clip...")
dem_clip = arcpy.Raster(os.path.join(gdb, "DEM_Clip"))
terrain_ruggedness_out = os.path.join(gdb, "Terrain_Ruggedness")

terrain_ruggedness = arcpy.sa.FocalStatistics(dem_clip, "Rectangle 3 3 CELL", "RANGE", "DATA")
terrain_ruggedness.save(terrain_ruggedness_out)
print_messages()
print("Terrain ruggedness raster created")
print("")


# Distance Accumulation: distance from every cell to the nearest hydrology,
# trail, and road feature. Cell size forced to 25 since these are vector
# sources and won't otherwise inherit the project's raster cell size.

print("Running Distance Accumulation on Hydro_Clip, Trails_Clip, and Road_Clip...")

with arcpy.EnvManager(cellSize=25):
    hydro_clip = os.path.join(gdb, "Kananaskis", "Hydro_Clip")
    distaccum_hydro_out = os.path.join(gdb, "DistAccum_Hydro")
    distaccum_hydro = arcpy.sa.DistanceAccumulation(hydro_clip)
    distaccum_hydro.save(distaccum_hydro_out)
    print_messages()
    print("DistAccum_Hydro created")

    trails_clip = os.path.join(gdb, "Kananaskis", "Trails_Clip")
    distaccum_trails_out = os.path.join(gdb, "DistAccum_Trails")
    distaccum_trails = arcpy.sa.DistanceAccumulation(trails_clip)
    distaccum_trails.save(distaccum_trails_out)
    print_messages()
    print("DistAccum_Trails created")

    road_clip = os.path.join(gdb, "Kananaskis", "Roads_Clip")
    distaccum_roads_out = os.path.join(gdb, "DistAccum_Roads")
    distaccum_roads = arcpy.sa.DistanceAccumulation(road_clip)
    distaccum_roads.save(distaccum_roads_out)
    print_messages()
    print("DistAccum_Roads created")
print("")


# Rescale By Function: convert each raw cost input onto a shared 0-10 scale.
# Terrain + Hydro are increasing (low input = low cost); Trails + Roads are
# decreasing (from/to scale swapped). Each output is re-clipped to the boundary.

def rescale_and_clip(raster_name, out_name, from_scale, to_scale):
    src = arcpy.Raster(os.path.join(gdb, raster_name))
    tf = arcpy.sa.TfLinear(src.minimum, src.maximum)
    rescaled = arcpy.sa.RescaleByFunction(src, tf, from_scale, to_scale)
    rescaled_out = os.path.join(gdb, out_name)
    rescaled.save(rescaled_out)
    print_messages()

    clip_out = os.path.join(gdb, out_name + "_Clip")
    arcpy.management.Clip(rescaled_out, "#", clip_out, boundary, "#",
                           "ClippingGeometry", "NO_MAINTAIN_EXTENT")
    print_messages()
    print(f"{out_name} rescaled and clipped")
    print("")

print("Rescaling terrain ruggedness and proximity rasters to a 0-10 cost scale...")
rescale_and_clip("Terrain_Ruggedness", "RESCALE_Terrain", 0, 10)
rescale_and_clip("DistAccum_Hydro", "RESCALE_Hydro", 0, 10)
rescale_and_clip("DistAccum_Trails", "RESCALE_Trails", 10, 0)
rescale_and_clip("DistAccum_Roads", "RESCALE_Roads", 10, 0)


# Weighted Sum: combine the five 0-10 cost inputs into one cost surface.
# All weights = 1, per the assignment's default weighting.

print("Combining five cost inputs into a single weighted cost surface...")

rcls_landcover_r = arcpy.Raster(os.path.join(gdb, "RCLS_Landcover"))
rescale_terrain_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Terrain_Clip"))
rescale_hydro_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Hydro_Clip"))
rescale_trails_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Trails_Clip"))
rescale_roads_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Roads_Clip"))

ws_table = arcpy.sa.WSTable([
    [rcls_landcover_r, "VALUE", 1],
    [rescale_terrain_r, "VALUE", 1],
    [rescale_hydro_r, "VALUE", 1],
    [rescale_trails_r, "VALUE", 1],
    [rescale_roads_r, "VALUE", 1]
])

cost_surface_out = os.path.join(gdb, "Cost_Surface")
cost_surface = arcpy.sa.WeightedSum(ws_table)
cost_surface.save(cost_surface_out)
print_messages()
print("Cost_Surface created")
print("")


# Optimal Region Connections: generate least-cost corridor routes connecting
# every pair of bear habitat patches across the combined cost surface.
# out_neighbor_paths is given an explicit gdb path rather than "#", since
# leaving it unspecified caused a persistent "table already exists" error.

print("Generating optimal wildlife corridor routes between habitat patches...")

bear_habitat = os.path.join(gdb, "Wildlife", "Bear_Habitat")
optimal_routes_out = os.path.join(gdb, "Wildlife", "Optimal_Routes")

neighbor_paths_out = os.path.join(gdb, "NeighborPaths")
arcpy.sa.OptimalRegionConnections(
    bear_habitat,           # in_input_data
    optimal_routes_out,     # out_optimal_paths
    "#",                    # in_input_barrier_data
    cost_surface_out,       # in_cost_raster
    neighbor_paths_out,     # out_neighbor_paths
    "PLANAR",               # in_distance_method
    "GENERATE_CONNECTIONS"  # in_connection_type
)
print_messages()
print("Optimal_Routes created")

# Confirm where the output actually landed, since this tool has been observed
# to write to the geodatabase root instead of the given feature dataset path
root_level_path = os.path.join(gdb, "Optimal_Routes")
if arcpy.Exists(optimal_routes_out):
    print("Optimal_Routes confirmed at the intended Wildlife feature dataset path")
elif arcpy.Exists(root_level_path):
    print("NOTE: Optimal_Routes was written to the geodatabase root instead")
    optimal_routes_out = root_level_path
else:
    raise RuntimeError("Optimal_Routes was not found after OptimalRegionConnections completed.")
print("")


# Grid statistics and printed results

boundary_zone = os.path.join(gdb, "Kananaskis", "Park_Boundary")

# 1. Average elevation of Kananaskis Country
print("Calculating average elevation of Kananaskis Country...")
avg_elev_table = os.path.join(gdb, "TBL_AvgElevation")
arcpy.sa.ZonalStatisticsAsTable(
    in_zone_data=boundary_zone,
    zone_field="OBJECTID",
    in_value_raster=dem_clip,
    out_table=avg_elev_table,
    statistics_type="MEAN"
)
print_messages()
with arcpy.da.SearchCursor(avg_elev_table, ["MEAN"]) as cursor:
    for row in cursor:
        print(f"Average elevation of Kananaskis Country: {row[0]:.2f} m")
print("")

# 2. Area of each landcover type within the park
print("Calculating landcover area by class within the park...")
landcover_clip_poly = os.path.join(gdb, "Kananaskis", "AB_Landcover_Clip")
landcover_area_table = os.path.join(gdb, "TBL_LandcoverArea")
with arcpy.EnvManager(cellSize=25):
    arcpy.sa.TabulateArea(
        in_zone_data=boundary_zone,
        zone_field="OBJECTID",
        in_class_data=landcover_clip_poly,
        class_field="LC_class",
        out_table=landcover_area_table
    )
print_messages()
print("TBL_LandcoverArea created")
print("")

# 3. Total length of the optimal routes, using a SHAPE@LENGTH geometry token
print("Calculating total length of the optimal routes...")
total_length = 0
with arcpy.da.SearchCursor(optimal_routes_out, ["SHAPE@LENGTH"]) as cursor:
    for row in cursor:
        total_length += row[0]
print(f"Total length of optimal routes: {total_length:.2f} m")
print("")

# 4. NTS map sheets and TWP-RGE-MER covering the park
print("Identifying NTS map sheets and townships covering the park...")
nts_clip = os.path.join(gdb, "Reference", "NTS_50_Clip")
township_clip = os.path.join(gdb, "Reference", "AB_Township_Clip")

nts_sheets = set()
with arcpy.da.SearchCursor(nts_clip, ["NAME"]) as cursor:
    for row in cursor:
        nts_sheets.add(row[0])
print("1:50,000 NTS map sheets covering Kananaskis Country:")
for sheet in sorted(nts_sheets):
    print(f"    {sheet}")

townships = set()
with arcpy.da.SearchCursor(township_clip, ["DESCRIPTOR"]) as cursor:
    for row in cursor:
        townships.add(row[0])
print("Townships (TWP-RGE-MER) covering Kananaskis Country:")
for twp in sorted(townships):
    print(f"    {twp}")
print("")


# Final cleanup: remove every intermediate/working dataset that isn't part of
# the assignment's Final Data Requirements list. Transportation is excluded
# from KEEP since it was never actually part of that required list, even
# though it was processed earlier because it happened to be in the raw folder.

optimal_routes_final = optimal_routes_out

print("Removing intermediate datasets not required in the final deliverable...")
KEEP = {
    os.path.join(gdb, "Kananaskis", "Park_Boundary"),
    os.path.join(gdb, "Kananaskis", "Roads_Clip"),
    os.path.join(gdb, "Kananaskis", "Trails_Clip"),
    os.path.join(gdb, "Kananaskis", "Hydro_Clip"),
    os.path.join(gdb, "Kananaskis", "AB_Landcover_Clip"),
    os.path.join(gdb, "Wildlife", "Bear_Habitat"),
    os.path.join(gdb, "Wildlife", "ESA_Clip"),
    optimal_routes_out,
    os.path.join(gdb, "Reference", "AB_Township_Clip"),
    os.path.join(gdb, "Reference", "NTS_50_Clip"),
    os.path.join(gdb, "DEM_Clip"),
    os.path.join(gdb, "Terrain_Ruggedness"),
    os.path.join(gdb, "TBL_AvgElevation"),
    os.path.join(gdb, "TBL_LandcoverArea"),
}

# Paths normalized before comparing, since arcpy.da.Walk's returned paths
# don't always match hardcoded paths on exact string equality
KEEP_NORMALIZED = {os.path.normcase(os.path.normpath(p)) for p in KEEP}

all_items = []
for dirpath, dirnames, filenames in arcpy.da.Walk(gdb, datatype=["FeatureClass", "RasterDataset", "Table"]):
    for fname in filenames:
        all_items.append(os.path.join(dirpath, fname))

for item in all_items:
    if os.path.normcase(os.path.normpath(item)) not in KEEP_NORMALIZED:
        arcpy.management.Delete(item)
        print_messages()
        print(f"    Deleted intermediate dataset: {os.path.basename(item)}")
print("")

# List and describe every final dataset that remains: geometry and spatial
# reference for feature classes, cell size and spatial reference for rasters,
# and name only for tables
print("Final feature classes, rasters, and tables in KananaskisWildlife.gdb:")
for item in sorted(KEEP):
    if not arcpy.Exists(item):
        continue
    desc = arcpy.Describe(item)
    name = os.path.basename(item)
    if desc.dataType == "FeatureClass":
        print(f"    {name} (feature class)")
        print(f"        Geometry: {desc.shapeType}")
        print(f"        Spatial Reference: {desc.spatialReference.name}")
    elif desc.dataType == "RasterDataset":
        print(f"    {name} (raster)")
        print(f"        Cell Size: {desc.meanCellWidth}")
        print(f"        Spatial Reference: {desc.spatialReference.name}")
    elif desc.dataType == "Table":
        print(f"    {name} (table)")
    else:
        print(f"    {name} ({desc.dataType})")
print("")

# Release Python-side Raster object references to datasets just deleted above,
# and clear the workspace cache, since stale in-memory handles to deleted data
# can cause confusing errors in the map export step that follows
del (dem_clip, rcls_landcover_r, rescale_terrain_r, rescale_hydro_r,
     rescale_trails_r, rescale_roads_r, terrain_ruggedness, landcover_raster,
     rcls_landcover, distaccum_hydro, distaccum_trails, distaccum_roads, cost_surface)
arcpy.management.ClearWorkspaceCache(gdb)
print_messages()
print("Workspace cache cleared")
print("")


# Populate the provided map layout and export to PDF.
# The .aprx is opened by its explicit path rather than "CURRENT", since this
# script runs through PyScripter's remote interpreter, not ArcGIS Pro's own
# Python window.

print("Populating the map layout and exporting to PDF...")
aprx_path = os.path.join(root, "GEOS456_FinalProject.aprx")
aprx = arcpy.mp.ArcGISProject(aprx_path)
active_map = aprx.listMaps()[0]
layout = aprx.listLayouts()[0]

# Park_Boundary is added first so it draws underneath Bear_Habitat and
# Optimal_Routes (Pro adds each new layer to the top of the draw order)
for lyr_path in [os.path.join(gdb, "Kananaskis", "Park_Boundary"), os.path.join(gdb, "Wildlife", "Bear_Habitat"), optimal_routes_final]:
    if not arcpy.Exists(lyr_path):
        print(f"    WARNING: {lyr_path} does not exist, skipping")
        continue
    catalog_path = arcpy.Describe(lyr_path).catalogPath
    print(f"    Adding {catalog_path}")
    active_map.addDataFromPath(catalog_path)
print_messages()

# Zoom the map frame to the park boundary, since addDataFromPath adds a layer
# to the map but does not zoom to show it
print("Setting map frame extent to show the park boundary and its contents...")
map_frame = layout.listElements("MAPFRAME_ELEMENT")[0]
boundary_layers = active_map.listLayers("Park_Boundary")
if boundary_layers:
    map_frame.camera.setExtent(map_frame.getLayerExtent(boundary_layers[0], True))
    print("Map frame extent set to Park_Boundary")
else:
    print("    WARNING: Park_Boundary layer not found, map frame extent left unchanged")
print("")

# Replace the layout template's placeholder title text
print("Updating map title...")
title_updated = False
for elem in layout.listElements("TEXT_ELEMENT"):
    if "TITLE" in elem.name.upper():
        elem.text = "Connecting Wildlife Habitat"
        print(f"    Updated title element: {elem.name}")
        title_updated = True
if not title_updated:
    print("    WARNING: no title text element found, template title left unchanged")
print("")

pdf_out = os.path.join(root, "GEOS456_FP_Abboud_John.pdf")
layout.exportToPDF(pdf_out)
print_messages()
print(f"Map exported to {pdf_out}")
print("")

# Release the aprx and every related map/layout object, so ArcGIS Pro
# doesn't leave the project locked/read-only. del aprx alone was not enough,
# since active_map, layout, map_frame, and boundary_layers still referenced it.
del aprx, active_map, layout, map_frame, boundary_layers
try:
    del elem
except NameError:
    pass
gc.collect()
print("aprx and related map/layout objects released")
print("")

# Assignment complete :)

print("Script complete - KananaskisWildlife.gdb and the map PDF have been created")


#-------------------------------------------------------------------------------
# Name:        Final Project: Connecting Wildlife Habitat
# Purpose:     Build a geoprocessing model to identify optimal wildlife corridor
#              routes connecting bear habitat patches in Kananaskis Country,
#              using a weighted cost surface based on landcover, terrain
#              ruggedness, and proximity to roads, trails, and hydrology.
#
# Author:      John Abboud
# Created:     03/08/2026
#-------------------------------------------------------------------------------

# Import the arcpy module
import arcpy
import os
import gc

# Set environment workspace and overwrite properties
arcpy.env.workspace = r"C:\GEOS456\FinalProject"
arcpy.env.overwriteOutput = True

# Root project folder - everything below references this location
root = r"C:\GEOS456\FinalProject"
gdb = os.path.join(root, "KananaskisWildlife.gdb")

# Spatial reference object used throughout the script
# NAD_1983_UTM_Zone_11N - the project's target projection
UTM11N = arcpy.SpatialReference(26911)

# Helper function used after every geoprocessing tool
# prints the first and last message returned by the most recently run tool
def print_messages():
    msgCount = arcpy.GetMessageCount()
    if msgCount > 0:
        print(arcpy.GetMessage(0))
        print(arcpy.GetMessage(msgCount - 1))


# Check if the assignment geodatabase already exists.
# If it exists, delete it prior to making a new one.

print("Checking for an existing KananaskisWildlife.gdb")

arcpy.env.workspace = root

if arcpy.Exists(gdb):
    arcpy.management.Delete(gdb)
    print_messages()
    print("Existing KananaskisWildlife.gdb was found and deleted")
else:
    print("No existing KananaskisWildlife.gdb was found")
print("")


# Create the file geodatabase and feature datasets to store the data

print("Creating KananaskisWildlife.gdb and feature datasets")

arcpy.management.CreateFileGDB(root, "KananaskisWildlife.gdb")
print_messages()
print("KananaskisWildlife.gdb created")
print("")

# Kananaskis = base/context layers, Wildlife = habitat + analysis outputs,
# Reference = administrative/index grids (townships, NTS map sheets)
fds_list = ["Kananaskis", "Wildlife", "Reference"]
for fds in fds_list:
    arcpy.management.CreateFeatureDataset(gdb, fds, UTM11N)
    print_messages()
print("Feature datasets created: Kananaskis, Wildlife, Reference")
print("")


# List of every raw data folder that contains shapefiles for this assignment,
# and dictionary mapping each raw shapefile name to its feature dataset and
# clean output name in the geodatabase

raw_vector_folders = [
    os.path.join(root, "ATS"),
    os.path.join(root, "Kananaskis"),
    os.path.join(root, "Landcover"),
    os.path.join(root, "NTS", "NTS-50"),
    os.path.join(root, "Wildlife")
]

raw_raster_folders = [
    os.path.join(root, "dem")
]

fds_assignment = {
    "KCountry_Bound": ("Kananaskis", "Park_Boundary"),
    "Road":           ("Kananaskis", "Roads"),
    "Trails":         ("Kananaskis", "Trails"),
    "Hydro":          ("Kananaskis", "Hydro"),
    "Transportation": ("Kananaskis", "Transportation"),
    "AB_Landcover":   ("Kananaskis", "AB_Landcover"),
    "Bear_Habitat":   ("Wildlife", "Bear_Habitat"),
    "ESA":            ("Wildlife", "ESA"),
    "AB_Township":    ("Reference", "AB_Township"),
    "NTS50":          ("Reference", "NTS_50")
}


# Import and project all vector layers into the geodatabase.
# Each shapefile's spatial reference is checked at runtime: layers already in
# UTM 11N are copied as-is, everything else is projected.

print("Copying/projecting vector layers into KananaskisWildlife.gdb...")
for folder in raw_vector_folders:
    arcpy.env.workspace = folder
    fcList = arcpy.ListFeatureClasses() or []
    print("Folder:", folder)

    for fc in fcList:
        fcDesc = arcpy.Describe(fc)
        fc_name = os.path.splitext(fc)[0]
        print("    Name:", fc)
        print("        Shape Type:", fcDesc.shapeType)
        print("        Spatial Reference:", fcDesc.spatialReference.name)

        if fc_name not in fds_assignment:
            print(f"        Skipping {fc_name}, no feature dataset assigned")
            continue

        target_fds, out_name = fds_assignment[fc_name]
        out_path = os.path.join(gdb, target_fds, out_name)

        # factoryCode 26911 = NAD83 UTM Zone 11N
        if fcDesc.spatialReference.factoryCode == 26911:
            arcpy.management.CopyFeatures(fc, out_path)
        else:
            arcpy.management.Project(fc, out_path, UTM11N)
        print_messages()
    print("")


# Import and project the DEM into the geodatabase, resampled to 25m

print("Copying/projecting DEM into KananaskisWildlife.gdb...")
for folder in raw_raster_folders:
    arcpy.env.workspace = folder
    rasList = arcpy.ListRasters() or []
    print("Folder:", folder)

    for ras in rasList:
        rasDesc = arcpy.Describe(ras)
        out_path = os.path.join(gdb, "DEM")
        print("    Name:", ras)
        print("        Spatial Reference:", rasDesc.spatialReference.name)
        print("        Cell Size:", rasDesc.meanCellWidth)

        if rasDesc.spatialReference.factoryCode == 26911:
            arcpy.management.CopyRaster(ras, out_path)
        else:
            # BILINEAR resampling for continuous elevation data
            arcpy.management.ProjectRaster(ras, out_path, UTM11N, "BILINEAR", 25)
        print_messages()
    print("")

# Reset the workspace to the geodatabase now that the folder-by-folder import
# loops above are done, so any tool with an unspecified output defaults safely
# into the gdb instead of the last raw data folder
arcpy.env.workspace = gdb


# Clip all layers to the Kananaskis Park Boundary.
# Physical/context layers get a hard Clip. Reference grids (townships, NTS
# sheets) use Select by Location instead, so whole units are kept rather than
# sliced at the boundary edge.

boundary = os.path.join(gdb, "Kananaskis", "Park_Boundary")

print("Clipping vector layers to the park boundary...")

clip_targets = {
    "Kananaskis": ["Roads", "Trails", "Hydro", "Transportation", "AB_Landcover"],
    "Wildlife": ["Bear_Habitat", "ESA"]
}

for fds, layers in clip_targets.items():
    for layer in layers:
        in_fc = os.path.join(gdb, fds, layer)
        out_fc = os.path.join(gdb, fds, layer + "_Clip")
        arcpy.analysis.Clip(in_fc, boundary, out_fc)
        print_messages()
        print(f"    {layer} clipped")
print("")

print("Selecting reference layers that intersect the park boundary...")
ref_layers = ["AB_Township", "NTS_50"]

for layer in ref_layers:
    in_fc = os.path.join(gdb, "Reference", layer)
    lyr_name = layer + "_lyr"
    out_fc = os.path.join(gdb, "Reference", layer + "_Clip")

    arcpy.management.MakeFeatureLayer(in_fc, lyr_name)
    arcpy.management.SelectLayerByLocation(lyr_name, "INTERSECT", boundary)
    arcpy.management.CopyFeatures(lyr_name, out_fc)
    print_messages()
    print(f"    {layer} intersecting features copied")
print("")

# Clip the DEM raster to the boundary's exact shape
print("Clipping DEM to the park boundary...")
dem_in = os.path.join(gdb, "DEM")
dem_out = os.path.join(gdb, "DEM_Clip")
arcpy.management.Clip(dem_in, "#", dem_out, boundary, "#", "ClippingGeometry", "NO_MAINTAIN_EXTENT")
print_messages()
print("DEM clipped")
print("")


# Convert the landcover polygon to a 25m raster, then reclassify using the
# assignment's landcover cost scale (1 = most desirable, 10 = least desirable)

arcpy.CheckOutExtension("Spatial")

print("Converting AB_Landcover_Clip polygon to a 25m raster...")
landcover_clip = os.path.join(gdb, "Kananaskis", "AB_Landcover_Clip")
landcover_raster = os.path.join(gdb, "Landcover_Raster")

arcpy.conversion.PolygonToRaster(
    in_features=landcover_clip,
    value_field="LC_class",
    out_rasterdataset=landcover_raster,
    cell_assignment="MAXIMUM_AREA",
    cellsize=25
)
print_messages()
print("Landcover raster created")
print("")

print("Reclassifying Landcover raster using the assignment's landcover cost scale...")
rcls_landcover_out = os.path.join(gdb, "RCLS_Landcover")

# ABMI code -> rubric scale value
#   20 Water -> 10          50 Shrubland -> 3          210 Coniferous Forest -> 1
#   31 Snow/Ice -> 8         110 Grassland -> 2          220 Broadleaf Forest -> 1
#   32 Rock/Rubble -> 7      120 Agriculture -> 9        230 Mixed Forest -> 1
#   33 Exposed Land -> 6
#   34 Developed -> 10
remap = arcpy.sa.RemapValue([
    [20, 10], [31, 8], [32, 7], [33, 6], [34, 10],
    [50, 3], [110, 2], [120, 9], [210, 1], [220, 1], [230, 1]
])

rcls_landcover = arcpy.sa.Reclassify(landcover_raster, "VALUE", remap, "DATA")
rcls_landcover.save(rcls_landcover_out)
print_messages()
print("Landcover reclassification completed")
print("")


# Terrain ruggedness: Focal Statistics (RANGE, 3x3) on the clipped DEM.
# High values = choppy, uneven terrain; low values = smooth, easy to cross.

print("Calculating terrain ruggedness from DEM_Clip...")
dem_clip = arcpy.Raster(os.path.join(gdb, "DEM_Clip"))
terrain_ruggedness_out = os.path.join(gdb, "Terrain_Ruggedness")

terrain_ruggedness = arcpy.sa.FocalStatistics(dem_clip, "Rectangle 3 3 CELL", "RANGE", "DATA")
terrain_ruggedness.save(terrain_ruggedness_out)
print_messages()
print("Terrain ruggedness raster created")
print("")


# Distance Accumulation: distance from every cell to the nearest hydrology,
# trail, and road feature. Cell size forced to 25 since these are vector
# sources and won't otherwise inherit the project's raster cell size.

print("Running Distance Accumulation on Hydro_Clip, Trails_Clip, and Road_Clip...")

with arcpy.EnvManager(cellSize=25):
    hydro_clip = os.path.join(gdb, "Kananaskis", "Hydro_Clip")
    distaccum_hydro_out = os.path.join(gdb, "DistAccum_Hydro")
    distaccum_hydro = arcpy.sa.DistanceAccumulation(hydro_clip)
    distaccum_hydro.save(distaccum_hydro_out)
    print_messages()
    print("DistAccum_Hydro created")

    trails_clip = os.path.join(gdb, "Kananaskis", "Trails_Clip")
    distaccum_trails_out = os.path.join(gdb, "DistAccum_Trails")
    distaccum_trails = arcpy.sa.DistanceAccumulation(trails_clip)
    distaccum_trails.save(distaccum_trails_out)
    print_messages()
    print("DistAccum_Trails created")

    road_clip = os.path.join(gdb, "Kananaskis", "Roads_Clip")
    distaccum_roads_out = os.path.join(gdb, "DistAccum_Roads")
    distaccum_roads = arcpy.sa.DistanceAccumulation(road_clip)
    distaccum_roads.save(distaccum_roads_out)
    print_messages()
    print("DistAccum_Roads created")
print("")


# Rescale By Function: convert each raw cost input onto a shared 0-10 scale.
# Terrain + Hydro are increasing (low input = low cost); Trails + Roads are
# decreasing (from/to scale swapped). Each output is re-clipped to the boundary.

def rescale_and_clip(raster_name, out_name, from_scale, to_scale):
    src = arcpy.Raster(os.path.join(gdb, raster_name))
    tf = arcpy.sa.TfLinear(src.minimum, src.maximum)
    rescaled = arcpy.sa.RescaleByFunction(src, tf, from_scale, to_scale)
    rescaled_out = os.path.join(gdb, out_name)
    rescaled.save(rescaled_out)
    print_messages()

    clip_out = os.path.join(gdb, out_name + "_Clip")
    arcpy.management.Clip(rescaled_out, "#", clip_out, boundary, "#",
                           "ClippingGeometry", "NO_MAINTAIN_EXTENT")
    print_messages()
    print(f"{out_name} rescaled and clipped")
    print("")

print("Rescaling terrain ruggedness and proximity rasters to a 0-10 cost scale...")
rescale_and_clip("Terrain_Ruggedness", "RESCALE_Terrain", 0, 10)
rescale_and_clip("DistAccum_Hydro", "RESCALE_Hydro", 0, 10)
rescale_and_clip("DistAccum_Trails", "RESCALE_Trails", 10, 0)
rescale_and_clip("DistAccum_Roads", "RESCALE_Roads", 10, 0)


# Weighted Sum: combine the five 0-10 cost inputs into one cost surface.
# All weights = 1, per the assignment's default weighting.

print("Combining five cost inputs into a single weighted cost surface...")

rcls_landcover_r = arcpy.Raster(os.path.join(gdb, "RCLS_Landcover"))
rescale_terrain_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Terrain_Clip"))
rescale_hydro_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Hydro_Clip"))
rescale_trails_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Trails_Clip"))
rescale_roads_r = arcpy.Raster(os.path.join(gdb, "RESCALE_Roads_Clip"))

ws_table = arcpy.sa.WSTable([
    [rcls_landcover_r, "VALUE", 1],
    [rescale_terrain_r, "VALUE", 1],
    [rescale_hydro_r, "VALUE", 1],
    [rescale_trails_r, "VALUE", 1],
    [rescale_roads_r, "VALUE", 1]
])

cost_surface_out = os.path.join(gdb, "Cost_Surface")
cost_surface = arcpy.sa.WeightedSum(ws_table)
cost_surface.save(cost_surface_out)
print_messages()
print("Cost_Surface created")
print("")


# Optimal Region Connections: generate least-cost corridor routes connecting
# every pair of bear habitat patches across the combined cost surface.
# out_neighbor_paths is given an explicit gdb path rather than "#", since
# leaving it unspecified caused a persistent "table already exists" error.

print("Generating optimal wildlife corridor routes between habitat patches...")

bear_habitat = os.path.join(gdb, "Wildlife", "Bear_Habitat")
optimal_routes_out = os.path.join(gdb, "Wildlife", "Optimal_Routes")

neighbor_paths_out = os.path.join(gdb, "NeighborPaths")
arcpy.sa.OptimalRegionConnections(
    bear_habitat,           # in_input_data
    optimal_routes_out,     # out_optimal_paths
    "#",                    # in_input_barrier_data
    cost_surface_out,       # in_cost_raster
    neighbor_paths_out,     # out_neighbor_paths
    "PLANAR",               # in_distance_method
    "GENERATE_CONNECTIONS"  # in_connection_type
)
print_messages()
print("Optimal_Routes created")

# Confirm where the output actually landed, since this tool has been observed
# to write to the geodatabase root instead of the given feature dataset path
root_level_path = os.path.join(gdb, "Optimal_Routes")
if arcpy.Exists(optimal_routes_out):
    print("Optimal_Routes confirmed at the intended Wildlife feature dataset path")
elif arcpy.Exists(root_level_path):
    print("NOTE: Optimal_Routes was written to the geodatabase root instead")
    optimal_routes_out = root_level_path
else:
    raise RuntimeError("Optimal_Routes was not found after OptimalRegionConnections completed.")
print("")


# Grid statistics and printed results

boundary_zone = os.path.join(gdb, "Kananaskis", "Park_Boundary")

# 1. Average elevation of Kananaskis Country
print("Calculating average elevation of Kananaskis Country...")
avg_elev_table = os.path.join(gdb, "TBL_AvgElevation")
arcpy.sa.ZonalStatisticsAsTable(
    in_zone_data=boundary_zone,
    zone_field="OBJECTID",
    in_value_raster=dem_clip,
    out_table=avg_elev_table,
    statistics_type="MEAN"
)
print_messages()
with arcpy.da.SearchCursor(avg_elev_table, ["MEAN"]) as cursor:
    for row in cursor:
        print(f"Average elevation of Kananaskis Country: {row[0]:.2f} m")
print("")

# 2. Area of each landcover type within the park
print("Calculating landcover area by class within the park...")
landcover_clip_poly = os.path.join(gdb, "Kananaskis", "AB_Landcover_Clip")
landcover_area_table = os.path.join(gdb, "TBL_LandcoverArea")
with arcpy.EnvManager(cellSize=25):
    arcpy.sa.TabulateArea(
        in_zone_data=boundary_zone,
        zone_field="OBJECTID",
        in_class_data=landcover_clip_poly,
        class_field="LC_class",
        out_table=landcover_area_table
    )
print_messages()
print("TBL_LandcoverArea created")
print("")

# 3. Total length of the optimal routes, using a SHAPE@LENGTH geometry token
print("Calculating total length of the optimal routes...")
total_length = 0
with arcpy.da.SearchCursor(optimal_routes_out, ["SHAPE@LENGTH"]) as cursor:
    for row in cursor:
        total_length += row[0]
print(f"Total length of optimal routes: {total_length:.2f} m")
print("")

# 4. NTS map sheets and TWP-RGE-MER covering the park
print("Identifying NTS map sheets and townships covering the park...")
nts_clip = os.path.join(gdb, "Reference", "NTS_50_Clip")
township_clip = os.path.join(gdb, "Reference", "AB_Township_Clip")

nts_sheets = set()
with arcpy.da.SearchCursor(nts_clip, ["NAME"]) as cursor:
    for row in cursor:
        nts_sheets.add(row[0])
print("1:50,000 NTS map sheets covering Kananaskis Country:")
for sheet in sorted(nts_sheets):
    print(f"    {sheet}")

townships = set()
with arcpy.da.SearchCursor(township_clip, ["DESCRIPTOR"]) as cursor:
    for row in cursor:
        townships.add(row[0])
print("Townships (TWP-RGE-MER) covering Kananaskis Country:")
for twp in sorted(townships):
    print(f"    {twp}")
print("")


# Final cleanup: remove every intermediate/working dataset that isn't part of
# the assignment's Final Data Requirements list. Transportation is excluded
# from KEEP since it was never actually part of that required list, even
# though it was processed earlier because it happened to be in the raw folder.

optimal_routes_final = optimal_routes_out

print("Removing intermediate datasets not required in the final deliverable...")
KEEP = {
    os.path.join(gdb, "Kananaskis", "Park_Boundary"),
    os.path.join(gdb, "Kananaskis", "Roads_Clip"),
    os.path.join(gdb, "Kananaskis", "Trails_Clip"),
    os.path.join(gdb, "Kananaskis", "Hydro_Clip"),
    os.path.join(gdb, "Kananaskis", "AB_Landcover_Clip"),
    os.path.join(gdb, "Wildlife", "Bear_Habitat"),
    os.path.join(gdb, "Wildlife", "ESA_Clip"),
    optimal_routes_out,
    os.path.join(gdb, "Reference", "AB_Township_Clip"),
    os.path.join(gdb, "Reference", "NTS_50_Clip"),
    os.path.join(gdb, "DEM_Clip"),
    os.path.join(gdb, "Terrain_Ruggedness"),
    os.path.join(gdb, "TBL_AvgElevation"),
    os.path.join(gdb, "TBL_LandcoverArea"),
}

# Paths normalized before comparing, since arcpy.da.Walk's returned paths
# don't always match hardcoded paths on exact string equality
KEEP_NORMALIZED = {os.path.normcase(os.path.normpath(p)) for p in KEEP}

all_items = []
for dirpath, dirnames, filenames in arcpy.da.Walk(gdb, datatype=["FeatureClass", "RasterDataset", "Table"]):
    for fname in filenames:
        all_items.append(os.path.join(dirpath, fname))

for item in all_items:
    if os.path.normcase(os.path.normpath(item)) not in KEEP_NORMALIZED:
        arcpy.management.Delete(item)
        print_messages()
        print(f"    Deleted intermediate dataset: {os.path.basename(item)}")
print("")

# List and describe every final dataset that remains: geometry and spatial
# reference for feature classes, cell size and spatial reference for rasters,
# and name only for tables
print("Final feature classes, rasters, and tables in KananaskisWildlife.gdb:")
for item in sorted(KEEP):
    if not arcpy.Exists(item):
        continue
    desc = arcpy.Describe(item)
    name = os.path.basename(item)
    if desc.dataType == "FeatureClass":
        print(f"    {name} (feature class)")
        print(f"        Geometry: {desc.shapeType}")
        print(f"        Spatial Reference: {desc.spatialReference.name}")
    elif desc.dataType == "RasterDataset":
        print(f"    {name} (raster)")
        print(f"        Cell Size: {desc.meanCellWidth}")
        print(f"        Spatial Reference: {desc.spatialReference.name}")
    elif desc.dataType == "Table":
        print(f"    {name} (table)")
    else:
        print(f"    {name} ({desc.dataType})")
print("")

# Release Python-side Raster object references to datasets just deleted above,
# and clear the workspace cache, since stale in-memory handles to deleted data
# can cause confusing errors in the map export step that follows
del (dem_clip, rcls_landcover_r, rescale_terrain_r, rescale_hydro_r,
     rescale_trails_r, rescale_roads_r, terrain_ruggedness, landcover_raster,
     rcls_landcover, distaccum_hydro, distaccum_trails, distaccum_roads, cost_surface)
arcpy.management.ClearWorkspaceCache(gdb)
print_messages()
print("Workspace cache cleared")
print("")


# Populate the provided map layout and export to PDF.
# The .aprx is opened by its explicit path rather than "CURRENT", since this
# script runs through PyScripter's remote interpreter, not ArcGIS Pro's own
# Python window.

print("Populating the map layout and exporting to PDF...")
aprx_path = os.path.join(root, "GEOS456_FinalProject.aprx")
aprx = arcpy.mp.ArcGISProject(aprx_path)
active_map = aprx.listMaps()[0]
layout = aprx.listLayouts()[0]

# Park_Boundary is added first so it draws underneath Bear_Habitat and
# Optimal_Routes (Pro adds each new layer to the top of the draw order)
for lyr_path in [os.path.join(gdb, "Kananaskis", "Park_Boundary"), os.path.join(gdb, "Wildlife", "Bear_Habitat"), optimal_routes_final]:
    if not arcpy.Exists(lyr_path):
        print(f"    WARNING: {lyr_path} does not exist, skipping")
        continue
    catalog_path = arcpy.Describe(lyr_path).catalogPath
    print(f"    Adding {catalog_path}")
    active_map.addDataFromPath(catalog_path)
print_messages()

# Zoom the map frame to the park boundary, since addDataFromPath adds a layer
# to the map but does not zoom to show it
print("Setting map frame extent to show the park boundary and its contents...")
map_frame = layout.listElements("MAPFRAME_ELEMENT")[0]
boundary_layers = active_map.listLayers("Park_Boundary")
if boundary_layers:
    map_frame.camera.setExtent(map_frame.getLayerExtent(boundary_layers[0], True))
    print("Map frame extent set to Park_Boundary")
else:
    print("    WARNING: Park_Boundary layer not found, map frame extent left unchanged")
print("")

# Replace the layout template's placeholder title text
print("Updating map title...")
title_updated = False
for elem in layout.listElements("TEXT_ELEMENT"):
    if "TITLE" in elem.name.upper():
        elem.text = "Connecting Wildlife Habitat"
        print(f"    Updated title element: {elem.name}")
        title_updated = True
if not title_updated:
    print("    WARNING: no title text element found, template title left unchanged")
print("")

pdf_out = os.path.join(root, "GEOS456_FP_Abboud_John.pdf")
layout.exportToPDF(pdf_out)
print_messages()
print(f"Map exported to {pdf_out}")
print("")

# Release the aprx and every related map/layout object, so ArcGIS Pro
# doesn't leave the project locked/read-only. del aprx alone was not enough,
# since active_map, layout, map_frame, and boundary_layers still referenced it.
del aprx, active_map, layout, map_frame, boundary_layers
try:
    del elem
except NameError:
    pass
gc.collect()
print("aprx and related map/layout objects released")
print("")

# Assignment complete :)

print("Script complete - KananaskisWildlife.gdb and the map PDF have been created")


'''
Sources Consulted:

An Overview of ArcPy functions
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/alphabetical-list-of-arcpy-functions.htm
ArcGISProject class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/arcgisproject-class.htm
Check Out Extension / Check In Extension
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/checkoutextension.htm
Clear Workspace Cache (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/clear-workspace-cache.htm
Clip (Analysis)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/clip.htm
Clip (Data Management, raster)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/clip.htm
Copy Features (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/copy-features.htm
Copy Raster (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/copy-raster.htm
Create Feature Dataset (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-feature-dataset.htm
Create File GDB (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-file-gdb.htm
Delete (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/delete.htm
Describe
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/describe.htm
Distance Accumulation (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/distance-accumulation.htm
EnvManager class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/envmanager.htm
Exists
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/exists.htm
Focal Statistics (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/focal-statistics.htm
GetMessage / GetMessageCount
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/getmessage.htm
Layout class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/layout-class.htm
List Feature Classes
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listfeatureclasses.htm
List Rasters
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listrasters.htm
Make Feature Layer (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/make-feature-layer.htm
Map class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/mapping/map-class.htm
Optimal Region Connections (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/optimal-region-connections.htm
Polygon to Raster (Conversion)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/polygon-to-raster.htm
Project (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/project.htm
Project Raster (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/project-raster.htm
Raster class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/raster-object.htm
Reclassify (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/reclassify.htm
RemapValue class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/spatial-analyst/remapvalue-class.htm
Rescale by Function (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/rescale-by-function.htm
SearchCursor
    https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm
Select Layer By Location (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/select-layer-by-location.htm
SpatialReference
    https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/spatialreference.htm
Tabulate Area (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/tabulate-area.htm
TfLinear class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/spatial-analyst/tflinear-class.htm
Walk
    https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/walk.htm
Weighted Sum (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/weighted-sum.htm
WSTable class
    https://pro.arcgis.com/en/pro-app/latest/arcpy/spatial-analyst/wstable-class.htm
Zonal Statistics as Table (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/zonal-statistics-as-table.htm
'''