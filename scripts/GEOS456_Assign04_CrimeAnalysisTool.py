#-------------------------------------------------------------------------------
# Name:        Assignment 4: Custom Geoprocessing Tool - Crime Analysis
# Purpose:     Custom script tool for the City of Nice Place police department.
#              For each of three crime types, intersects the crime points with
#              the Precincts feature class and produces a table (sorted
#              ascending by frequency) showing how many of that crime type
#              occurred in each precinct. Separately, buffers Landmarks by a
#              user-supplied distance (forced to metres) and determines how
#              many assaults occur within that distance of a landmark, and
#              which landmark is most associated with assaults.
#
# Author:      John Abboud
# Created:     26/07/2026
#-------------------------------------------------------------------------------
#
# TOOL SETUP (to be done once in ArcGIS Pro, not in this file):
#   1. In the City_of_Nice_Place.gdb, create a new toolbox named "Crime_Analysis"
#      (toolbox names can't contain spaces - use an underscore, same as the
#      "Custom_Tools" toolbox from the Mod 8 Activity 1 handout)
#   2. Right-click the toolbox -> Add -> Script
#        Name:  CrimeAnalysisTool
#        Label: Crime Analysis Tool
#        Script File: point this to this .py file (Store tool with relative path)
#   3. On the Parameters page, define the 5 parameters IN THIS ORDER:
#
#        # | Label            | Name            | Data Type     | Type     | Direction
#        --|------------------|-----------------|---------------|----------|----------
#        0 | Workspace        | Workspace       | Workspace     | Required | Input
#        1 | Crime Type 1     | Crime_Type_1    | Feature Class | Required | Input
#        2 | Crime Type 2     | Crime_Type_2    | Feature Class | Required | Input
#        3 | Crime Type 3     | Crime_Type_3    | Feature Class | Required | Input
#        4 | Buffer Distance  | Buffer_Distance | Linear Unit   | Required | Input
#
#   4. In the tool's Item Description (Catalog -> right-click tool -> Edit
#      Metadata / Properties), add a Summary describing the tool's purpose
#      (see the docstring above) and a short description for each parameter,
#      e.g. "The geodatabase workspace where all outputs will be saved",
#      "One of the three crime feature classes to analyze (Arsons, Assault,
#      or burglaries can be provided in any order)", "The search distance
#      around each landmark, in any linear unit - it will be converted to
#      metres automatically".
#-------------------------------------------------------------------------------

# Import arcpy, os and the Spatial Analyst module (os is used to pull short
# names out of the full feature class paths passed in as parameters)
import arcpy
import os
from arcpy import env

# Allow outputs to be overwritten if the tool is re-run
env.overwriteOutput = True


# Helper function used after every geoprocessing tool - writes the first and
# last message from the most recently run tool to the tool's Messages panel
def add_tool_messages():
    msgCount = arcpy.GetMessageCount()
    if msgCount > 0:
        arcpy.AddMessage(arcpy.GetMessage(0))
        arcpy.AddMessage(arcpy.GetMessage(msgCount - 1))


try:
    # ---------------------------------------------------------------------
    # Read in the 5 required parameters
    # ---------------------------------------------------------------------
    workspace = arcpy.GetParameterAsText(0)
    crimeType1 = arcpy.GetParameterAsText(1)
    crimeType2 = arcpy.GetParameterAsText(2)
    crimeType3 = arcpy.GetParameterAsText(3)
    bufferDistanceInput = arcpy.GetParameterAsText(4)

    env.workspace = workspace

    arcpy.AddMessage("Workspace set to: " + workspace)
    arcpy.AddMessage("")

    # Force the buffer distance to metres regardless of what unit was
    # selected on the Linear Unit parameter. GetParameterAsText on a Linear
    # Unit parameter returns a string like "250 Meters" or "250 Unknown" -
    # only the numeric portion is kept, then "Meters" is appended. Passing
    # an explicit linear unit like this to Buffer causes ArcGIS to perform a
    # geodesic buffer in true metres even on unprojected data.
    distanceValue = bufferDistanceInput.split()[0]
    bufferDistance = distanceValue + " Meters"
    arcpy.AddMessage("Buffer distance forced to: " + bufferDistance)
    arcpy.AddMessage("")

    # Precinct field used to group crime frequency by precinct. Verify this
    # matches your Precincts attribute table (printed below at runtime).
    precinct_field = "Precinct"

    # Field on Landmarks used to identify each landmark by name. Verify this
    # matches your Landmarks attribute table (printed below at runtime) and
    # update if it differs.
    landmark_field = "LANDNAME"

    # Print the field lists for Precincts and Landmarks so the field names
    # above can be confirmed against the actual data
    arcpy.AddMessage("Fields on Precincts: " + str([f.name for f in arcpy.ListFields("Precincts")]))
    arcpy.AddMessage("Fields on Landmarks: " + str([f.name for f in arcpy.ListFields("Landmarks")]))
    arcpy.AddMessage("")

    # ---------------------------------------------------------------------
    # Part 1: Intersect each crime type with Precincts and summarize the
    #         frequency of that crime type per precinct
    # ---------------------------------------------------------------------

    crimeTypes = [crimeType1, crimeType2, crimeType3]
    sortedTables = []   # keep track of the 3 sorted output tables for Part 1c

    for crimeFC in crimeTypes:

        crimeName = os.path.basename(crimeFC)
        arcpy.AddMessage("Processing crime type: " + crimeName)

        # Intersect this crime type with the Precincts feature class
        intersectOut = "Precincts_" + crimeName
        arcpy.analysis.Intersect([crimeFC, "Precincts"], intersectOut)
        add_tool_messages()

        # Count how many crime points fall in each precinct
        freqTemp = "Precinct_" + crimeName + "_freq_temp"
        arcpy.analysis.Frequency(intersectOut, freqTemp, [precinct_field])
        add_tool_messages()

        # Sort the frequency table ascending, as required by the assignment
        sortedOut = "Precinct_" + crimeName + "_Sorted"
        arcpy.management.Sort(freqTemp, sortedOut, [["FREQUENCY", "ASCENDING"]])
        add_tool_messages()

        # Remove the intermediate, non-essential frequency table
        arcpy.management.Delete(freqTemp)

        sortedTables.append((crimeName, sortedOut))
        arcpy.AddMessage(crimeName + " frequency by precinct saved to " + sortedOut)
        arcpy.AddMessage("")

    # Print the contents of all 3 sorted tables to the tool messages
    arcpy.AddMessage("Results - crime frequency by precinct (ascending order):")
    for crimeName, table in sortedTables:
        arcpy.AddMessage("  " + crimeName + " (" + table + "):")
        with arcpy.da.SearchCursor(table, [precinct_field, "FREQUENCY"]) as cursor:
            for row in cursor:
                arcpy.AddMessage("      Precinct " + str(row[0]) + " - Frequency: " + str(row[1]))
    arcpy.AddMessage("")

    # ---------------------------------------------------------------------
    # Part 2: Buffer the Landmarks and determine assault proximity
    # ---------------------------------------------------------------------

    # Identify which of the 3 crime type inputs represents assaults, based
    # on the feature class name rather than assuming a fixed parameter order
    assaultFC = None
    for crimeFC in crimeTypes:
        if "assault" in os.path.basename(crimeFC).lower():
            assaultFC = crimeFC
            break

    if assaultFC is None:
        arcpy.AddWarning("None of the 3 crime type inputs appears to be the "
                          "Assault feature class (name did not contain "
                          "'assault'). Skipping the landmark proximity "
                          "analysis in Part 2.")
    else:
        arcpy.AddMessage("Assault feature class identified as: " + os.path.basename(assaultFC))
        arcpy.AddMessage("")

        # Buffer the landmarks by the forced-metres distance
        bufferOut = "Landmarks_Buffer_" + distanceValue + "m"
        arcpy.analysis.Buffer("Landmarks", bufferOut, bufferDistance)
        add_tool_messages()

        # Intersect assaults with the landmark buffers (per-landmark - one
        # row per assault PER landmark buffer it falls inside). This is
        # correct for the per-landmark breakdown below, but if two landmark
        # buffers overlap, a single assault that falls in the overlap gets
        # a row for each landmark - so this dataset must NOT be used to
        # count total assaults, or that assault gets double-counted.
        landmarksAssaultsOut = "Landmarks_Assaults"
        arcpy.analysis.Intersect([assaultFC, bufferOut], landmarksAssaultsOut)
        add_tool_messages()

        # a) How many assaults occur within the buffer distance of a landmark?
        # Build a second, DISSOLVED version of the buffer so overlapping
        # landmark buffers merge into a single polygon. An assault sitting
        # in an overlap zone then only intersects that merged shape once,
        # regardless of how many individual landmarks it was near - giving
        # an accurate, non-duplicated count.
        bufferDissolved = "Landmarks_Buffer_" + distanceValue + "m_Dissolved"
        arcpy.analysis.Buffer("Landmarks", bufferDissolved, bufferDistance, dissolve_option="ALL")
        add_tool_messages()

        assaultsUniqueOut = "Landmarks_Assaults_Unique_temp"
        arcpy.analysis.Intersect([assaultFC, bufferDissolved], assaultsUniqueOut)
        add_tool_messages()

        assaultCount = arcpy.management.GetCount(assaultsUniqueOut)[0]

        # Remove the intermediate dissolved-buffer datasets - they exist
        # only to produce an accurate count and aren't part of the required
        # final outputs
        arcpy.management.Delete(bufferDissolved)
        arcpy.management.Delete(assaultsUniqueOut)

        # Count assaults per landmark
        landmarksFreqTemp = "Landmarks_Assaults_freq_temp"
        arcpy.analysis.Frequency(landmarksAssaultsOut, landmarksFreqTemp, [landmark_field])
        add_tool_messages()

        # Sort descending so the top row is the landmark with the most
        # associated assaults - directly answers question 2b
        landmarksSortedOut = "Landmarks_Assaults_Sorted"
        arcpy.management.Sort(landmarksFreqTemp, landmarksSortedOut, [["FREQUENCY", "DESCENDING"]])
        add_tool_messages()

        # Remove the intermediate, non-essential frequency table
        arcpy.management.Delete(landmarksFreqTemp)

        # b) Which landmark is this type of crime most likely to occur near?
        topLandmark = None
        topFrequency = None
        with arcpy.da.SearchCursor(landmarksSortedOut, [landmark_field, "FREQUENCY"]) as cursor:
            for row in cursor:
                if topLandmark is None:
                    topLandmark, topFrequency = row[0], row[1]

        # c) Print the results of this table to the tool messages
        arcpy.AddMessage("Results - assaults by landmark (descending order):")
        with arcpy.da.SearchCursor(landmarksSortedOut, [landmark_field, "FREQUENCY"]) as cursor:
            for row in cursor:
                arcpy.AddMessage("      " + str(row[0]) + " - Frequency: " + str(row[1]))
        arcpy.AddMessage("")

        # Final plain-language answers to Question 2, as required
        arcpy.AddMessage("There are " + str(assaultCount) + " assaults that occur within "
                          + distanceValue + " metres of a landmark.")
        arcpy.AddMessage("Assaults are most likely to occur near the " + str(topLandmark)
                          + " landmark (" + str(topFrequency) + " occurrences).")

    arcpy.AddMessage("")
    arcpy.AddMessage("Crime Analysis tool complete.")

except Exception as e:
    arcpy.AddError("The Crime Analysis tool encountered an error: " + str(e))


'''
Sources Consulted:

An Overview of ArcPy functions
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/alphabetical-list-of-arcpy-functions.htm
AddMessage / AddWarning / AddError
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/addmessage.htm
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/addwarning.htm
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/adderror.htm
Buffer (Analysis)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/buffer.htm
Delete (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/delete.htm
Frequency (Analysis)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/frequency.htm
GetCount (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/get-count.htm
GetMessage / GetMessageCount
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/getmessage.htm
GetParameterAsText
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/getparameterastext.htm
Intersect (Analysis)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/analysis/intersect.htm
ListFields
    https://pro.arcgis.com/en/pro-app/latest/arcpy/functions/listfields.htm
SearchCursor
    https://pro.arcgis.com/en/pro-app/latest/arcpy/data-access/searchcursor-class.htm
Sort (Data Management)
    https://pro.arcgis.com/en/pro-app/latest/tool-reference/data-management/sort.htm
Script Tools
    https://pro.arcgis.com/en/pro-app/latest/arcpy/geoprocessing-and-python/defining-parameters-in-a-script-tool.htm
'''
