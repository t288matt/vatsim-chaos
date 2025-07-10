# ATC Conflict Analysis System

A Python-based system for generating chaotic, conflicting SimBrief XML flight plans to create challenging air traffic control (ATC) event scenarios. The system is designed to help event organizers create situations where ATC must resolve numerous, simultaneous conflicts during live events.

## 🎯 Purpose

This system enables event organizers to:
- **Parse SimBrief XML flight plans** and analyze multiple routes
- **Intentionally generate and identify conflicts** between aircraft to maximize ATC workload
- **Provide detailed conflict analysis** with location, timing, and phase information
- **Detect conflicts both at waypoints and between waypoints** for comprehensive event realism
- **Generate KML files** for Google Earth visualization with diverse color schemes

## 🚀 Quick Start

### Prerequisites
- Python 3.6+
- SimBrief XML flight plan files

### Basic Workflow
```bash
# 1. Place SimBrief XML files in the project directory
# 2. Extract flight plan data and generate KML files
python simbrief_xml_flightplan_extractor.py

# 3. Run conflict analysis on all XML files
python conflict_analyzer.py

# 4. Generate readable conflict report
python conflicts_list.py

# 5. Merge KML files for Google Earth viewing
python merge_kml_flightplans.py
```

### Expected Output
- `temp/conflict_analysis.json` - Detailed conflict data
- `conflict_list.txt` - Formatted conflict list
- `merged_flightplans.kml` - Combined KML file for Google Earth
- Individual KML files in `temp/` directory

## 🔍 Conflict Detection Features

### Detection Methods
- **At Waypoints**: Detects conflicts when aircraft are at the same named waypoint
- **Between Waypoints**: Detects conflicts when routes cross at interpolated points along route segments
- **3D Analysis**: Considers lateral distance, vertical separation, and timing
- **Phase Detection**: Automatically determines climb, cruise, or descent phases based on TOC/TOD

### Conflict Criteria
- **Lateral Separation**: < 3 nautical miles
- **Vertical Separation**: < 900 feet
- **Altitude Threshold**: Aircraft must be above 2500 ft
- **Route Interpolation**: 10 interpolation points between waypoints for enroute conflicts
- **Duplicate Filtering**: Ignores conflicts within 4 NM of previous conflicts between same routes

### Output Formats
- **Detailed Conflict List**: Shows all conflicts with location, altitudes, times, and phases
- **JSON Export**: Structured data for further analysis (stored in temp directory)
- **KML Visualization**: Google Earth compatible files with 40 diverse colors
- **Smart Location Format**: Shows conflicts between waypoints as "X NM [direction] of [waypoint]"

## 📁 System Components

### Core Analysis
- `conflict_analyzer.py` - Main analysis engine with 3D spatial conflict detection
- `conflicts_list.py` - Conflict listing and reporting with smart formatting
- `conflict_list.txt` - Formatted conflict output

### Data Processing
- `simbrief_xml_flightplan_extractor.py` - Converts SimBrief XML to KML for visualization
- `merge_kml_flightplans.py` - Merges individual KML files into a single file

### Data Organization
- `temp/` - Directory containing all generated data files
  - Individual KML files for each flight plan
  - Individual JSON data files for each flight plan
  - `conflict_analysis.json` - Main analysis results

### Visualization
- `merged_flightplans.kml` - Combined KML file for Google Earth viewing
- 40 diverse colors for easy route identification

## 📊 Conflict Types

### At Waypoints
- **Location**: Shows waypoint names (e.g., "YORG/VIRUR")
- **Conflict Type**: "at waypoint"
- **Phase**: Actual flight phase (climb, cruise, descent)

### Between Waypoints
- **Location**: Shows distance and direction from nearest waypoint (e.g., "2.1 NM NE of YBDG")
- **Conflict Type**: "between waypoints"
- **Phase**: Determined by position relative to TOC/TOD (climb, cruise, descent)
- **Segments**: Shows route segments involved

## 🛠️ Technical Details

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
4. **Interpolation**: Linear interpolation between waypoints
5. **Nearest Waypoint**: Calculates distance/direction from closest waypoint on either route

### Filtering Logic
- **Low Altitude**: Aircraft ≤ 2500 ft excluded
- **Duplicate Conflicts**: Conflicts within 4 NM of previous conflicts between same routes ignored
- **Invalid Data**: Malformed XML entries skipped

### Color Scheme
The system uses 40 diverse colors for route visualization:
- **Primary colors**: Red, Green, Blue, Magenta, Cyan, Yellow
- **Pastel variants**: Light Blue, Pink, Lime Green, Light Red
- **Bright variants**: Bright Green, Bright Red, Bright Lime, Bright Pink
- **Metallic tones**: Gold, Amber, Lavender, Violet, Aqua, Rose, Orchid
- **Light variants**: Light Gold, Light Lavender, Light Mint, Light Salmon, Light Plum

## 📋 Example Output

```
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

## 🎪 Event Scenario Applications

This system is designed for event scenario creation, enabling organizers to:

### Scenario Creation
- **Maximize Conflict Density**: Generate as many conflicts as possible in a given airspace
- **Create Chaotic Situations**: Overlap routes and phases to challenge ATC
- **Increase Realism and Workload**: Simulate high-traffic, high-stress environments for live events

### Event Execution
- **Readable Output**: Clear conflict descriptions for event planning and ATC briefings
- **Visual Analysis**: Google Earth integration for spatial understanding
- **Structured Data**: JSON format for further analysis and integration

## 🔧 Advanced Usage

### Custom Analysis
```bash
# Run individual components
python simbrief_xml_flightplan_extractor.py  # Extract data only
python conflict_analyzer.py                   # Analyze conflicts only
python conflicts_list.py                      # Generate report only
python merge_kml_flightplans.py              # Merge KML files only
```

### File Organization
```
Chaos2/
├── Core Analysis
│   ├── conflict_analyzer.py      # Main analysis engine
│   ├── conflicts_list.py         # Conflict reporting
│   └── conflict_list.txt         # Formatted output
├── Data Processing
│   ├── simbrief_xml_flightplan_extractor.py  # XML extraction
│   └── merge_kml_flightplans.py             # KML merging
├── Input Data
│   └── *.xml                    # SimBrief XML files
├── Output Data
│   ├── temp/                    # Generated data files
│   │   ├── *.kml               # Individual KML files
│   │   ├── *_data.json         # Flight plan data
│   │   └── conflict_analysis.json  # Analysis results
│   └── merged_flightplans.kml  # Combined visualization
└── Documentation
    ├── README.md               # User documentation
    └── ARCHITECTURE.md         # Technical architecture
```

## 🚨 Troubleshooting

### Common Issues
1. **No XML files found**: Ensure SimBrief XML files are in the project directory
2. **No conflicts detected**: Check that aircraft altitudes are above 2500 ft
3. **KML files not generated**: Verify XML files are valid SimBrief format
4. **Memory errors**: Reduce number of flight plans for large datasets

### Error Messages
- `❌ No XML files found`: Place SimBrief XML files in the directory
- `⚠️ Error parsing waypoint`: Check XML file format and data integrity
- `❌ Need at least 2 flight plans`: Add more flight plan files for analysis

## 🔮 Future Enhancements

### Planned Features
1. **Real-time Processing**: WebSocket integration for live flight data
2. **Advanced Algorithms**: Machine learning for conflict prediction
3. **Database Integration**: Persistent storage for historical analysis
4. **API Layer**: RESTful interface for external integrations
5. **Enhanced Visualization**: 3D rendering and animation capabilities

### Contributing
The system is designed for easy extension and modification:
- Modular architecture with clear separation of concerns
- JSON-based data exchange between components
- Standard library dependencies for easy deployment
- Comprehensive error handling and logging

## 📚 Requirements

- **Python 3.6+**: Core runtime
- **Standard Library**: xml.etree.ElementTree, json, os, math
- **No External Dependencies**: Self-contained for easy deployment
- **SimBrief XML Files**: Flight plan data in SimBrief format

## 📄 License

This project is designed for event scenario creation and live ATC challenge applications.

---

**For detailed technical information, see [ARCHITECTURE.md](ARCHITECTURE.md)** 