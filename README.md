# ATC Conflict Generation System

A Python-based system for generating chaotic, conflicting SimBrief XML flight plans to create challenging air traffic control (ATC) event scenarios. The system is designed to help the events team create situations where controllers are challenged and pilots can enjoy fun, dynamic events.

**Recent Improvements:**
- ✅ **Flight ID System** - Each flight gets a unique ID (FLT0001, FLT0002, etc.) for better tracking
- ✅ **Enhanced Separation Rules** - 5-minute minimum separation for flights with same origin-destination
- ✅ **Fixed scheduling algorithm** - Now respects conflict analysis departure times instead of "most conflicts" rule
- ✅ **Corrected departure timing** - YSSY-YSWG now departs at 14:16 instead of 14:00 as intended
- ✅ **Enhanced audit system** - Added departure time column to track scheduling accuracy
- ✅ **Eliminated circular dependency** between scheduling and animation
- ✅ **Metadata-based approach** for departure schedule sharing
- ✅ **Removed x/y projected coordinates** from animation data
- ✅ **Linear data flow** with clear dependencies
- ✅ **Simplified data structures** for better performance
- ✅ **Single Source of Truth** - One comprehensive JSON file contains all flight data, conflicts, and scheduling
- ✅ **VATSIM Radar-style UI** - Modern dark theme with glass morphism effects and professional ATC styling
- ✅ **Frontend Time Controls** - Event time parameters moved from backend to frontend for better user control
- ✅ **File Management Enhancements** - Added file deletion functionality with trash can icons
- ✅ **Animation Time Fix** - Fixed event start/end times not being passed through to animation display
- ✅ **Pilot Briefing Fix** - Fixed white text on white background issue in briefing modal
- ✅ **Process Button State** - Button remains disabled until files are selected
- ✅ **UI Text Updates** - Changed "Process Analysis" to "Generate Schedule" and "Analysis Time Window" to "Event Time"
- ✅ **Default Time Updates** - Changed default event time from 10:00-18:00 to 08:00-11:00
- ✅ **Upload Area Optimization** - Reduced upload box height for better space utilization

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

## Flight ID System

The system now uses unique flight IDs (FLT0001, FLT0002, etc.) instead of origin-destination pairs for better conflict tracking and separation enforcement:

- **Unique Identification**: Each flight gets a sequential flight ID during XML processing
- **Route Preservation**: Origin-destination information is maintained alongside flight IDs
- **Separation Rules**: Both flight IDs and routes are used for separation enforcement
- **Conflict Tracking**: Enables tracking of "first conflicts" between unique aircraft pairs
- **Same Route Handling**: Flights with identical origin-destination are treated as separate flights with 5-minute minimum separation

## Altitude Handling

The system uses a consistent altitude approach across backend and frontend:

- **Backend Processing**: All altitudes are stored and processed in feet (e.g., 2000ft, 36000ft)
- **Frontend Display**: Altitudes are displayed using the transition altitude from `env.py` (TRANSITION_ALTITUDE_FT = 10500)
  - Below transition altitude: Displayed in feet (e.g., "8500ft")
  - At or above transition altitude: Displayed as flight levels (e.g., "FL350")
- **Translation Logic**: Frontend JavaScript converts feet to appropriate display format based on transition altitude
- **Configuration**: Transition altitude can be modified in `env.py` to match local aviation standards

## Separation Rules

The system enforces two key separation rules:

1. **Departure Separation**: Minimum 2 minutes between departures from the same airport
2. **Same Route Separation**: Minimum 5 minutes between flights with identical origin-destination

These rules prevent aircraft with identical routes from departing too close together while maintaining event realism.

## Purpose

This system enables event organisers to:
- **Parse SimBrief XML flight plans** and analyse multiple routes
- **Intentionally generate and identify conflicts** between aircraft to maximise ATC workload and event excitement
- **Focus on "First Conflicts"** - the initial point where two aircraft first meet conflict criteria, representing the moment ATC first needs to intervene
- **Provide detailed conflict analysis** with location, timing, and phase information
- **Detect conflicts both at waypoints and between waypoints** for comprehensive event realism
- **Generate KML files** for Google Earth visualisation with diverse colour schemes
- **Schedule departures accurately** based on conflict analysis results

## Quick Start

### Prerequisites
- Python 3.6+
- SimBrief XML flight plan files

## Docker Installation (Recommended for Remote Deployment)

### Option 1: Minimal Setup (Recommended)

If you only need to run the application and don't need the source code:

```bash
# Download just the docker-compose.yml
curl -O https://raw.githubusercontent.com/t288matt/vatsim-chaos/main/docker-compose.yml

# Create required directories
mkdir -p temp xml_files logs

# Edit volume paths in docker-compose.yml
nano docker-compose.yml
# or
vim docker-compose.yml
# or
code docker-compose.yml
```

**Find this section:**
```yaml
volumes:
  - /home/matt/data/vatsim-chaos/temp:/app/temp:rw  # Processing results
  - /home/matt/data/vatsim-chaos/xml_files:/app/xml_files:rw  # XML storage
  - /home/matt/data/vatsim-chaos/logs:/app/logs:rw  # Application logs
```

**Change it to:**
```yaml
volumes:
  - ./temp:/app/temp:rw  # Processing results
  - ./xml_files:/app/xml_files:rw  # XML storage
  - ./logs:/app/logs:rw  # Application logs
```

**Start the application:**
```bash
# Start using the pre-built image (no build needed!)
docker-compose up -d

# Access the application
# Main Web Interface: http://YOUR_IP:5000
# Animation Server: http://YOUR_IP:8000
```

### Option 2: Full Repository Clone

If you want the complete project with source code:

```bash
# Clone the entire repository
git clone https://github.com/t288matt/vatsim-chaos.git
cd vatsim-chaos

# Update volume paths in docker-compose.yml (same as Option 1)

# Create directories
mkdir -p temp xml_files logs

# Start the application
docker-compose up -d
```

### Useful Docker Commands

```bash
# Check if containers are running
docker-compose ps

# View logs
docker-compose logs -f

# Stop the application
docker-compose down

# Restart the application
docker-compose restart

# Access container shell (for debugging)
docker-compose exec atc-conflict bash
```

### Troubleshooting

#### If ports are already in use:
```bash
# Check what's using the ports
sudo netstat -tulpn | grep :5000
sudo netstat -tulpn | grep :8000

# Stop conflicting services or change ports in docker-compose.yml
```

#### If you need to change ports:
Edit `docker-compose.yml` and change:
```yaml
ports:
  - "YOUR_PORT:5000"  # Change YOUR_PORT to available port
  - "YOUR_ANIMATION_PORT:8000"
```

#### Check resource usage:
```bash
docker stats
```

### Important Notes

- **Animation files are generated inside the container** and are not persisted to the host
- **Uploaded XML files are stored in the `xml_files` directory** on the host
- **Processing results are stored in the `temp` directory** on the host
- **Logs are stored in the `logs` directory** on the host
- **Animation files are recreated each time** you process new flight plans

The application should be fully functional once the containers are running!

### Web Interface (Recommended)
The easiest way to use the system is through the modern web interface:

```bash
# Start the web server
cd web
python app.py

# Open in browser: http://localhost:5000
```

The web interface provides:
- **Drag-and-drop file upload** with validation
- **File library management** with selection controls
- **Event time configuration** (default: 08:00-11:00)
- **Real-time processing** with progress tracking
- **3D visualization** with Cesium integration
- **Pilot briefing** with export options

### Command Line Workflow
For advanced users or automation:

```bash
# Run complete workflow (extract → analyse → report → merge → schedule → frontend)
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
Open animation/animation.html in your browser

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
- `animation/conflict_points.json` - Conflict location/timing (filtered by altitude)
- `animation/animation.html` - 3D web visualization
- `audit_conflict_output.txt` - **Raw data audit report** (Markdown tables showing exact values across all data sources)

### Recent Fixes and Improvements

#### UI/UX Enhancements
- **VATSIM Radar-style Interface**: Modern dark theme with glass morphism effects
- **Frontend Time Controls**: Event time parameters moved from backend to frontend
- **File Management**: Added file deletion functionality with trash can icons
- **Button State Management**: Process button remains disabled until files are selected
- **Text Updates**: Changed "Process Analysis" to "Generate Schedule" and "Analysis Time Window" to "Event Time"
- **Default Times**: Updated default event time from 10:00-18:00 to 08:00-11:00
- **Upload Optimization**: Reduced upload box height for better space utilization

#### Technical Fixes
- **Animation Time Display**: Fixed event start/end times not being passed through to animation interface
- **Pilot Briefing Display**: Fixed white text on white background issue in briefing modal
- **Time Parameter Flow**: Ensured UTC time parameters are passed correctly through the entire processing pipeline
- **Metadata Integration**: Animation now uses event start/end times from metadata instead of hardcoded defaults

## System Architecture

### Linear Data Flow (No Circular Dependencies)
```
Conflict Generation → Scheduling → Animation Generation
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
- **Event Planning**: Helps organisers understand when conflicts will first occur
- **Resource Allocation**: Enables better planning of ATC resources and timing
- **Realistic Scenarios**: Focuses on the most critical conflict moment rather than tracking every subsequent conflict

### Output Formats
- **Detailed First Conflict List**: Shows only the first conflict between each aircraft pair with location, altitudes, times, and phases
- **JSON Export**: Structured data for further analysis (stored in temp directory)
- **KML Visualisation**: Google Earth compatible files with 40 diverse colours
- **Smart Location Format**: Shows conflicts between waypoints as "X NM [direction] of [waypoint]"

## SimBrief XML Generation Guidelines

### Important: Altitude Handling in SimBrief

When generating XML files in SimBrief, **always explicitly set altitudes** rather than letting SimBrief auto-calculate them. If you let SimBrief auto-calculate altitudes, it may insert unexpected step climbs and descents that pilots wouldn't typically fly.

**Example of SimBrief Auto-Calculated Issues:**
- FL350 → FL360 → FL350 on north-south routes
- Unnecessary step climbs during cruise
- Unrealistic altitude changes that don't match pilot behavior

**Best Practice:**
1. **Set explicit altitudes** for each waypoint in SimBrief
2. **Use realistic climb/descent profiles** (e.g., climb to FL360, cruise, then descend)
3. **Avoid letting SimBrief insert intermediate altitude changes** during cruise
4. **Review the flight plan** to ensure altitude changes match expected pilot behavior

### Critical: Conflict Analysis Based on SimBrief Data

**All conflict detection in this system is based explicitly on the climb profiles and altitudes from SimBrief XML files.** The system reads the exact altitude values and timing from your SimBrief flight plans to determine when and where aircraft will conflict.

**Before submitting XML files to the app:**
1. **Sense-check your SimBrief flight plans** - ensure altitudes and climb profiles are realistic
2. **Verify altitude assignments** - make sure each waypoint has appropriate altitudes for the aircraft type
3. **Review climb/descent profiles** - ensure they match expected pilot behavior for the route
4. **Test with a few flights first** - validate that the conflict analysis produces realistic results

**Why this matters:**
- **Garbage in, garbage out** - unrealistic SimBrief altitudes will produce unrealistic conflicts
- **Event planning depends on accuracy** - controllers need realistic conflict scenarios
- **Pilot behavior modeling** - conflicts should reflect how pilots actually fly these routes

This ensures the generated XML files contain realistic altitude profiles that match how pilots actually fly, leading to more accurate conflict analysis and event scenarios.

### System Limitation: Same Origin-Destination Routes

The system cannot process multiple flights with identical origin-destination pairs. Only the first flight per route will be processed.

**To avoid this limitation:**
- Remove duplicate files with the same origin and destination.

## Web Interface

### Modern ATC-Style Interface
The system now features a modern web interface inspired by VATSIM Radar with:

- **Dark Aviation Theme** - Professional dark colour scheme with aviation blue accents
- **Glass Morphism Effects** - Modern translucent panels with backdrop blur
- **Responsive Design** - Optimised for different screen sizes
- **File Management** - Drag-and-drop upload with validation and file library
- **Event Time Controls** - Frontend time parameter controls (08:00-11:00 default)
- **Real-time Processing** - Live progress tracking with step-by-step status
- **3D Visualization** - Cesium-based 3D map integration
- **Pilot Briefing Modal** - Formatted briefing display with print/download options

### Key Features
- **File Upload**: Drag-and-drop XML file upload with validation
- **File Library**: Manage uploaded files with selection controls and deletion
- **Event Time Window**: Set custom start/end times for conflict generation
- **Generate Schedule**: Process selected files to create conflict scenarios
- **3D Map View**: Interactive Cesium-based visualization of flight paths
- **Pilot Briefing**: Access formatted conflict briefing with export options

### Interface Components
- **Flight Plan Upload**: Upload and validate SimBrief XML files
- **Event Time**: Configure the time window for conflict generation (default: 08:00-11:00)
- **File Library**: Select and manage uploaded files with validation status
- **Generate Schedule**: Process selected files to create conflict scenarios
- **Processing Status**: Real-time progress tracking with step indicators
- **3D Map**: Interactive visualization of flight paths and conflicts
- **Pilot Briefing**: Access and export formatted conflict information

## System Components

### Python Scripts - Input and Output Files

| Script | Input Files | Output Files |
|--------|-------------|--------------|
| **execute.py** | None (master script) | None (orchestrates other scripts) |
| **extract_simbrief_xml_flightplan.py** | `*.xml` (SimBrief XML files in root directory) | `temp/*_data.json` (individual flight data)<br>`temp/*.kml` (individual KML files) |
| **find_potential_conflicts.py** | `*.xml` (SimBrief XML files)<br>`temp/*_data.json` (individual flight data) | `temp/potential_conflict_data.json` (conflict analysis)<br>`conflict_list.txt` (formatted conflict report)<br>`temp/routes_with_added_interpolated_points.json` (interpolated routes) |
| **merge_kml_flightplans.py** | `temp/*.kml` (individual KML files) | `merged_flightplans.kml` (merged KML for Google Earth) |
| **generate_schedule_conflicts.py** | `temp/potential_conflict_data.json` (conflict analysis)<br>`temp/routes_with_added_interpolated_points.json` (interpolated routes) | `pilot_briefing.txt` (pilot briefing)<br>`temp/routes_with_added_interpolated_points.json` (updated with schedule metadata) |
| **generate_animation.py** | `temp/routes_with_added_interpolated_points.json` (single source of truth) | `animation/animation_data.json` (complete animation data)<br>`animation/conflict_points.json` (conflict locations) |
| **audit_conflict.py** | `temp/potential_conflict_data.json` (conflict analysis)<br>`temp/routes_with_added_interpolated_points.json` (interpolated routes)<br>`animation/animation_data.json` (animation data) | `audit_conflict_output.txt` (data integrity audit report) |
| **animation/validate_animation_data.py** | `animation/animation_data.json` (animation data) | Console output (validation results) |

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
- `animation/animation.html` - 3D animated web visualization (CesiumJS)
- 40 diverse colours for easy route identification

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

### Colour Scheme
The system uses 40 diverse colours for route visualisation:
- **Primary colours**: Red, Green, Blue, Magenta, Cyan, Yellow
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
- **Maximise First Conflict Density**: Generate as many initial conflicts as possible in a given airspace
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
python find_potential_conflicts.py        # Analyse first conflicts only
python merge_kml_flightplans.py              # Merge KML files only
python generate_animation.py              # Export web visualization data only
```

### Recent Improvements Summary
- **Circular Dependency Elimination**: Linear data flow from analysis to visualization
- **Metadata-Based Approach**: Departure schedule shared via interpolated points metadata
- **Data Structure Simplification**: Removed x/y projected coordinates from animation data
- **Performance Optimization**: Reduced file sizes and processing overhead
- **Audit Enhancement**: Time values rounded to zero decimal places for cleaner output