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
- Read conflict_analysis.json
- Assign departure times to maximize/synchronize conflicts
- Output pilot_briefing.txt (authoritative, includes schedule and conflicts)

**Outputs**:
- pilot_briefing.txt (single source of truth for schedule and conflicts)

### 4. Animation Data Export Layer
**File**: `generate_animation.py`

**Responsibilities**:
- Generate all analysis and schedule data into animation-ready JSON for web visualization
- Output: `animation_data.json`, `flight_tracks.json`, `conflict_points.json`

### 5. Visualization Layer
**Files**: `merge_kml_flightplans.py`, `web_visualization/cesium_flight_anim.html`

**Responsibilities**:
- Merge KML files for Google Earth
- Provide interactive 3D web visualization (CesiumJS)
- Animate aircraft with real-time altitude labels, conflict points, and alerts
- Timeline controls and camera auto-zoom
- Dynamic data loading from JSON (no server required)

## Data Flow

1. SimBrief XML → Extraction → conflict_analysis.json
2. conflict_analysis.json → Scheduling → pilot_briefing.txt
3. pilot_briefing.txt → Animation Generation → animation_data.json

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

### Animation Data (animation_data.json)
```json
{
  "metadata": { ... },
  "flights": [
    {
      "flight_id": "YBDG-YSBK",
      "departure_time": "14:00",
      "waypoints": [ { "lat": ..., "lon": ..., "altitude": ..., "time_from_departure": ... }, ... ]
    }, ...
  ],
  "conflicts": [ ... ],
  "timeline": [ ... ]
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

### 3. Data Persistence
- **Format**: JSON for structured data, KML for visualization
- **Organization**: `temp/` directory for generated files
- **Naming**: Consistent with original XML filenames

### 4. Conflict Detection Algorithm
- **Two-Phase Approach**: Waypoint conflicts + interpolated enroute conflicts
- **Filtering**: Altitude thresholds and duplicate detection
- **Optimization**: Departure time optimization for event scenarios
- **First Conflict Focus**: Only tracks the earliest conflict between aircraft pairs

### 5. Visualization Strategy
- **Platform**: Google Earth via KML format
- **Color Scheme**: 40 diverse colors for route identification
- **Organization**: Hierarchical folder structure in merged KML

## Performance Characteristics

- **Scalability**: Linear complexity with number of flight plans
- **Memory Usage**: Moderate - stores flight plan objects in memory
- **Processing Time**: Fast for typical scenarios (< 100 flight plans)
- **Output Size**: KML files scale with number of waypoints

## Error Handling

- **XML Parsing**: Graceful handling of malformed XML
- **Missing Data**: Default values for optional fields
- **File I/O**: Clear error messages for missing files
- **Spatial Calculations**: Validation of coordinate data

## Future Enhancements

1. **Real-time Processing**: WebSocket integration for live flight data
2. **Advanced Algorithms**: Machine learning for conflict prediction
3. **Database Integration**: Persistent storage for historical analysis
4. **API Layer**: RESTful interface for external integrations
5. **Enhanced Visualization**: 3D rendering and animation capabilities

## Dependencies

- **Python 3.6+**: Core runtime
- **Standard Library**: xml.etree.ElementTree, json, os, math
- **No External Dependencies**: Self-contained for easy deployment

## Deployment

The system is designed for local deployment with minimal setup:
1. Place SimBrief XML files in project directory
2. Run extraction script: `python extract_simbrief_xml_flightplan.py`
3. Run analysis script: `python find_potential_conflicts.py`
4. Generate schedule: `python generate_schedule_conflicts.py --start 14:00 --end 18:00`
5. Merge visualization: `python merge_kml_flightplans.py`

This architecture provides a robust foundation for ATC conflict analysis while maintaining simplicity and ease of use for event scenario creation and execution. 