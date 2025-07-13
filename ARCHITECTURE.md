# ATC Conflict Analysis System - Architecture Document

## System Overview

The ATC Conflict Analysis System is a Python-based application designed to analyze SimBrief XML flight plans and identify potential air traffic conflicts for event scenario creation. The system helps the events team build challenging events for controllers and fun, dynamic events for pilots. It processes multiple flight plans simultaneously, detects conflicts using 3D spatial analysis, and generates both detailed reports and visual outputs.

**Key Concept: First Conflicts**
The system focuses on identifying "first conflicts" - the initial point where two aircraft first meet conflict criteria during their flights. This is critical for event planning as it represents the moment when ATC first needs to intervene between aircraft pairs, rather than tracking every subsequent conflict between the same aircraft.

## Architecture Principles

- **Modular Design**: Clear separation between data extraction, analysis, reporting, and visualization
- **Single Responsibility**: Each component has a focused purpose
- **Data-Driven**: JSON-based data exchange between components
- **Visualization-First**: KML output for Google Earth integration
- **Event-Focused**: Optimized for event scenario workflows
- **First Conflict Priority**: Tracks only the initial conflict between aircraft pairs for ATC intervention planning
- **Linear Data Flow**: Eliminated circular dependencies through metadata-based approach
- **Accurate Scheduling**: Respects conflict analysis departure times instead of "most conflicts" rule

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
- Output: `animation_data.json`, `flight_tracks.json`, `conflict_points.json`

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

**Responsibilities**:
- Perform raw data integrity audit across all processing stages
- Compare conflict data between three sources:
  - `potential_conflict_data.json` (conflict detection output)
  - `routes_with_added_interpolated_points.json` (backend processed data)
  - `animation_data.json` (frontend visualization data)
- Generate readable Markdown tables showing exact data values
- **IMPORTANT**: Shows RAW DATA ONLY with NO CONVERSIONS for true audit integrity
- **Rounds time values to zero decimal places for cleaner output**
- **Enhanced with departure time column** to track scheduling accuracy

**Outputs**:
- `audit_conflict_output.txt` - Markdown-formatted audit report
- Displays all values exactly as stored in source files
- Groups conflicts by flight for easy comparison
- **New departure time column** for scheduling verification

## Data Flow

**Updated Linear Flow (No Circular Dependencies):**

1. **SimBrief XML** → Extraction → `potential_conflict_data.json`
2. **potential_conflict_data.json** → Scheduling → `temp/routes_with_added_interpolated_points.json` (with metadata)
3. **Interpolated points with metadata** → Animation Generation → `animation_data.json`
4. **All Data Sources** → Audit → `audit_conflict_output.txt` (raw data verification)

**Key Improvements:**
- **Fixed scheduling algorithm** - Now respects conflict analysis departure times
- **Eliminated circular dependency** between scheduling and animation
- **Metadata-based approach** for departure schedule sharing
- **Linear data flow** from analysis to visualization
- **Enhanced audit system** with departure time tracking

## Data Models

### FlightPlan
```python
class FlightPlan:
    origin: str           # ICAO airport code
    destination: str      # ICAO airport code
    route: str           # Route string
    waypoints: List[Waypoint]
    departure: Waypoint
    arrival: Waypoint
```

### Waypoint
```python
class Waypoint:
    name: str            # Waypoint identifier
    lat: float          # Latitude
    lon: float          # Longitude
    altitude: int       # Altitude in feet
    time_total: int     # Elapsed time in seconds
    stage: str          # CLB/CRZ/DES
    waypoint_type: str  # vor/ndb/wpt/airport
```

### Conflict
```python
{
    'flight1': str,           # Route identifier
    'flight2': str,           # Route identifier
    'lat1/lon1': float,       # Conflict coordinates
    'lat2/lon2': float,       # Conflict coordinates
    'alt1/alt2': int,         # Aircraft altitudes
    'distance': float,         # Lateral separation (NM)
    'altitude_diff': int,      # Vertical separation (ft)
    'time1/time2': float,     # Arrival times (minutes)
    'stage1/stage2': str,     # Flight phases
    'conflict_type': str,      # 'at waypoint' or 'between waypoints'
    'is_waypoint': bool,      # True for waypoint conflicts
    'time': float             # Earliest conflict time (for first conflict detection)
}
```

### Animation Data (animation_data.json) - Updated Structure
```json
{
  "metadata": {
    "total_flights": 3,
    "total_conflicts": 2,
    "event_duration": 5,
    "export_time": "2025-07-13T20:40:08.358541"
  },
  "flights": [
    {
      "flight_id": "YBDG-YSBK",
      "departure": "YBDG",
      "arrival": "YSBK",
      "departure_time": "1400",
      "waypoints": [
        {
          "index": 0,
          "name": "YBDG",
          "lat": -37.123456,
          "lon": 147.123456,
          "altitude": 23,
          "UTC time": "1400",
          "stage": ""
        }
      ]
    }
  ],
  "conflicts": [...],
  "timeline": [...]
}
```

**Key Changes:**
- **Removed x/y fields**: No longer includes projected coordinates
- **Simplified structure**: Only essential geographic and timing data
- **UTC time format**: Consistent HHMM string format for animation

### Interpolated Points with Metadata
```json
{
  "YBDG-YSBK": [...],
  "YSSY-YSWG": [...],
  "_metadata": {
    "departure_schedule": {
      "YBDG-YSBK": {
        "departure_time": "1400",
        "conflicts": 2
      }
    },
    "event_start": "1400",
    "event_end": "1800",
    "total_flights": 3,
    "total_conflicts": 4
  }
}
```

## Key Technical Decisions

### 1. XML Parsing Strategy
- **Choice**: `xml.etree.ElementTree` (standard library)
- **Rationale**: No external dependencies, sufficient for SimBrief XML structure
- **Error Handling**: Graceful degradation with detailed error messages

### 2. Spatial Analysis
- **Distance Calculation**: Haversine formula for accurate nautical mile calculations
- **Interpolation**: Configurable spacing (default 2nm) for enroute conflict detection
- **Coordinate System**: WGS84 lat/lon with nautical mile distances

### 3. Scheduling Algorithm
- **Previous Approach**: Prioritized flights with "most conflicts" and forced them to depart at event start time
- **Current Approach**: Respects conflict analysis departure times and schedules flights in chronological order
- **Rationale**: Ensures accurate departure timing based on conflict analysis results rather than arbitrary "most conflicts" rule 