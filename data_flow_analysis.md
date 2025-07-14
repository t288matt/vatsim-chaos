# Python Scripts Data Flow Analysis

## Overview
This document provides a comprehensive analysis of all Python scripts in the ATC Conflict Analysis System, showing their input data sources and output data files based on actual code analysis.

## Data Flow Table

| Script | Input Data Sources | Output Data Files | Description |
|--------|-------------------|-------------------|-------------|
| **execute.py** | None (orchestrator) | None (orchestrator) | Master workflow script that runs all other scripts in sequence |
| **extract_simbrief_xml_flightplan.py** | • `*.xml` files (SimBrief XML flight plans)<br>• Directory: `.` (current directory) | • `temp/<FLIGHT_ID>_data.json`<br>• `temp/<FLIGHT_ID>.kml` | Extracts flight plan data from SimBrief XML files and creates JSON/KML outputs |
| **find_potential_conflicts.py** | • `temp/*_data.json` files<br>• Directory: `temp/` | • `temp/conflict_analysis.log`<br>• `temp/potential_conflict_data.json`<br>• `temp/routes_with_added_interpolated_points.json`<br>• `conflict_list.txt` | Analyzes flight plans for potential conflicts and generates conflict reports |
| **merge_kml_flightplans.py** | • `temp/*.kml` files<br>• Directory: `temp/` | • `merged_flightplans.kml` | Merges individual KML files into a single KML for Google Earth visualization |
| **generate_schedule_conflicts.py** | • `temp/potential_conflict_data.json`<br>• `temp/routes_with_added_interpolated_points.json` | • `temp/routes_with_added_interpolated_points.json` (updated)<br>• `pilot_briefing.txt` | Schedules conflicts and updates interpolated points with departure times and aircraft types |
| **generate_animation.py** | • `temp/potential_conflict_data.json`<br>• `temp/routes_with_added_interpolated_points.json`<br>• `temp/*_data.json` files | • `animation/animation_data.json`<br>• `animation/conflict_points.json` | Generates animation data for web visualization |
| **audit_conflict.py** | • `temp/potential_conflict_data.json`<br>• `temp/routes_with_added_interpolated_points.json`<br>• `animation/animation_data.json` | • `audit_conflict_output.txt` | Audits conflict data across all sources for consistency |
| **test_generate_schedule_conflicts.py** | • Test data (internal) | • Test outputs (internal) | Unit tests for generate_schedule_conflicts.py |
| **env.py** | • Environment variables | • Console output | Environment configuration script |

## Data File Types

### Input Files
- **XML Files**: SimBrief flight plan data (`*.xml`)
- **JSON Files**: Flight data, conflict data, interpolated points
- **KML Files**: Google Earth visualization files
- **Log Files**: Analysis logs and reports

### Output Files
- **JSON Files**: Processed flight data, animation data, conflict data
- **KML Files**: Flight plan visualizations
- **TXT Files**: Reports, briefings, audit outputs
- **HTML Files**: Web visualization (in animation/ directory)

## Data Flow Summary

1. **Extraction Phase**: XML → JSON/KML
2. **Analysis Phase**: JSON → Conflict Analysis → Reports
3. **Scheduling Phase**: Conflict Data → Scheduled Conflicts
4. **Animation Phase**: Scheduled Data → Animation Data
5. **Audit Phase**: All Data → Audit Report

## Key Data Transformations

- **Aircraft Type**: Added to all JSON files from XML extraction
- **Conflict Data**: Generated from flight plan analysis
- **Scheduling**: Applied to conflict points with departure times
- **Animation**: Converted to web-compatible format
- **Audit**: Cross-referenced across all data sources 