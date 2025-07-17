# ATC Conflict Generation System - Architecture Document

## System Overview

The ATC Conflict Analysis System is a Python-based application designed to analyse SimBrief XML flight plans and identify potential air traffic conflicts for event scenario creation. The system helps the events team build challenging events for controllers and fun, dynamic events for pilots. It processes multiple flight plans simultaneously, detects conflicts using 3D spatial analysis, and generates both detailed reports and visual outputs.

**Dual Interface Support**:
- **Command Line Interface**: Direct script execution for batch processing and automation
- **Web Interface**: Browser-based interface (`web/` directory) for interactive file upload, validation, and processing with real-time progress tracking

**Key Concept: First Conflicts**
The system focuses on identifying "first conflicts" - the initial point where two aircraft first meet conflict criteria during their flights. This is critical for event planning as it represents the moment when ATC first needs to intervene between aircraft pairs, rather than tracking every subsequent conflict between the same aircraft.

**Flight ID System**
The system now uses unique flight IDs (FLT0001, FLT0002, etc.) instead of origin-destination pairs for better conflict tracking and separation enforcement. Each flight gets a sequential flight ID during XML processing, which is maintained throughout the entire workflow.

**Altitude Handling**
The system uses a consistent altitude approach across backend and frontend:
- **Backend**: All altitudes are stored and processed in feet (e.g., 2000ft, 36000ft)
- **Frontend**: Altitudes are displayed using the transition altitude from `env.py` (TRANSITION_ALTITUDE_FT = 10500)
  - Below transition altitude: Displayed in feet (e.g., "8500ft")
  - At or above transition altitude: Displayed as flight levels (e.g., "FL350")
- **Translation Logic**: Frontend JavaScript converts feet to appropriate display format based on transition altitude

**Separation Rules**
The system enforces two key separation rules:
1. **Departure Separation**: Minimum 2 minutes between departures from the same airport
2. **Same Route Separation**: Minimum 5 minutes between flights with identical origin-destination

## Single Source of Truth Architecture

**Key Innovation: `temp/routes_with_added_interpolated_points.json`**

The system implements a true single source of truth approach where one comprehensive JSON file contains all necessary data:

### Why `find_potential_conflicts.py` creates the foundation:
1. **Route Interpolation**: The conflict detection algorithm needs to check for conflicts not just at waypoints, but also **between** waypoints. To do this accurately, it interpolates additional points along each route at regular intervals (every 2 nautical miles by default).

2. **Enhanced Conflict Detection**: By adding interpolated points, the system can detect conflicts that occur between the original waypoints, which is crucial for realistic ATC scenarios where aircraft don't just conflict at navigation points.

3. **Data Structure**: The interpolated points file contains:
   - Original waypoints from the flight plans
   - Additional interpolated points between waypoints
   - Each point has lat/lon/altitude/time data
   - This becomes the foundation for all downstream processing

4. **Single Source of Truth Foundation**: This file becomes the base that other scripts build upon. `generate_schedule_conflicts.py` then adds departure schedule metadata to it, and `generate_animation.py` reads from it.

### The Data Flow:
```
XML files → find_potential_conflicts.py → routes_with_added_interpolated_points.json (with interpolated points)
                                                                    ↓
generate_schedule_conflicts.py → adds departure schedule metadata
                                                                    ↓  
generate_animation.py → reads single source of truth
```

## Architecture Principles

- **Modular Design**: Clear separation between data extraction, analysis, reporting, and visualization
- **Single Responsibility**: Each component has a focused purpose
- **Data-Driven**: JSON-based data exchange between components
- **Visualization-First**: KML output for Google Earth integration
- **Event-Focused**: Optimised for event scenario workflows
- **First Conflict Priority**: Tracks only the initial conflict between aircraft pairs for ATC intervention planning
- **Linear Data Flow**: Eliminated circular dependencies through metadata-based approach
- **Accurate Scheduling**: Respects conflict generation departure times instead of "most conflicts" rule
- **Flight ID Tracking**: Uses unique flight IDs for better conflict tracking and separation enforcement
- **Single Source of Truth**: One comprehensive JSON file contains all flight data, conflicts, and scheduling
- **Backend-Centric Validation**: Web interface relies on backend for XML parsing and route validation due to browser limitations

## System Components

### Python Scripts - Input and Output Files

| Script | Input Files | Output Files |
|--------|-------------|--------------|
| **execute.py** | None (master script) | None (orchestrates other scripts) |
| **extract_simbrief_xml_flightplan.py** | `*.xml` (SimBrief XML files in root directory) | `temp/*_data.json` (individual flight data)<br>`temp/*.kml` (individual KML files) |
| **find_potential_conflicts.py** | `*.xml` (SimBrief XML files)<br>`temp/*_data.json` (individual flight data) | `temp/potential_conflict_data.json` (conflict generation)<br>`conflict_list.txt` (formatted conflict report)<br>`temp/routes_with_added_interpolated_points.json` (interpolated routes) |
| **merge_kml_flightplans.py** | `temp/*.kml` (individual KML files) | `merged_flightplans.kml` (merged KML for Google Earth) |
| **generate_schedule_conflicts.py** | `temp/potential_conflict_data.json` (conflict generation)<br>`temp/routes_with_added_interpolated_points.json` (interpolated routes) | `pilot_briefing.txt` (pilot briefing)<br>`temp/routes_with_added_interpolated_points.json` (updated with schedule metadata) |
| **generate_animation.py** | `temp/routes_with_added_interpolated_points.json` (single source of truth) | `animation/animation_data.json` (complete animation data)<br>`animation/conflict_points.json` (conflict locations) |
| **audit_conflict.py** | `temp/potential_conflict_data.json` (conflict generation)<br>`temp/routes_with_added_interpolated_points.json` (interpolated routes)<br>`animation/animation_data.json` (animation data) | `audit_conflict_output.txt` (data integrity audit report) |
| **animation/validate_animation_data.py** | `animation/animation_data.json` (animation data) | Console output (validation results) |

### 1. Data Extraction Layer
**File**: `extract_simbrief_xml_flightplan.py`

**Responsibilities**:
- Parse SimBrief XML flight plan files
- Extract waypoints, coordinates, altitudes, and timing
- Convert to structured data formats (JSON/KML)
- Handle XML parsing errors gracefully

**Key Classes**:
- `FlightPlan`: Represents a complete flight plan with origin, destination, and waypoints
- `Waypoint`: Individual navigation points with coordinates, altitude, and timing

**Outputs**:
- Individual KML files for each flight plan
- JSON data files for structured analysis
- 40-colour visualisation scheme for route identification

### 2. Conflict Generation Engine
**File**: `find_potential_conflicts.py`

**Responsibilities**:
- Perform 3D spatial conflict detection
- Analyse both waypoint and enroute conflicts
- Optimise departure times for maximum conflicts
- Generate comprehensive conflict scenarios for events
- **Identify and track only first conflicts between aircraft pairs**
- **Create the single source of truth foundation with interpolated routes**

**Core Algorithms**:
- **Distance Calculation**: Haversine formula for lateral separation
- **Route Interpolation**: Configurable spacing (default 2nm) between waypoints
- **Phase Detection**: TOC/TOD-based climb/cruise/descent determination
- **Conflict Filtering**: Altitude thresholds and duplicate detection
- **First Conflict Detection**: Tracks earliest conflict between each aircraft pair

**Conflict Criteria**:
- Lateral separation < 3 nautical miles
- Vertical separation < 900 feet
- Aircraft altitude > 2500 feet
- Duplicate filtering within 4 NM
- **First conflict only**: Only the earliest conflict between aircraft pairs is reported

### 3. Scheduling & Briefing
**File**: `generate_schedule_conflicts.py`

**Responsibilities**:
- Read potential_conflict_data.json
- **Load conflict generation departure times** and respect intended scheduling
- **Sort flights by intended departure time** (earliest first)
- **Schedule flights at their intended times** instead of forcing "most conflicts" flight to depart first
- Add departure schedule metadata to interpolated points file
- Output pilot_briefing.txt (authoritative, includes schedule and conflicts)
- Use interpolated points directly for position interpolation (no circular dependency)

**Key Changes**:
- **Fixed scheduling algorithm**: Now uses conflict generation departure times instead of "most conflicts" rule
- **Eliminated circular dependency**: No longer depends on animation_data.json
- **Metadata approach**: Adds departure schedule to `temp/routes_with_added_interpolated_points.json`
- **Direct interpolation**: Uses interpolated points file for conflict position calculations

**Previous Issue**:
The original algorithm incorrectly prioritized flights with "most conflicts" and forced them to depart at event start time, ignoring the intended departure times from conflict generation.

**Current Fix**:
- **YMES-YSRI**: 14:00 (as intended)
- **YSSY-YSWG**: 14:16 (as intended) - previously was incorrectly 14:00
- **YSNW-YWLM**: 14:20 (as intended)

**Outputs**:
- pilot_briefing.txt (single source of truth for schedule and conflicts)
- Updated `temp/routes_with_added_interpolated_points.json` with departure metadata

### 4. Animation Data Export Layer
**File**: `generate_animation.py`

**Responsibilities**:
- Generate all analysis and schedule data into animation-ready JSON for web visualization
- **Read departure times from interpolated points metadata (not pilot_briefing.txt)**
- **Use only the single source of truth - no XML file dependencies**
- Output: `animation_data.json`, `conflict_points.json`

**Key Changes**:
- **Removed x/y fields**: No longer generates projected coordinates
- **Metadata-based schedule loading**: Reads from interpolated points file
- **Simplified data structure**: Only essential lat/lon/altitude/time fields
- **Eliminated XML dependency**: Now uses only the single source of truth

### 5. Visualization Layer
**Files**: `merge_kml_flightplans.py`, `animation/animation.html`

**Responsibilities**:
- Merge KML files for Google Earth
- Provide interactive 3D web visualization (CesiumJS)
- Animate aircraft with real-time altitude labels, conflict points, and alerts
- Timeline controls and camera auto-zoom
- Dynamic data loading from JSON (no server required)
- **Dynamic camera positioning**: Automatically calculates optimal view to cover 90% of origin and destination airports globally

**Dynamic Camera Positioning**:
- **Global Coverage**: Works for any flight routes worldwide, not limited to specific regions
- **Automatic Calculation**: Analyses all departure and arrival airports from flight data
- **90% Coverage**: Ensures airports are well within the view with 10% padding
- **Adaptive Zoom**: Automatically adjusts zoom level based on airport distances
- **Minimum View Size**: Prevents excessive zoom for very close airports
- **Fallback Support**: Uses default view if coordinates aren't available
- **Console Logging**: Shows covered airports and view coordinates for debugging

**Camera Algorithm**:
1. Collects all unique departure and arrival airports from flights
2. Extracts coordinates from first waypoint (departure) and last waypoint (arrival)
3. Calculates minimum/maximum longitude/latitude bounds
4. Adds 10% padding for 90% coverage
5. Ensures minimum view size (0.1° longitude/latitude)
6. Sets camera view to cover all airports with appropriate zoom level

### 6. Data Audit Layer
**File**: `audit_conflict.py`

### 7. Web Interface Layer
**Directory**: `web/`

**Responsibilities**:
- Provide browser-based interface for file upload and processing
- Handle XML file validation and duplicate route detection
- Manage processing workflow and progress tracking
- Serve animation files and pilot briefing
- **Frontend-Backend Dependency**: Frontend relies on backend for XML validation

**Key Components**:
- **Flask Backend** (`app.py`): REST API endpoints for file management and processing
- **HTML/CSS/JavaScript Frontend**: Modern responsive interface
- **File Manager** (`fileManager.js`): Handles uploads, validation, and file selection
- **Processor** (`processor.js`): Manages workflow execution and progress
- **Map Viewer** (`mapViewer.js`): 3D visualization integration

**Frontend-Backend Validation Architecture**:
- **Backend XML Parsing**: Uses `extract_simbrief_xml_flightplan.py` for consistent validation
- **Route Duplicate Detection**: Backend checks for same origin-destination pairs across files
- **Frontend Dependencies**: Frontend cannot parse XML independently due to browser limitations
- **Validation Flow**: Frontend → Backend API → XML parsing → Route analysis → Frontend display
- **Error Handling**: Comprehensive edge case handling for network issues, file validation, and processing timeouts

**Validation Endpoints**:
- `/validate-same-routes` (POST): Checks for duplicate origin-destination pairs
- `/validate/<filename>` (GET): Validates individual XML file structure
- `/files` (GET): Lists uploaded files with metadata
- `/process` (POST): Executes the complete analysis workflow

**User Experience Features**:
- **Visual Indicators**: Duplicate routes highlighted in file list
- **Warning Dialogs**: Detailed explanations of system limitations
- **Progress Tracking**: Real-time processing status updates
- **Error Recovery**: Automatic retry logic and graceful failure handling