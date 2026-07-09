#-------------------------------------------------------------------------------
# Name:        GEOS456_Assign01 (CORRECTED REFERENCE VERSION)
# Purpose:     To incorporate geoprocessing techniques into high-level
#              programming (HLP) language - identify the top 3 townships
#              (communes) in Toulouse containing the most cycling network.
#
# Author:      John Abboud
# Date:        03/06/2026
#
# NOTE: This is a corrected reference copy made after grading, kept for
# future reference. Original error: line ~135 failed because
# CalculateGeometryAttributes_management was run with "LENGTH" on every
# intersected feature class. The instructor confirmed this fails whenever a
# feature class with a different geometry type (e.g. a polygon) is mixed in
# with polylines, since "LENGTH" is not a valid geometry property for
# polygons. The fix below uses arcpy.Describe().shapeType to check each
# feature class's actual geometry type at run time and calculates LENGTH
# for polylines or AREA for polygons accordingly - so the script adapts
# correctly no matter which input layers turn out to be which geometry type.
#-------------------------------------------------------------------------------

import arcpy, os

# Allow existing outputs to be overwritten
arcpy.env.overwriteOutput = True

# FIX: Set the workspace to the root assignment folder, as required by the
# instructor, so the script can be run directly from C:\GEOS456\Assign01
arcpy.env.workspace = r"C:\GEOS456\Assign01"
root = arcpy.env.workspace

# Path to geodatabase where all outputs will be stored
gdb = os.path.join(root, "Toulouse.gdb")

# Define the coordinate system for projection
projection = arcpy.SpatialReference("NTF (PARIS) Lambert Sud France")

#--------------------------------------------------
# 1. FIND AND PROJECT ALL SHAPEFILES

print("1. RAW data (shapefiles) in the folder:")

# Raw data is stored in two subfolders beneath the root workspace
raw_folders = [
    os.path.join(root, "communes"),
    os.path.join(root, "reseau-cyclable-et-vert")
]

for folder in raw_folders:
    arcpy.env.workspace = folder
    fcs = arcpy.ListFeatureClasses()

    for fc in fcs:
        print(" - " + fc)  # print file name

        # Create output name for projected feature
        out_name = fc.replace(".shp", "_projected")

        # Full path to save the projected file inside the geodatabase
        out_path = os.path.join(gdb, out_name)

        # Run projection tool
        arcpy.management.Project(fc, out_path, projection)

print("")

#--------------------------------------------------
# 2. LIST FEATURES INSIDE THE GDB (BEFORE INTERSECT)

# Switch workspace to geodatabase
arcpy.env.workspace = gdb

print("2. Features stored in gdb before intersecting:")

# Get all feature classes in the gdb
fc_list = arcpy.ListFeatureClasses()

for fc in fc_list:
    print(" - " + fc)

print("")

#--------------------------------------------------
# 3. SEPARATE NETWORKS AND TOWNSHIPS

networks = []   # will store cycling network layers
township = ""   # will store commune layer

for fc in fc_list:

    # Select only the cycling/green network layers
    if "Cyclable" in fc or "ReseauVert" in fc:
        networks.append(fc)

    # Identify the township layer (communes)
    if "commune" in fc.lower():
        township = fc

#--------------------------------------------------
# 4. INTERSECT NETWORKS WITH TOWNSHIPS

# This step splits cycling/green networks by township boundaries
for fc in networks:

    out_fc = fc + "_by_commune"

    # Intersect tool combines geometry from both layers
    arcpy.analysis.Intersect([fc, township], out_fc)

    print(fc + " successfully intersected")
    print("")

#--------------------------------------------------
# 5. LIST FEATURES AFTER INTERSECT

print("2.Below is the list of features stored in gdb after intersecting:")

fc_list = arcpy.ListFeatureClasses()

for fc in fc_list:
    print(" - " + fc)

print("")

#--------------------------------------------------
# 6. ADD A LENGTH/AREA FIELD AND CALCULATE GEOMETRY
#
# FIX: "LENGTH" is only a valid geometry property for polylines - using it
# on a polygon causes a tool error. arcpy.Describe().shapeType is used here
# to check each feature class's actual geometry type before deciding
# whether to calculate LENGTH or AREA, rather than assuming based on name.

intersects = arcpy.ListFeatureClasses("*_by_commune")

# Add a field to each intersected feature class - DOUBLE works for both
# a length value (km) or an area value (sq km)
for fc in intersects:
    fcDesc = arcpy.Describe(fc)

    if fcDesc.shapeType == "Polygon":
        arcpy.management.AddField(fc, "Area_SqKM", "DOUBLE")
        print("Area_SqKM field added to " + fc + " (Polygon)")
    else:
        arcpy.management.AddField(fc, "Length_KM", "DOUBLE")
        print("Length_KM field added to " + fc + " (Polyline)")
    print("")

# Calculate geometry attributes based on each feature class's shape type
for fc in intersects:
    fcDesc = arcpy.Describe(fc)

    if fcDesc.shapeType == "Polygon":
        arcpy.management.CalculateGeometryAttributes(
            fc,
            [["Area_SqKM", "AREA"]],
            area_unit="SQUARE_KILOMETERS"
        )
        print("Area_SqKM calculated successfully for " + fc)
    else:
        arcpy.management.CalculateGeometryAttributes(
            fc,
            [["Length_KM", "LENGTH"]],
            length_unit="KILOMETERS"
        )
        print("Length_KM calculated successfully for " + fc)
    print("")

#--------------------------------------------------
# 7. SUMMARIZE TOTAL LENGTH/AREA PER TOWNSHIP

# Create summary tables (sum of length or area per township)
for fc in intersects:
    fcDesc = arcpy.Describe(fc)
    out_table = fc + "_sum"

    if fcDesc.shapeType == "Polygon":
        arcpy.analysis.Statistics(
            fc,
            out_table,
            [["Area_SqKM", "SUM"]],
            "libelle"
        )
    else:
        arcpy.analysis.Statistics(
            fc,
            out_table,
            [["Length_KM", "SUM"]],
            "libelle"
        )

print("")

#--------------------------------------------------
# 8. PRINT TOP 3 TOWNSHIPS FOR EACH NETWORK

print("Below is the summary table of the top 3 townships:")

# Get all summary tables
tables = arcpy.ListTables("*_sum")

for table in tables:

    # Recover the original intersected feature class name from the table
    # name (table name = fc name + "_sum") so its shape type can be
    # checked directly, instead of guessing the field from the layer name
    fc_name = table.replace("_sum", "")
    fcDesc = arcpy.Describe(fc_name)

    if fcDesc.shapeType == "Polygon":
        field_name = "SUM_Area_SqKM"
        unit_label = "sq km"
    else:
        field_name = "SUM_Length_KM"
        unit_label = "km"

    # Assign a readable label based on the table name
    if "Bande_Cyclable" in table:
        label = "Bande Cyclable"
    elif "Piste_Cyclable" in table:
        label = "Piste Cyclable"
    elif "ReseauVert" in table:
        label = "ReseauVert"
    else:
        label = table

    print("\nTop 3 townships - " + label + ":")

    rows = []

    # Read table values using a search cursor
    with arcpy.da.SearchCursor(table, ["libelle", field_name]) as sc:
        for row in sc:
            rows.append([row[0], row[1]])

    # Sort rows manually from highest to lowest
    for x in range(len(rows)):
        for y in range(x + 1, len(rows)):
            if rows[y][1] > rows[x][1]:
                temp = rows[x]
                rows[x] = rows[y]
                rows[y] = temp

    # Print the top 3 results only
    count = 0
    for item in rows:
        print(" - {0}: {1:.2f} {2}".format(item[0], item[1], unit_label))
        count += 1
        if count == 3:
            break

print("")
print("Assignment complete!")


#-------------------------------------------------------------------------------
# Sources Consulted
#-------------------------------------------------------------------------------
'''
ArcGIS Pro Documentation:

Project (Data Management)
https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/project.htm

Intersect (Analysis)
https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/intersect.htm

Add Field (Data Management)
https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/add-field.htm

Calculate Geometry Attributes (Data Management)
https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/calculate-geometry-attributes.htm

Summary Statistics (Analysis)
https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/summary-statistics.htm

ListFeatureClasses (ArcPy)
https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listfeatureclasses.htm

Describe (ArcPy)
https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/describe.htm

General ArcPy Reference
https://pro.arcgis.com/en/pro-app/latest/arcpy/get-started/what-is-arcpy-.htm
'''