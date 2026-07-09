#-------------------------------------------------------------------------------
# Name:        Assignment 2: Geoprocessing for Map Overlays
# Purpose:     Automate the conversion and management of NTS base features,
#              the ATS/DLS land fabric, and a GPS point into a single file
#              geodatabase for use in mapping initiatives.
#
# Author:      John Abboud
# Created:     19/06/2026
# Copyright:   (c) 456460 2026
#-------------------------------------------------------------------------------

# Import the arcpy module
import arcpy
import os

# Set environment workspace and overwrite properties
arcpy.env.workspace = r"C:\GEOS456\Assign02"
arcpy.env.overwriteOutput = True

# Root project folder - everything below references this location
root = r"C:\GEOS456\Assign02"
gdb = os.path.join(root, "Assignment02.gdb")

# Spatial reference objects used throughout the script
# NAD_1983_10TM_AEP_Resource - the raw Base data's true projection
AEP_10TM = arcpy.SpatialReference(3403)
# NAD_1983_UTM_Zone_12N - the project's target projection
UTM12N = arcpy.SpatialReference(26912)


# Helper function used after every geoprocessing tool
# prints the first and last message returned by the most recently run tool
def print_messages():
    msgCount = arcpy.GetMessageCount()
    if msgCount > 0:
        print(arcpy.GetMessage(0))
        print(arcpy.GetMessage(msgCount - 1))



# Create a list of all the assignment datasets prior to importing,
# and describe the data type, geometry and spatial reference of
# each shapefile in the assignment data folder


print("Listing and describing all raw assignment datasets")
print("")

# List of every raw data folder that contains shapefiles for this assignment
raw_folders = [
    root,
    os.path.join(root, "Base", "82I11NW", "82I11NW"),
    os.path.join(root, "Base", "82I14SW"),
    os.path.join(root, "DLS")
]

for folder in raw_folders:
    arcpy.env.workspace = folder
    fcList = arcpy.ListFeatureClasses()
    print("Folder:", folder)
    for fc in fcList:
        fcDesc = arcpy.Describe(fc)
        print("    Name:", fc)
        print("        Shape Type:", fcDesc.shapeType)
        print("        Spatial Reference:", fcDesc.spatialReference.name)
    print("")


# Check if the assignment geodatabase already exists.
# If it exists, delete it prior to making a new one.

print("Checking for an existing Assignment02.gdb")

arcpy.env.workspace = root

if arcpy.Exists(gdb):
    arcpy.management.Delete(gdb)
    print("Existing Assignment02.gdb was found and deleted")
else:
    print("No existing Assignment02.gdb was found")
print("")



# Create the file geodatabase and feature datasets to store the data

print("Creating Assignment02.gdb and feature datasets")

# Create the file geodatabase in the Assign02 folder
arcpy.management.CreateFileGDB(root, "Assignment02.gdb")
print_messages()
print("Assignment02.gdb created")
print("")

# Create a feature dataset to hold the DLS / ATS land fabric data
arcpy.management.CreateFeatureDataset(gdb, "DLS", UTM12N)
print_messages()
print("DLS feature dataset created")
print("")

# Create a feature dataset to hold the 1:20,000 Base Features data
arcpy.management.CreateFeatureDataset(gdb, "Base_Features", UTM12N)
print_messages()
print("Base_Features feature dataset created")
print("")

# Convert all assignment data and store it in the geodatabase
print("Importing, projecting, merging and clipping all assignment data")
print("")


# Import and project the GPS point (already in the correct projection,
# so Project is used simply to copy it into the gdb with a clean name)

print("Importing GSP_Pointe.shp (GPS point) to the geodatabase...")
in_gps = os.path.join(root, "GSP_Pointe.shp")
out_gps = os.path.join(gdb, "GPS_Point")
arcpy.management.Project(in_gps, out_gps, UTM12N)
print_messages()
print("GPS point imported")
print("")

# Project the Township grid and identify the Study Area
# (the township that contains the GPS point)

print("Projecting Township grid (82I_TWP.shp) into the geodatabase...")
in_twp = os.path.join(root, "DLS", "82I_TWP.shp")
out_twp = os.path.join(gdb, "raw_TWP")
arcpy.management.Project(in_twp, out_twp, UTM12N)
print_messages()
print("Township grid projected")
print("")

print("Selecting the township that contains the GPS point...")
twp_layer = arcpy.management.MakeFeatureLayer(out_twp, "twp_layer")
gps_layer = arcpy.management.MakeFeatureLayer(out_gps, "gps_layer")

# Select townships that CONTAIN the GPS point
arcpy.management.SelectLayerByLocation(twp_layer, "CONTAINS", gps_layer, "", "NEW_SELECTION")
print_messages()
print("Township containing GPS point selected")
print("")

print("Exporting the selected township as the Study_Area...")
study_area = os.path.join(gdb, "DLS", "Study_Area")
arcpy.conversion.ExportFeatures(twp_layer, study_area)
print_messages()
print("Study_Area created in the DLS feature dataset")
print("")

# Remove the intermediate, non-essential township data
arcpy.management.Delete(out_twp)
print("Intermediate raw_TWP deleted")
print("")

# Project the remaining ATS/DLS land fabric (Sections, Quarter Sections,
# Legal Subdivisions) and clip each one to the Study_Area.
# Note: Road Allowance (RA) is intentionally excluded per the assignment.

print("Processing DLS / ATS land fabric layers...")
print("")

# Dictionary of DLS shapefiles to process: {raw shapefile name : output name}
dls_layers = {
    "82I_SEC.shp": "Section",
    "82I_QTR.shp": "QuarterSection",
    "82I_LSD.shp": "LegalSubdivision"
}

for raw_name, out_name in dls_layers.items():
    print("Processing " + out_name + "...")

    # Project the raw shapefile into the geodatabase (NAD 1983 UTM Zone 12N)
    in_shp = os.path.join(root, "DLS", raw_name)
    out_projected = os.path.join(gdb, "raw_" + out_name)
    arcpy.management.Project(in_shp, out_projected, UTM12N)
    print_messages()

    # Clip the projected layer to the Study_Area so it does not extend
    # beyond the boundary of the study area
    out_clip = os.path.join(gdb, "DLS", out_name)
    arcpy.analysis.Clip(out_projected, study_area, out_clip)
    print_messages()
    print(out_name + " clipped to Study_Area")

    # Remove the intermediate, non-essential projected data
    arcpy.management.Delete(out_projected)
    print("Intermediate raw_" + out_name + " deleted")
    print("")


# Process the 1:20,000 Base Features.
# Each base feature exists as two shapefiles (one per NTS quarter:
# 82I11NW and 82I14SW) that are missing a coordinate system.
# Workflow:
#       1. Define Projection -> NAD_1983_10TM_AEP_Resource
#       2. Project -> NAD_1983_UTM_Zone_12N
#       3. Merge the two NTS quarters into one feature class
#       4. Clip the merged feature class to the Study_Area


print("Processing 1:20,000 Base Features...")
print("")

# Path to each NTS quarter's raw Base Feature shapefiles
nts_82I11NW = os.path.join(root, "Base", "82I11NW", "82I11NW")
nts_82I14SW = os.path.join(root, "Base", "82I14SW")

# Dictionary of base feature shapefiles to process:
# {raw shapefile name : output name in Base_Features}
base_features = {
    "BF_CONTOUR_ARC.shp": "Contours",
    "BF_CUT_TRAIL_ARC.shp": "Trails",
    "BF_PIPELINE_ARC.shp": "Pipelines",
    "BF_POWERLINE_ARC.shp": "Powerlines",
    "BF_ROAD_ARC.shp": "Roads"
}

for raw_name, out_name in base_features.items():
    print("Processing " + out_name + "...")

    # 82I11NW quarter
    in_11nw = os.path.join(nts_82I11NW, raw_name)
    defined_11nw = os.path.join(gdb, out_name + "_82I11NW_Unprojected")
    # Import the raw shapefile into the gdb (the source has no projection)
    arcpy.conversion.FeatureClassToFeatureClass(in_11nw, gdb, out_name + "_82I11NW_Unprojected")
    # Define the projection as NAD_1983_10TM_AEP_Resource
    arcpy.management.DefineProjection(defined_11nw, AEP_10TM)
    # Project into NAD_1983_UTM_Zone_12N
    projected_11nw = os.path.join(gdb, out_name + "_82I11NW_Projected")
    arcpy.management.Project(defined_11nw, projected_11nw, UTM12N)
    print_messages()

    # 82I14SW quarter
    in_14sw = os.path.join(nts_82I14SW, raw_name)
    defined_14sw = os.path.join(gdb, out_name + "_82I14SW_Unprojected")
    arcpy.conversion.FeatureClassToFeatureClass(in_14sw, gdb, out_name + "_82I14SW_Unprojected")
    arcpy.management.DefineProjection(defined_14sw, AEP_10TM)
    projected_14sw = os.path.join(gdb, out_name + "_82I14SW_Projected")
    arcpy.management.Project(defined_14sw, projected_14sw, UTM12N)
    print_messages()

    # Merge the two projected NTS quarters into a single feature class
    merged = os.path.join(gdb, out_name + "_Merged")
    arcpy.management.Merge([projected_11nw, projected_14sw], merged)
    print_messages()

    # Clip the merged feature class to the Study_Area
    out_clip = os.path.join(gdb, "Base_Features", out_name)
    arcpy.analysis.Clip(merged, study_area, out_clip)
    print_messages()
    print(out_name + " merged and clipped to Study_Area")

    # Remove all intermediate, non-essential data
    arcpy.management.Delete(defined_11nw)
    arcpy.management.Delete(projected_11nw)
    arcpy.management.Delete(defined_14sw)
    arcpy.management.Delete(projected_14sw)
    arcpy.management.Delete(merged)
    print("Intermediate " + out_name + " data deleted")
    print("")



# List the features within each feature dataset and describe the
# final spatial reference of each feature class

print("Final feature class list and spatial reference for each dataset")
print("")

final_locations = [
    gdb,
    os.path.join(gdb, "DLS"),
    os.path.join(gdb, "Base_Features")
]

for location in final_locations:
    arcpy.env.workspace = location
    fcList = arcpy.ListFeatureClasses()
    print("Location:", location)
    for fc in fcList:
        fcDesc = arcpy.Describe(fc)
        print("    Name:", fc)
        print("        Shape Type:", fcDesc.shapeType)
        print("        Spatial Reference:", fcDesc.spatialReference.name)
    print("")


# Only the final datasets are stored in the geodatabase.
# All intermediate and non-essential features were already removed

print("Intermediate and non-essential data removed")
print("")

# Use a cursor to identify and print the full DLS description of the
# single Legal Subdivision that the GPS point falls within

print("Printing the DLS description for the LSD containing the GPS point")
print("")

lsd_fc = os.path.join(gdb, "DLS", "LegalSubdivision")

# Make feature layers so the LSD that contains the GPS point can be selected
lsd_layer = arcpy.management.MakeFeatureLayer(lsd_fc, "lsd_layer")
gps_layer2 = arcpy.management.MakeFeatureLayer(out_gps, "gps_layer2")

# Select the single LSD polygon that CONTAINS the GPS point
arcpy.management.SelectLayerByLocation(lsd_layer, "CONTAINS", gps_layer2, "", "NEW_SELECTION")
print_messages()
print("LSD containing the GPS point selected")
print("")

# Use a search cursor on the selected LSD only to read the fields needed
# to build the DLS description. Field names follow the standard ATS schema
found = False
with arcpy.da.SearchCursor(lsd_layer, ["LSD", "SEC", "TWP", "RGE", "MER"]) as cursor:
    for row in cursor:
        found = True
        lsd, sec, twp, rge, mer = row
        print("LSD" + str(lsd).zfill(2) + " - Sec" + str(sec).zfill(2) + " - Twp" + str(twp)
              + " - Rge" + str(rge) + " - W" + str(mer))

# Defensive check in case the GPS point does not fall within any LSD
if not found:
    print("No LSD was found containing the GPS point - check the GPS point location")
print("")

# Assignment complete :)

print("Script complete - Assignment02.gdb has been created at " + root)


'''
Sources Consulted:

An Overview of ArcPy functions
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/alphabetical-list-of-arcpy-functions.htm
Clip (Analysis)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/clip.htm
Create Feature Dataset (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-feature-dataset.htm
Create File GDB (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/create-file-gdb.htm
Define Projection (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/define-projection.htm
Delete (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/delete.htm
Describe
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/describe.htm
Exists
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/exists.htm
Export Features (Conversion)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/export-features.htm
Feature Class To Feature Class (Conversion)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/conversion/feature-class-to-feature-class.htm
GetMessage / GetMessageCount
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/getmessage.htm
Introduction to ArcPy
    https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm
ListFeatureClasses
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listfeatureclasses.htm
Make Feature Layer (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/make-feature-layer.htm
Merge (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/merge.htm
Project (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/project.htm
SearchCursor
    https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm
Select Layer By Location (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/select-layer-by-location.htm
SpatialReference
    https://pro.arcgis.com/en/pro-app/latest/arcpy/classes/spatialreference.htm
'''