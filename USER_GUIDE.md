# ATC Conflict Generation System - User Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Key Concepts and Definitions](#key-concepts-and-definitions)
3. [Getting Started](#getting-started)
4. [Web Interface Guide](#web-interface-guide)
5. [Command Line Usage](#command-line-usage)
6. [SimBrief XML Guidelines](#simbrief-xml-guidelines)
7. [Understanding Conflict Analysis](#understanding-conflict-analysis)
8. [Output Files and Results](#output-files-and-results)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

## System Overview

The ATC Conflict Generation System is designed to help event organisers create challenging air traffic control (ATC) scenarios by analysing SimBrief XML flight plans and identifying potential conflicts between aircraft. The system generates realistic conflict scenarios that challenge controllers while providing fun, dynamic events for pilots.

### Purpose
- **Event Planning**: Create scenarios where controllers are challenged and pilots enjoy dynamic events
- **Conflict Detection**: Identify realistic conflicts between aircraft using 3D spatial analysis
- **Schedule Generation**: Create departure schedules that maximize ATC workload
- **Visualization**: Provide 3D visualizations and reports for event planning

### Dual Interface Support
- **Web Interface** (Recommended): Modern browser-based interface with drag-and-drop file upload
- **Command Line**: Direct script execution for batch processing and automation

## Key Concepts and Definitions

### What is a "Conflict"?
A conflict occurs when two aircraft meet specific criteria simultaneously:

**Conflict Criteria:**
- **Lateral Separation**: Aircraft are within 3 nautical miles of each other
- **Vertical Separation**: Aircraft are within 900 feet vertically of each other
- **Altitude Threshold**: Both aircraft must be above 5,000 feet
- **Time Coincidence**: Aircraft must be at the conflict location at the same time

**Example Conflict:**
```
Flight A: FLT0001 (YBDG-YSBK) at FL350, position: 2.1 NM NE of YBDG
Flight B: FLT0002 (YSSY-YSWG) at FL340, position: 2.1 NM NE of YBDG
Time: 08:15 UTC
Separation: 2.3nm lateral, 500ft vertical
```

### "First Conflict" Concept
The system focuses on **"First Conflicts"** - the initial point where two aircraft first meet conflict criteria during their flights. This is critical because:

- **ATC Intervention Point**: Represents when controllers first need to intervene
- **Event Planning**: Helps organizers understand when conflicts will first occur
- **Resource Allocation**: Enables better planning of ATC resources and timing
- **Realistic Scenarios**: Focuses on the most critical conflict moment

### Flight ID System
Each flight receives a unique identifier (FLT0001, FLT0002, etc.) for better tracking:
- **Unique Identification**: Sequential flight IDs during XML processing
- **Route Preservation**: Origin-destination information maintained alongside flight IDs
- **Separation Rules**: Both flight IDs and routes used for separation enforcement
- **Conflict Tracking**: Enables tracking of "first conflicts" between unique aircraft pairs

### Altitude Handling
The system uses consistent altitude handling across backend and frontend:

**Backend Processing:**
- All altitudes stored and processed in feet (e.g., 2000ft, 36000ft)

**Frontend Display:**
- **Below 10,500ft**: Displayed in feet (e.g., "8500ft")
- **At or above 10,500ft**: Displayed as flight levels (e.g., "FL350")

### Separation Rules
The system enforces two key separation rules:

1. **Departure Separation**: Minimum 2 minutes between departures from the same airport
2. **Same Route Separation**: Minimum 5 minutes between flights with identical origin-destination

## Getting Started

### Prerequisites
- Python 3.6 or higher
- SimBrief XML flight plan files
- Modern web browser (for web interface)

### Quick Start (Web Interface - Recommended)

1. **Start the Web Server:**
   ```bash
   cd web
   python app.py
   ```

2. **Open Your Browser:**
   Navigate to `http://localhost:5000`

3. **Upload Flight Plans:**
   - Drag and drop SimBrief XML files into the upload area
   - Or click to browse and select files

4. **Configure Event Time:**
   - Set start time (default: 08:00)
   - Set end time (default: 11:00)

5. **Generate Schedule:**
   - Select files from the library
   - Click "Generate Schedule" button
   - Monitor progress in real-time

6. **View Results:**
   - 3D map visualization with flight paths
   - Pilot briefing with conflict details
   - Export options for reports

### Quick Start (Command Line)

```bash
# Run complete workflow
python execute.py

# Run with custom event times
python execute.py --start-time 14:00 --end-time 18:00
```

## Web Interface Guide

### Main Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│                    Header/Title Bar                        │
├─────────────────┬───────────────────────────────────────────┤
│                 │                                         │
│   Left Panel    │              Right Panel                │
│   (File Mgmt)   │              (Map View)                │
│                 │                                         │
│ ┌─────────────┐ │  ┌─────────────────────────────────────┐ │
│ │ File Upload │ │  │                                     │ │
│ │             │ │  │                                     │ │
│ │ File List   │ │  │         Cesium Map                  │ │
│ │ (Checkboxes)│ │  │                                     │ │
│ │             │ │  │                                     │ │
│ └─────────────┘ │  └─────────────────────────────────────┘ │
│                 │                                         │
│ ┌─────────────┐ │                                         │
│ │ Process     │ │                                         │
│ │ Button      │ │                                         │
│ └─────────────┘ │                                         │
│                 │                                         │
│ ┌─────────────┐ │                                         │
│ │ Pilot       │ │                                         │
│ │ Briefing    │ │                                         │
│ │ Button      │ │                                         │
│ └─────────────┘ │                                         │
└─────────────────┴─────────────────────────────────────────┘
```

### File Management

#### Upload Area
- **Drag and Drop**: Drag XML files directly into the upload area
- **File Browser**: Click to browse and select files
- **Validation**: System validates XML format and structure
- **Feedback**: Shows upload progress and success/error messages

#### File Library
- **Checkbox Selection**: Select multiple files for processing
- **File Information**: Shows filename, upload date, and file size
- **Validation Status**: Indicates if files are valid for processing
- **File Removal**: Delete individual files with trash can icons
- **Select All/None**: Quick selection buttons for convenience

### Event Time Configuration
- **Start Time**: When the event begins (default: 08:00)
- **End Time**: When the event ends (default: 11:00)
- **Time Format**: 24-hour format (HH:MM)
- **UTC Time**: All times are in UTC

### Processing Workflow

#### Generate Schedule Button
- **State Management**: Button changes appearance based on current state
- **Disabled**: When no files are selected
- **Ready**: When files are selected and ready to process
- **Processing**: During analysis with loading animation
- **Complete**: When processing finishes successfully

#### Progress Tracking
The system shows real-time progress through these steps:

1. **Extract Flight Plan Data**: Parse XML files and extract waypoints
2. **Analyze Conflicts**: Perform 3D spatial conflict detection
3. **Merge KML Files**: Combine individual flight plans for visualization
4. **Schedule Conflicts**: Generate departure schedule based on conflicts
5. **Export Animation Data**: Create data for 3D visualization
6. **Audit Conflict Data**: Verify data integrity across all stages

### 3D Map Visualization

#### Cesium Map Features
- **3D Aircraft Models**: Animated aircraft with realistic movement
- **Real-time Altitude Labels**: Shows current altitude below each aircraft
- **Conflict Points**: Highlights where conflicts occur
- **Timeline Controls**: Play/pause/seek through the animation
- **Camera Controls**: Zoom, pan, and rotate the 3D view
- **Flight Labels**: Toggle aircraft labels on/off
- **Auto-zoom**: Automatically positions camera to show all flights

#### Map Controls
- **Timeline**: Control animation playback speed and position
- **Camera**: Manual camera positioning and auto-follow options
- **Display Options**: Toggle flight paths, labels, and conflict points
- **Full-screen**: Expand map to full screen for detailed viewing

### Pilot Briefing Modal

#### Accessing the Briefing
- Click the "Pilot Briefing" button after processing completes
- Modal appears over the main interface
- Map remains visible in the background

#### Briefing Content
- **Departure Schedule**: All flights with departure times
- **Conflict Details**: Location, timing, and separation information
- **Flight Information**: Aircraft types, routes, and altitudes
- **Event Summary**: Total flights and conflicts generated

#### Export Options
- **Print**: Print the briefing to paper or PDF
- **Download**: Save briefing as text file
- **Copy**: Copy content to clipboard

## Command Line Usage

### Complete Workflow
```bash
# Run the complete analysis pipeline
python execute.py

# Run with custom event times
python execute.py --start-time 14:00 --end-time 18:00
```

### Individual Scripts

#### 1. Extract Flight Plan Data
```bash
# Place SimBrief XML files in the project directory
python extract_simbrief_xml_flightplan.py
```
**Outputs:**
- Individual KML files in `temp/` directory
- Individual JSON data files in `temp/` directory

#### 2. Analyze Conflicts
```bash
python find_potential_conflicts.py
```
**Outputs:**
- `temp/potential_conflict_data.json` - Detailed conflict analysis
- `conflict_list.txt` - Formatted conflict report (first conflicts only)
- `temp/routes_with_added_interpolated_points.json` - Interpolated routes

#### 3. Generate Schedule and Briefing
```bash
python generate_schedule_conflicts.py --start 14:00 --end 18:00
```
**Outputs:**
- `pilot_briefing.txt` - Pilot conflict briefing
- Updated `temp/routes_with_added_interpolated_points.json` with schedule metadata

#### 4. Generate Animation Data
```bash
python generate_animation.py
```
**Outputs:**
- `animation/animation_data.json` - Animation data for web visualization
- `animation/conflict_points.json` - Conflict location/timing data

#### 5. Merge KML Files (Optional)
```bash
python merge_kml_flightplans.py
```
**Outputs:**
- `merged_flightplans.kml` - Combined KML file for Google Earth

#### 6. Audit Data Integrity (Optional)
```bash
python audit_conflict.py
```
**Outputs:**
- `audit_conflict_output.txt` - Raw data audit report

### Expected Output Files

#### Core Analysis Files
- `temp/potential_conflict_data.json` - Detailed conflict analysis
- `conflict_list.txt` - Formatted conflict list (first conflicts only)
- `temp/routes_with_added_interpolated_points.json` - Interpolated points with departure metadata

#### Visualization Files
- `merged_flightplans.kml` - Combined KML file for Google Earth
- `animation/animation_data.json` - Animation data for Cesium (simplified structure)
- `animation/conflict_points.json` - Conflict location/timing (filtered by altitude)
- `animation/animation.html` - 3D web visualization

#### Reports
- `pilot_briefing.txt` - Pilot conflict briefing (authoritative, includes all departure times and conflict details)
- `audit_conflict_output.txt` - Raw data audit report (Markdown tables showing exact values)

## SimBrief XML Guidelines

### Critical: Altitude Handling in SimBrief

**IMPORTANT**: When generating XML files in SimBrief, **always explicitly set altitudes** rather than letting SimBrief auto-calculate them.

#### Problems with Auto-Calculated Altitudes
- **Unexpected Step Climbs**: FL350 → FL360 → FL350 on north-south routes
- **Unrealistic Changes**: Unnecessary altitude changes during cruise
- **Pilot Behavior Mismatch**: Altitudes that don't match how pilots actually fly

#### Best Practices
1. **Set Explicit Altitudes**: Manually set altitude for each waypoint
2. **Use Realistic Profiles**: Climb to cruise altitude, maintain, then descend
3. **Avoid Auto-Calculation**: Don't let SimBrief insert intermediate changes
4. **Review Flight Plans**: Ensure altitude changes match expected pilot behavior

### Why This Matters
- **Conflict Analysis Accuracy**: All conflict detection is based on SimBrief altitudes
- **Event Realism**: Controllers need realistic conflict scenarios
- **Pilot Behavior Modeling**: Conflicts should reflect actual pilot behavior

### System Limitation: Same Origin-Destination Routes

The system cannot process multiple flights with identical origin-destination pairs. Only the first flight per route will be processed.

**Solution**: Remove duplicate files with the same origin and destination.

## Understanding Conflict Analysis

### Conflict Detection Methods

#### 1. At Waypoints
- **Detection**: Conflicts when aircraft are at the same named waypoint
- **Example**: "YORG/VIRUR" - both aircraft at VIRUR waypoint
- **Phase**: Actual flight phase (climb, cruise, descent)

#### 2. Between Waypoints
- **Detection**: Conflicts when routes cross at interpolated points
- **Example**: "2.1 NM NE of YBDG" - conflict between waypoints
- **Phase**: Determined by position relative to TOC/TOD
- **Interpolation**: Configurable spacing (default 2nm) between waypoints

### Conflict Calculation Process

#### 1. Distance Calculation
- **Method**: Haversine formula for lateral separation
- **Unit**: Nautical miles
- **Threshold**: < 3 nautical miles

#### 2. Altitude Analysis
- **Method**: Absolute difference between aircraft altitudes
- **Unit**: Feet
- **Threshold**: < 900 feet

#### 3. Time Analysis
- **Method**: Converted from seconds to minutes
- **Format**: UTC time (HH:MM)
- **Coincidence**: Aircraft must be at conflict location simultaneously

#### 4. Phase Determination
- **Climb**: Before TOC (Top of Climb) waypoint
- **Cruise**: Between TOC and TOD (Top of Descent) waypoints
- **Descent**: After TOD waypoint

### Filtering Logic

#### Altitude Threshold
- **Minimum**: Aircraft must be above 5,000 feet
- **Purpose**: Focus on enroute conflicts, not ground operations

#### Duplicate Filtering
- **Distance**: Conflicts within 4 NM of previous conflicts ignored
- **Purpose**: Avoid reporting the same conflict multiple times

#### First Conflict Only
- **Logic**: Only the earliest conflict between aircraft pairs reported
- **Purpose**: Focus on ATC intervention points

### Example Conflict Output

```
Time: 08:15 UTC
Flight A: FLT0001 (YBDG-YSBK) at FL350, position: 2.1 NM NE of YBDG
Flight B: FLT0002 (YSSY-YSWG) at FL340, position: 2.1 NM NE of YBDG
Separation: 2.3nm lateral, 500ft vertical
Phase: Both aircraft in climb phase
```

## Output Files and Results

### Core Analysis Files

#### `temp/potential_conflict_data.json`
**Purpose**: Detailed conflict analysis with all technical data
**Content**:
- Flight information (ID, origin, destination, aircraft type)
- Waypoint data with coordinates, altitudes, and timing
- Conflict details (location, separation, timing, phase)
- Interpolated route points for enhanced detection

#### `conflict_list.txt`
**Purpose**: Human-readable conflict report
**Content**:
- First conflicts only (earliest conflict between each aircraft pair)
- Formatted for easy reading
- Location, timing, and separation information
- Flight identification and route details

#### `temp/routes_with_added_interpolated_points.json`
**Purpose**: Single source of truth for all flight data
**Content**:
- Original waypoints from flight plans
- Additional interpolated points between waypoints
- Departure schedule metadata
- Complete flight data for downstream processing

### Visualization Files

#### `merged_flightplans.kml`
**Purpose**: Google Earth visualization
**Features**:
- Combined KML file with all flight paths
- 40 diverse colors for route identification
- 3D flight paths with altitude information
- Compatible with Google Earth Pro

#### `animation/animation_data.json`
**Purpose**: Web-based 3D visualization
**Features**:
- Simplified data structure (lat/lon/altitude only)
- Real-time animation data
- Aircraft movement and timing information
- Compatible with CesiumJS viewer

#### `animation/animation.html`
**Purpose**: Interactive 3D web visualization
**Features**:
- CesiumJS-based 3D map
- Animated aircraft with realistic movement
- Timeline controls for playback
- Camera controls for navigation
- Real-time altitude labels
- Conflict point highlighting

### Reports

#### `pilot_briefing.txt`
**Purpose**: Authoritative conflict briefing
**Content**:
- Complete departure schedule with times
- Detailed conflict information
- Flight details (aircraft type, route, altitude)
- Event summary (total flights and conflicts)
- Formatted for easy reading and printing

#### `audit_conflict_output.txt`
**Purpose**: Data integrity verification
**Content**:
- Raw data comparison across all processing stages
- Exact values with no conversions
- Departure time verification
- Markdown tables for easy reading
- Verification of scheduling accuracy

### File Organization

#### `temp/` Directory
- Individual KML files for each flight plan
- Individual JSON data files for each flight plan
- `potential_conflict_data.json` - Main analysis results
- `routes_with_added_interpolated_points.json` - Interpolated points with metadata

#### `animation/` Directory
- `animation_data.json` - Complete animation data
- `conflict_points.json` - Conflict location/timing data
- `animation.html` - 3D web visualization
- `status_bar_development.html` - Development version with status bar

## Troubleshooting

### Common Issues

#### File Upload Problems
**Problem**: Files not uploading or showing validation errors
**Solutions**:
- Ensure files are valid SimBrief XML format
- Check file size (should be reasonable for flight plans)
- Verify XML structure contains required waypoint data
- Try refreshing the page and uploading again

#### Processing Errors
**Problem**: "Generate Schedule" button fails or shows errors
**Solutions**:
- Check that files are selected before processing
- Verify event time settings are valid (start before end)
- Ensure sufficient disk space for temporary files
- Check console for specific error messages

#### Map Loading Issues
**Problem**: 3D map doesn't load or shows errors
**Solutions**:
- Ensure JavaScript is enabled in browser
- Check internet connection (Cesium requires CDN resources)
- Try refreshing the page
- Verify that processing completed successfully

#### Conflict Analysis Issues
**Problem**: No conflicts detected or unrealistic conflicts
**Solutions**:
- Review SimBrief XML files for realistic altitude profiles
- Ensure waypoints have explicit altitudes set
- Check that flight paths actually cross or converge
- Verify event time window includes flight times

### Error Messages

#### "No files selected"
**Cause**: No files checked in the file library
**Solution**: Select one or more files before clicking "Generate Schedule"

#### "Invalid XML format"
**Cause**: File is not a valid SimBrief XML flight plan
**Solution**: Ensure files are exported from SimBrief in XML format

#### "Processing failed"
**Cause**: Error during analysis pipeline
**Solution**: Check console for specific error details, verify file formats

#### "Map data not available"
**Cause**: Animation data not generated or corrupted
**Solution**: Re-run processing, check that all steps completed successfully

### Performance Issues

#### Slow Processing
**Causes**:
- Large number of flight plans
- Complex route structures
- Limited system resources

**Solutions**:
- Process fewer files at once
- Close other applications to free memory
- Use command line for batch processing

#### Map Performance
**Causes**:
- Too many aircraft visible
- Complex 3D models
- Browser limitations

**Solutions**:
- Toggle flight labels off
- Reduce animation speed
- Use a modern browser with hardware acceleration

## Advanced Features

### Command Line Automation

#### Batch Processing
```bash
# Process multiple event scenarios
for start_time in 08:00 10:00 14:00; do
    python execute.py --start-time $start_time --end-time 11:00
done
```

#### Custom Analysis
```bash
# Run individual analysis steps
python find_potential_conflicts.py
python generate_schedule_conflicts.py --start 14:00 --end 18:00
python generate_animation.py
```

### Data Validation

#### Audit System
```bash
# Verify data integrity across all stages
python audit_conflict.py
```

**Output**: Detailed comparison of data across all processing stages

#### Animation Validation
```bash
# Validate animation data structure
python animation/validate_animation_data.py
```

**Output**: Console output showing validation results

### Custom Configuration

#### Environment Variables
Edit `env.py` to modify system behavior:
- `TRANSITION_ALTITUDE_FT`: Altitude threshold for flight level display
- `CONFLICT_DISTANCE_NM`: Lateral separation threshold
- `CONFLICT_ALTITUDE_FT`: Vertical separation threshold
- `MIN_ALTITUDE_FT`: Minimum altitude for conflict detection

#### Interpolation Settings
Modify `find_potential_conflicts.py` for custom interpolation:
- `INTERPOLATION_DISTANCE_NM`: Distance between interpolated points
- `DUPLICATE_FILTER_DISTANCE_NM`: Distance for duplicate filtering

### Integration Options

#### Google Earth Integration
- Use `merged_flightplans.kml` in Google Earth Pro
- 40-color scheme for easy route identification
- 3D flight paths with altitude information

#### Web Integration
- Embed `animation/animation.html` in other web applications
- Use `animation/animation_data.json` for custom visualizations
- Integrate with existing ATC training systems

#### API Development
- Extend Flask backend for API endpoints
- Integrate with external flight planning systems
- Connect to real-time ATC systems

### Future Enhancements

#### Planned Features
- **Real-time Integration**: Connect to live flight data
- **Advanced Scheduling**: Machine learning for optimal departure times
- **Weather Integration**: Include weather effects on conflicts
- **Multi-region Support**: Handle multiple airspace regions
- **Advanced Visualization**: More sophisticated 3D effects

#### Customization Options
- **Conflict Criteria**: Adjustable separation thresholds
- **Visualization Themes**: Custom color schemes and styles
- **Export Formats**: Additional output formats (PDF, Excel, etc.)
- **Integration APIs**: REST API for external system integration

---

## Support and Resources

### Documentation
- `README.md`: System overview and technical details
- `ARCHITECTURE.md`: Detailed system architecture
- `FRONTEND_REQUIREMENTS.md`: Web interface specifications

### File Structure
```
Chaos2/
├── web/                    # Web interface
│   ├── app.py             # Flask backend
│   ├── templates/         # HTML templates
│   └── static/           # CSS, JS, and assets
├── animation/             # 3D visualization
│   ├── animation.html    # Main visualization
│   └── animation_data.json
├── temp/                  # Temporary data files
├── *.py                  # Python analysis scripts
└── *.md                  # Documentation files
```

### Getting Help
- Check the troubleshooting section for common issues
- Review the documentation files for technical details
- Verify file formats and system requirements
- Test with simple flight plans before complex scenarios

---

*This user guide covers all aspects of the ATC Conflict Generation System. For technical details, refer to the README.md and ARCHITECTURE.md files.* 