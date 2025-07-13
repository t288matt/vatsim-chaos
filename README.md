# ATC Conflict Analysis System

A Python-based system for generating chaotic, conflicting SimBrief XML flight plans to create challenging air traffic control (ATC) event scenarios. The system is designed to help the events team create situations where controllers are challenged and pilots can enjoy fun, dynamic events.

## Purpose

This system enables event organizers to:
- **Parse SimBrief XML flight plans** and analyze multiple routes
- **Intentionally generate and identify conflicts** between aircraft to maximize ATC workload and event excitement
- **Focus on "First Conflicts"** - the initial point where two aircraft first meet conflict criteria, representing the moment ATC first needs to intervene
- **Provide detailed conflict analysis** with location, timing, and phase information
- **Detect conflicts both at waypoints and between waypoints** for comprehensive event realism
- **Generate KML files** for Google Earth visualization with diverse color schemes

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
python execute.py --start 14:00 --end 18:00
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

# 6. Generate event schedule and pilot briefing (single output)
python generate_schedule_conflicts.py --start 14:00 --end 18:00

# 7. Generate animation data for web visualization
python generate_animation.py

# 8. Open the visualization
Open animation/cesium_flight_anim.html in your browser
```

### Expected Output
- `temp/potential_conflict_data.json` - Detailed conflict data
- `conflict_list.txt` - Formatted conflict list (first conflicts only)
- `merged_flightplans.kml` - Combined KML file for Google Earth
- Individual KML files in `temp/` directory
- `pilot_briefing.txt` - Pilot conflict briefing (authoritative, includes all departure times and conflict details)
- `animation/animation_data.json` - Animation data for Cesium (filtered by altitude)
- `animation/flight_tracks.json` - Flight path data
- `animation/conflict_points.json` - Conflict location/timing (filtered by altitude)
- `animation/cesium_flight_anim.html` - 3D web visualization

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
- `generate_schedule_conflicts.py` - Generates event schedule for conflicts
- `generate_animation.py` - Generates animation data for web visualization (filters conflicts by altitude threshold)

### Data Organization
- `temp/` - Directory containing all generated data files
  - Individual KML files for each flight plan
  - Individual JSON data files for each flight plan
  - `potential_conflict_data.json` - Main analysis results

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