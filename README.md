# ATC Conflict Analysis System

A Python-based system for generating chaotic, conflicting SimBrief XML flight plans to create challenging air traffic control (ATC) event scenarios. The system is designed to help the events team create situations where controllers are challenged and pilots can enjoy fun, dynamic events.

**Recent Improvements:**
- ✅ **Fixed scheduling algorithm** - Now respects conflict analysis departure times instead of "most conflicts" rule
- ✅ **Corrected departure timing** - YSSY-YSWG now departs at 14:16 instead of 14:00 as intended
- ✅ **Enhanced audit system** - Added departure time column to track scheduling accuracy
- ✅ **Eliminated circular dependency** between scheduling and animation
- ✅ **Metadata-based approach** for departure schedule sharing
- ✅ **Removed x/y projected coordinates** from animation data
- ✅ **Linear data flow** with clear dependencies
- ✅ **Simplified data structures** for better performance

## Purpose

This system enables event organizers to:
- **Parse SimBrief XML flight plans** and analyze multiple routes
- **Intentionally generate and identify conflicts** between aircraft to maximize ATC workload and event excitement
- **Focus on "First Conflicts"** - the initial point where two aircraft first meet conflict criteria, representing the moment ATC first needs to intervene
- **Provide detailed conflict analysis** with location, timing, and phase information
- **Detect conflicts both at waypoints and between waypoints** for comprehensive event realism
- **Generate KML files** for Google Earth visualization with diverse color schemes
- **Schedule departures accurately** based on conflict analysis results

## Quick Start

### Prerequisites
- Python 3.6+
- SimBrief XML flight plan files

### Master Workflow (Recommended)
The easiest way to run the complete analysis is using the master script:

```bash
# Run complete workflow (extract → analyze → report → merge → schedule → frontend)
python execute.py

# Run with custom schedule times
python execute.py --start-time 14:00 --end-time 18:00
```

### Basic Workflow
```bash
# Option 1: Run complete workflow with master script
python execute.py

# Option 2: Run individual steps
# 1. Place SimBrief XML files in the project directory
# 2. Extract flight plan data and generate KML files
python extract_simbrief_xml_flightplan.py

# 3. Run conflict analysis on all XML files
python find_potential_conflicts.py

# 4. Generate readable conflict report
python conflicts_list.py

# 5. Merge KML files for Google Earth viewing
python merge_kml_flightplans.py

# 6. Generate event schedule and pilot briefing (with metadata)
python generate_schedule_conflicts.py --start 14:00 --end 18:00

# 7. Generate animation data for web visualization (simplified structure)
python generate_animation.py

# 8. Open the visualization
Open animation/cesium_flight_anim.html in your browser

# 9. Run data integrity audit (optional)
python audit_conflict.py  # Generates audit_conflict_output.txt with raw data comparison
```

### Expected Output
- `temp/potential_conflict_data.json` - Detailed conflict data
- `conflict_list.txt` - Formatted conflict list (first conflicts only)
- `merged_flightplans.kml` - Combined KML file for Google Earth
- Individual KML files in `temp/` directory
- `pilot_briefing.txt` - Pilot conflict briefing (authoritative, includes all departure times and conflict details)
- `temp/routes_with_added_interpolated_points.json` - Interpolated points with departure metadata
- `animation/animation_data.json` - Animation data for Cesium (simplified structure, no x/y fields)
- `animation/flight_tracks.json` - Flight path data
- `animation/conflict_points.json` - Conflict location/timing (filtered by altitude)
- `animation/cesium_flight_anim.html` - 3D web visualization
- `audit_conflict_output.txt` - **Raw data audit report** (Markdown tables showing exact values across all data sources)

## System Architecture

### Linear Data Flow (No Circular Dependencies)
```
Conflict Analysis → Scheduling → Animation Generation
       ↓              ↓              ↓
potential_conflict_data.json → routes_with_metadata.json → animation_data.json
```

### Key Improvements
- **Fixed scheduling algorithm** - Now uses conflict analysis departure times instead of "most conflicts" rule
- **Eliminated circular dependency** between scheduling and animation
- **Metadata-based approach** for departure schedule sharing
- **Simplified data structures** (removed x/y projected coordinates)
- **Linear processing** with clear dependencies

## Scheduling Algorithm

### Previous Issue
The original scheduling algorithm incorrectly prioritized flights with "most conflicts" and forced them to depart at event start time, ignoring the intended departure times from conflict analysis.

### Current Fix
The scheduling algorithm now:
1. **Loads conflict analysis data** to get intended departure times
2. **Sorts flights by intended departure time** (earliest first)
3. **Schedules flights at their intended times** instead of forcing the "most conflicts" flight to depart first
4. **Respects conflict analysis results** (e.g., YSSY-YSWG at 14:16)

### Example Results
- **YMES-YSRI**: 14:00 (as intended)
- **YSSY-YSWG**: 14:16 (as intended) - previously was incorrectly 14:00
- **YSNW-YWLM**: 14:20 (as intended)

## Conflict Detection Features

### Detection Methods
- **At Waypoints**: Detects conflicts when aircraft are at the same named waypoint
- **Between Waypoints**: Detects conflicts when routes cross at interpolated points along route segments
- **3D Analysis**: Considers lateral distance, vertical separation, and timing
- **Phase Detection**: Automatically determines climb, cruise, or descent phases based on TOC/TOD

### Conflict Criteria
- **Lateral Separation**: < 3 nautical miles
- **Vertical Separation**: < 900 feet
- **Altitude Threshold**: Aircraft must be above 5000 ft
- **Route Interpolation**: Configurable spacing (default 2nm) between waypoints for enroute conflicts
- **Duplicate Filtering**: Ignores conflicts within 4 NM of previous conflicts between same routes

### First Conflict Concept
The system focuses on **"First Conflicts"** - the initial point where two aircraft first meet conflict criteria during their flights. This is critical for event planning because:

- **ATC Intervention Point**: Represents the moment when controllers first need to intervene between aircraft pairs
- **Event Planning**: Helps organizers understand when conflicts will first occur
- **Resource Allocation**: Enables better planning of ATC resources and timing
- **Realistic Scenarios**: Focuses on the most critical conflict moment rather than tracking every subsequent conflict

### Output Formats
- **Detailed First Conflict List**: Shows only the first conflict between each aircraft pair with location, altitudes, times, and phases
- **JSON Export**: Structured data for further analysis (stored in temp directory)
- **KML Visualization**: Google Earth compatible files with 40 diverse colors
- **Smart Location Format**: Shows conflicts between waypoints as "X NM [direction] of [waypoint]"

## System Components

### Core Analysis
- `execute.py` - Master workflow script (runs complete analysis pipeline)
- `find_potential_conflicts.py` - Main analysis engine (focuses on first conflicts)
- `conflicts_list.py` - Conflict listing and reporting
- `conflict_list.txt` - Formatted conflict output (first conflicts only)

### Data Processing
- `extract_simbrief_xml_flightplan.py` - Converts SimBrief XML to KML for visualization
- `merge_kml_flightplans.py` - Merges individual KML files into a single file
- `generate_schedule_conflicts.py` - Generates event schedule and adds metadata to interpolated points (FIXED: now respects conflict analysis departure times)
- `generate_animation.py` - Generates animation data for web visualization (simplified structure)
- `audit_conflict.py` - **Raw data integrity audit** across all processing stages (shows exact values with NO CONVERSIONS, includes departure time column)

### Data Organization
- `temp/` - Directory containing all generated data files
  - Individual KML files for each flight plan
  - Individual JSON data files for each flight plan
  - `potential_conflict_data.json` - Main analysis results
  - `routes_with_added_interpolated_points.json` - Interpolated points with departure metadata

### Visualization
- `merged_flightplans.kml` - Combined KML file for Google Earth viewing
- `animation/cesium_flight_anim.html` - 3D animated web visualization (CesiumJS)
- 40 diverse colors for easy route identification

## Web Visualization Features
- 3D animated aircraft with scalable icons
- Real-time altitude labels (below aircraft)
- Conflict points and live alerts
- Timeline controls, camera auto-zoom
- Toggleable flight labels
- Loads data from JSON (no server required)
- **Simplified data structure** (lat/lon/altitude only, no x/y fields)

## Data Structure Changes

### Animation Data (Simplified)
```json
{
  "metadata": { ... },
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
  ]
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

## Audit System

### Enhanced Audit Report
The audit system now includes a **departure time column** to track scheduling accuracy:

```
Columns: Source | Flight | Departure Time | Time (UTC) | Lat | Lon | Alt | Altitude Diff | Distance
```

This allows verification that:
- **Scheduling algorithm** correctly uses conflict analysis departure times
- **Animation data** reflects the correct scheduled times
- **All data sources** are consistent across the workflow

### Data Sources Tracked
1. **potential_conflict_data.json** - Raw conflict analysis results
2. **interpolated_points** - Backend processed data with metadata
3. **animation_data.json** - Frontend visualization data

## Conflict Types

### At Waypoints
- **Location**: Shows waypoint names (e.g., "YORG/VIRUR")
- **Conflict Type**: "at waypoint"
- **Phase**: Actual flight phase (climb, cruise, descent)

### Between Waypoints
- **Location**: Shows distance and direction from nearest waypoint (e.g., "2.1 NM NE of YBDG")
- **Conflict Type**: "between waypoints"
- **Phase**: Determined by position relative to TOC/TOD (climb, cruise, descent)
- **Segments**: Shows route segments involved

## Technical Details

### Flight Plan Structure
The system parses SimBrief XML files containing:
```xml
<flightplan>
  <waypoint>
    <name>YMAY</name>
    <lat>-36.0678</lat>
    <lon>146.9581</lon>
    <altitude>3000</altitude>
    <time_total>3000</time_total> <!-- seconds -->
    <stage>CRZ</stage>
  </waypoint>
</flightplan>
```

### Phase Determination
- **Climb**: Before TOC (Top of Climb) waypoint
- **Cruise**: Between TOC and TOD (Top of Descent) waypoints
- **Descent**: After TOD waypoint

### Conflict Calculation
1. **Distance**: Haversine formula for lateral separation
2. **Altitude**: Absolute difference between aircraft altitudes
3. **Time**: Converted from seconds to minutes for analysis
4. **Interpolation**: Configurable spacing (default 2nm) between waypoints
5. **Nearest Waypoint**: Calculates distance/direction from closest waypoint on either route
6. **First Conflict Detection**: Tracks only the earliest conflict between each aircraft pair

### Filtering Logic
- **Low Altitude**: Aircraft ≤ 5000 ft excluded
- **Duplicate Conflicts**: Conflicts within 4 NM of previous conflicts between same routes ignored
- **Invalid Data**: Malformed XML entries skipped
- **First Conflict Only**: Only the earliest conflict between aircraft pairs is reported

### Color Scheme
The system uses 40 diverse colors for route visualization:
- **Primary colors**: Red, Green, Blue, Magenta, Cyan, Yellow
- **Pastel variants**: Light Blue, Pink, Lime Green, Light Red
- **Bright variants**: Bright Green, Bright Red, Bright Lime, Bright Pink
- **Metallic tones**: Gold, Amber, Lavender, Violet, Aqua, Rose, Orchid
- **Light variants**: Light Gold, Light Lavender, Light Mint, Light Salmon, Light Plum

## Example Output

```
First Conflicts Found:
==================================================

Total First Conflicts: 1

1. YMCO-YMAY & YMEN-YMAY
   Location: YMAY/YMAY
   Conflict Type: at waypoint
   Distance: 0.0 NM
   Altitudes: 3000/3000 ft
   Altitude Diff: 0 ft
   Arrival Times: 73.9 vs 99.3 min
   Phase: descent/descent

2. YMER-YMML & YMMB-YSWG
   Location: 2.4 NM NE of BOYSE
   Conflict Type: between waypoints
   Distance: 0.9 NM
   Altitudes: 19880/19000 ft
   Altitude Diff: 880 ft
   Arrival Times: 54.5 vs 12.1 min
   Phase: descent/cruise
```

## Event Scenario Applications

This system is designed for event scenario creation, enabling the events team to:

### Scenario Creation
- **Maximize First Conflict Density**: Generate as many initial conflicts as possible in a given airspace
- **Create Chaotic Situations**: Overlap routes and phases to challenge controllers
- **Increase Realism and Workload**: Simulate high-traffic, high-stress environments for live events
- **Deliver Fun and Dynamic Events**: Provide pilots with engaging and unpredictable flying experiences
- **Focus on Critical Moments**: Identify when ATC first needs to intervene between aircraft pairs

### Event Execution
- **Readable Output**: Clear first conflict descriptions for event planning and briefings
- **Visual Analysis**: Google Earth integration for spatial understanding
- **Structured Data**: JSON format for further analysis and integration

## Advanced Usage

### Custom Analysis
```bash
# Run individual components
python extract_simbrief_xml_flightplan.py  # Extract data only
python find_potential_conflicts.py        # Analyze first conflicts only
python merge_kml_flightplans.py              # Merge KML files only
python generate_animation.py              # Export web visualization data only
```

### Recent Improvements Summary
- **Circular Dependency Elimination**: Linear data flow from analysis to visualization
- **Metadata-Based Approach**: Departure schedule shared via interpolated points metadata
- **Data Structure Simplification**: Removed x/y projected coordinates from animation data
- **Performance Optimization**: Reduced file sizes and processing overhead
- **Audit Enhancement**: Time values rounded to zero decimal places for cleaner output