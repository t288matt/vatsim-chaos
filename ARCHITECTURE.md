# ATC Conflict Analysis System - Architecture Document

## System Overview

The ATC Conflict Analysis System is a Python-based application designed to analyze SimBrief XML flight plans and identify potential air traffic conflicts for event scenario creation. The system helps the events team build challenging events for controllers and fun, dynamic events for pilots. It processes multiple flight plans simultaneously, detects conflicts using 3D spatial analysis, and generates both detailed reports and visual outputs.

**Key Concept: First Conflicts**
The system focuses on identifying "first conflicts" - the initial point where two aircraft first meet conflict criteria during their flights. This is critical for event planning as it represents the moment when ATC first needs to intervene between aircraft pairs, rather than tracking every subsequent conflict between the same aircraft.

**Flight ID System**
The system now uses unique flight IDs (FLT0001, FLT0002, etc.) instead of origin-destination pairs for better conflict tracking and separation enforcement. Each flight gets a sequential flight ID during XML processing, which is maintained throughout the entire workflow.

**Separation Rules**
The system enforces two key separation rules:
1. **Departure Separation**: Minimum 2 minutes between departures from the same airport
2. **Same Route Separation**: Minimum 5 minutes between flights with identical origin-destination

## Architecture Principles

- **Modular Design**: Clear separation between data extraction, analysis, reporting, and visualization
- **Single Responsibility**: Each component has a focused purpose
- **Data-Driven**: JSON-based data exchange between components
- **Visualization-First**: KML output for Google Earth integration
- **Event-Focused**: Optimized for event scenario workflows
- **First Conflict Priority**: Tracks only the initial conflict between aircraft pairs for ATC intervention planning
- **Linear Data Flow**: Eliminated circular dependencies through metadata-based approach
- **Accurate Scheduling**: Respects conflict analysis departure times instead of "most conflicts" rule
- **Flight ID Tracking**: Uses unique flight IDs for better conflict tracking and separation enforcement

## System Components

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
- 40-color visualization scheme for route identification

### 2. Conflict Analysis Engine
**File**: `find_potential_conflicts.py`

**Responsibilities**:
- Perform 3D spatial conflict detection
- Analyze both waypoint and enroute conflicts
- Optimize departure times for maximum conflicts
- Generate comprehensive conflict scenarios for events
- **Identify and track only first conflicts between aircraft pairs**

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
- **Load conflict analysis departure times** and respect intended scheduling
- **Sort flights by intended departure time** (earliest first)
- **Schedule flights at their intended times** instead of forcing "most conflicts" flight to depart first
- Add departure schedule metadata to interpolated points file
- Output pilot_briefing.txt (authoritative, includes schedule and conflicts)
- Use interpolated points directly for position interpolation (no circular dependency)

**Key Changes**:
- **Fixed scheduling algorithm**: Now uses conflict analysis departure times instead of "most conflicts" rule
- **Eliminated circular dependency**: No longer depends on animation_data.json
- **Metadata approach**: Adds departure schedule to `temp/routes_with_added_interpolated_points.json`
- **Direct interpolation**: Uses interpolated points file for conflict position calculations

**Previous Issue**:
The original algorithm incorrectly prioritized flights with "most conflicts" and forced them to depart at event start time, ignoring the intended departure times from conflict analysis.

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
- Output: `animation_data.json`, `conflict_points.json`

**Key Changes**:
- **Removed x/y fields**: No longer generates projected coordinates
- **Metadata-based schedule loading**: Reads from interpolated points file
- **Simplified data structure**: Only essential lat/lon/altitude/time fields

### 5. Visualization Layer
**Files**: `merge_kml_flightplans.py`, `animation/cesium_flight_anim.html`

**Responsibilities**:
- Merge KML files for Google Earth
- Provide interactive 3D web visualization (CesiumJS)
- Animate aircraft with real-time altitude labels, conflict points, and alerts
- Timeline controls and camera auto-zoom
- Dynamic data loading from JSON (no server required)

### 6. Data Audit Layer
**File**: `audit_conflict.py`