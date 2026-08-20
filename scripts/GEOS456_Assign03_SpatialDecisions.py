#-------------------------------------------------------------------------------
# Name:        Assignment 3: Spatial Decisions Using Raster Datasets
# Purpose:     The purpose of this assignment is to apply grid statistics to
#              analyze raster datasets using high-level programming (HLP) language
#              through geographic information system (GIS) extensions.
#
# Author:      John Abboud
# Created:     15/07/2026
#-------------------------------------------------------------------------------

# Import arcpy and the Spatial Analyst module
import arcpy
from arcpy import env
from arcpy.sa import *

# Set environment workspace and overwrite properties
env.workspace = r"C:\GEOS456\Assign03\Spatial_Decisions.gdb"
env.overwriteOutput = True

# Check out the Spatial Analyst extension so it can be used
arcpy.CheckOutExtension("Spatial")
print("Spatial Analyst extension checked out and ready to use.")
print("")


# Helper function used after every geoprocessing tool
# prints the first and last message returned by the most recently run tool
def print_messages():
    msgCount = arcpy.GetMessageCount()
    if msgCount > 0:
        print(arcpy.GetMessage(0))
        print(arcpy.GetMessage(msgCount - 1))


# See what is available in the workspace before starting
print("Contents of Spatial_Decisions.gdb")
print("    Rasters:", arcpy.ListRasters())
print("    Feature Classes:", arcpy.ListFeatureClasses())
print("    Tables:", arcpy.ListTables())
print("")


# -------------------------------------------------------------------------
# Part 1: Describe the dem raster dataset properties
# -------------------------------------------------------------------------

print("Part 1: Describing the dem raster dataset")
print("")

dem = arcpy.Raster("dem")
demDesc = arcpy.Describe("dem")

print("Data format:", demDesc.format)
print("Cell size (x):", demDesc.meanCellWidth)
print("Cell size (y):", demDesc.meanCellHeight)
print("Coordinate system:", demDesc.spatialReference.name)
print("")


# -------------------------------------------------------------------------
# Part 2: Apply suitability criteria to the dem and geolgrid rasters
#   a. Elevation: 1,000 m to 1,550 m
#   b. Slope: <= 18 degrees
#   c. Geology Type: Madison Limestone
# -------------------------------------------------------------------------

print("Part 2: Applying suitability criteria")
print("")

geolgrid = arcpy.Raster("geolgrid")

# Print the geolgrid attribute table so the correct VALUE code for
# "Madison Limestone" can be confirmed before it is used below.
print("geolgrid attribute table (confirm the Madison Limestone VALUE here):")
geolFields = [f.name for f in arcpy.ListFields("geolgrid")]
with arcpy.da.SearchCursor("geolgrid", geolFields) as cursor:
    for row in cursor:
        print("   ", row)
print("")

# a. Elevation criteria: 1,000 m to 1,550 m
print("Creating elevation criteria raster (1,000 m - 1,550 m)...")
elev_crit = (dem >= 1000) & (dem <= 1550)
elev_crit.save("elev_crit")
print_messages()
print("Elevation criteria raster created and saved as elev_crit")
print("")

# b. Slope criteria: <= 18 degrees
print("Creating a slope raster (degrees) from the dem...")
slopeRaster = Slope(dem, "DEGREE")
slopeRaster.save("slope")
print_messages()
print("Slope raster created and saved as slope")
print("")

print("Creating slope criteria raster (<= 18 degrees)...")
slope_crit = (slopeRaster <= 18)
slope_crit.save("slope_crit")
print_messages()
print("Slope criteria raster created and saved as slope_crit")
print("")

# c. Geology criteria: Madison Limestone
madison_limestone_code = 7

print("Creating geology criteria raster (Madison Limestone)...")
geol_crit = (geolgrid == madison_limestone_code)
geol_crit.save("geol_crit")
print_messages()
print("Geology criteria raster created and saved as geol_crit")
print("")

# Confirm the three criteria rasters were created successfully
print("elev_crit exists:", arcpy.Exists("elev_crit"))
print("slope_crit exists:", arcpy.Exists("slope_crit"))
print("geol_crit exists:", arcpy.Exists("geol_crit"))
print("")


# -------------------------------------------------------------------------
# Part 2i: Combine the criteria rasters and summarize the suitable pixels
#   • Number of cells
#   • Area in square metres
#   • Average elevation
# -------------------------------------------------------------------------

print("Combining criteria rasters into one final suitability raster...")
final_criteria = Raster("elev_crit") * Raster("slope_crit") * Raster("geol_crit")
final_criteria.save("final_criteria")
print_messages()
print("Final criteria raster created and saved as final_criteria")
print("")

print("Running Zonal Statistics as Table on the final criteria raster...")
zonalTable = "Mean_Elev_Stats"
ZonalStatisticsAsTable("final_criteria", "VALUE", dem, zonalTable, "DATA", "MEAN")
print_messages()
print("Zonal statistics table created:", zonalTable)
print("")

print("Results - suitable pixels (Elevation + Slope + Geology criteria):")
with arcpy.da.SearchCursor(zonalTable, ["VALUE", "COUNT", "AREA", "MEAN"]) as cursor:
    for row in cursor:
        # VALUE = 1 means all three criteria were met for that pixel
        if row[0] == 1:
            print("    Number of suitable cells:", row[1])
            print("    Suitable area (sq m):", row[2])
            print("    Average elevation (m):", round(row[3], 2))
print("")


# -------------------------------------------------------------------------
# Part 3: Mean slope for selected watersheds (wshds2c)
#   WSHD2SC_ID: 291, 313, 525
# -------------------------------------------------------------------------

print("Part 3: Mean slope statistics for selected watersheds")
print("")

wshds = "wshds2c"

# Confirm the actual ID field name on the watershed feature class
print("Fields on wshds2c:")
for f in arcpy.ListFields(wshds):
    print("   ", f.name)
print("")

id_field = "WSHDS2C_ID"

# Add field delimiters to keep the where clause valid regardless of format
field_delim = arcpy.AddFieldDelimiters(wshds, id_field)
where_clause = field_delim + " IN (291, 313, 525)"

print("Creating a feature layer for the three required watersheds...")
wshd_layer = arcpy.management.MakeFeatureLayer(wshds, "wshd_lyr", where_clause)
print_messages()
print("Watershed layer created")
print("")

print("Running Zonal Statistics as Table on watershed slope...")
wshdTable = "watershed_slope_stats"
ZonalStatisticsAsTable(wshd_layer, id_field, slopeRaster, wshdTable, "DATA", "MEAN")
print_messages()
print("Watershed slope statistics table created:", wshdTable)
print("")

print("Results - mean slope (degrees) by watershed:")
with arcpy.da.SearchCursor(wshdTable, [id_field, "MEAN"]) as cursor:
    for row in cursor:
        print(f"    Watershed {row[0]} - mean slope (degrees): {row[1]:.2f}")
print("")


# Return the Spatial Analyst extension to the license manager
arcpy.CheckInExtension("Spatial")
print("Spatial Analyst extension returned to the license manager.")
print("")

# Assignment complete :)
print("Script complete - Assignment 3 analysis finished in Spatial_Decisions.gdb")


'''
Sources Consulted:

An Overview of ArcPy functions
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/alphabetical-list-of-arcpy-functions.htm
AddFieldDelimiters
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/addfielddelimiters.htm
CheckOutExtension / CheckInExtension
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/checkoutextension.htm
Describe
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/describe.htm
Exists
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/exists.htm
GetMessage / GetMessageCount
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/getmessage.htm
ListFields
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listfields.htm
ListRasters
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listrasters.htm
Make Feature Layer (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/make-feature-layer.htm
Raster Calculator / Map Algebra operators
    https://pro.arcgis.com/en/pro-app/latest/arcpy/spatial-analyst/raster-calculator.htm
SearchCursor
    https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm
Slope (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/slope.htm
Zonal Statistics as Table (Spatial Analyst)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/spatial-analyst/zonal-statistics-as-table.htm
'''