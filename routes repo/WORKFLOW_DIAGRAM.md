# Workflow Diagram: ATC Conflict Analysis System

## System Overview
This workflow diagram illustrates the complete process flow from SimBrief XML input to final visualization outputs.

**Recent Improvements:**
- ✅ **Eliminated circular dependency** between scheduling and animation
- ✅ **Metadata-based approach** for departure schedule sharing
- ✅ **Removed x/y projected coordinates** from animation data
- ✅ **Linear data flow** with clear dependencies

```
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    ATC CONFLICT ANALYSIS WORKFLOW                                                                        │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                                    START                                                                                  │
│                                                                                                                                    │
│  ┌─────────────────┐                                                                                                                │
│  │   execute.py│                                                                                                                │
│  │   Master Script │                                                                                                                │
│  └─────────────────┘                                                                                                                │
│           │                                                                                                                          │
│           ▼                                                                                                                          │
│  ┌─────────────────┐                                                                                                                │
│  │ Check Prerequisites│                                                                                                                │
│  │ • 16 XML files  │                                                                                                                │
│  │ • Scripts exist │                                                                                                                │
│  │ • Dirs created  │                                                                                                                │
│  └─────────────────┘                                                                                                                │
│           │                                                                                                                          │
│           ▼                                                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STEP 1: XML EXTRACTION                                                                               │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    extract_simbrief_xml_flightplan.py                                                                           │  │
│  │                                                                                                                               │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                                    │  │
│  │  │ Parse XML   │───▶│ Extract     │───▶│ Generate    │───▶│ Save Flight │───▶│ Create KML  │                                    │  │
│  │  │ Files       │    │ Waypoints   │    │ Flight Data │    │ Data Files  │    │ Files       │                                    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘                                    │  │
│  │                                                                                                                               │  │
│  │  • Parse 16 XML files                                                                                                          │  │
│  │  • Extract coordinates, altitudes, times                                                                                       │  │
│  │  • Generate flight_plans.json                                                                                                  │  │
│  │  • Create individual KML files                                                                                                 │  │
│  │  • Save waypoint data                                                                                                          │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    OUTPUTS                                                                                        │  │
│  │  • flight_plans.json (flight data)                                                                                              │  │
│  │  • Individual KML files (16 files)                                                                                             │  │
│  │  • Waypoint coordinates and timing                                                                                              │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STEP 2: CONFLICT ANALYSIS                                                                           │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    find_potential_conflicts.py                                                                                │  │
│  │                                                                                                                               │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                                    │  │
│  │  │ Load Flight │───▶│ Detect      │───▶│ Filter      │───▶│ Generate    │───▶│ Save        │                                    │  │
│  │  │ Plans       │    │ Conflicts   │    │ by Altitude │    │ Reports     │    │ Analysis    │                                    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘                                    │  │
│  │                                                                                                                               │  │
│  │  • Load flight_plans.json                                                                                                      │  │
│  │  • Calculate lateral separation (< 3 NM)                                                                                       │  │
│  │  • Calculate vertical separation (< 900 ft)                                                                                    │  │
│  │  • Filter conflicts above 5000 ft                                                                                              │  │
│  │  • Optimize departure times                                                                                                    │  │
│  │  • Generate conflict reports                                                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    OUTPUTS                                                                                        │  │
│  │  • conflict_list.txt (2,704 bytes)                                                                                             │  │
│  │  • temp/potential_conflict_data.json                                                                                                 │  │
│  │  • temp/conflict_analysis.log                                                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STEP 3: KML MERGE                                                                                   │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    merge_kml_flightplans.py                                                                                      │  │
│  │                                                                                                                               │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                                    │  │
│  │  │ Find KML    │───▶│ Parse KML   │───▶│ Merge       │───▶│ Add Conflict│───▶│ Save        │                                    │  │
│  │  │ Files       │    │ Files       │    │ Flight      │    │ Markers     │    │ Merged KML  │                                    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘                                    │  │
│  │                                                                                                                               │  │
│  │  • Scan for individual KML files                                                                                              │  │
│  │  • Parse each KML file                                                                                                        │  │
│  │  • Combine all flight paths                                                                                                   │  │
│  │  • Add conflict location markers                                                                                               │  │
│  │  • Create single merged KML file                                                                                              │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    OUTPUTS                                                                                        │  │
│  │  • merged_flightplans.kml (140,897 bytes)                                                                                     │  │
│  │  • Google Earth compatible visualization                                                                                       │  │
│  │  • Conflict markers at intersection points                                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STEP 4: SCHEDULING & METADATA                                                                       │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    generate_schedule_conflicts.py                                                                                 │  │
│  │                                                                                                                               │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                                    │  │
│  │  │ Load        │───▶│ Calculate   │───▶│ Apply       │───▶│ Add         │───▶│ Save        │                                    │  │
│  │  │ Conflicts   │    │ Departure   │    │ Separation   │    │ Metadata    │    │ Files       │                                    │  │
│  │  │ Data        │    │ Times       │    │ Rules       │    │ to Points   │    │             │                                    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘                                    │  │
│  │                                                                                                                               │  │
│  │  • Load potential_conflict_data.json                                                                                                │  │
│  │  • Calculate optimal departure times                                                                                           │  │
│  │  • Apply 2-minute separation rules                                                                                            │  │
│  │  • Add departure schedule metadata to interpolated points                                                                      │  │
│  │  • Use interpolated points directly (no circular dependency)                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    OUTPUTS                                                                                        │  │
│  │  • pilot_briefing.txt - Pilot briefing document                                                                                │  │
│  │  • temp/routes_with_added_interpolated_points.json (with metadata)                                                              │  │
│  │  • _metadata.departure_schedule containing departure times                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STEP 5: ANIMATION GENERATION                                                                        │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    generate_animation.py                                                                                       │  │
│  │                                                                                                                               │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                                    │  │
│  │  │ Load        │───▶│ Read        │───▶│ Generate    │───▶│ Create      │───▶│ Save        │                                    │  │
│  │  │ Analysis    │    │ Metadata    │    │ Flight      │    │ Animation   │    │ JSON Files  │                                    │  │
│  │  │ Data        │    │ Schedule    │    │ Tracks      │    │ Timeline    │    │ (No x/y)    │                                    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘                                    │  │
│  │                                                                                                                               │  │
│  │  • Load potential_conflict_data.json                                                                                                │  │
│  │  • Read departure times from interpolated points metadata                                                                      │  │
│  │  • Extract waypoints from interpolated points                                                                                  │  │
│  │  • Generate flight track data (lat/lon/altitude only)                                                                         │  │
│  │  • Create animation timeline                                                                                                   │  │
│  │  • Export to animation/ (simplified structure)                                                                                │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    OUTPUTS                                                                                        │  │
│  │  • animation/animation_data.json (simplified, no x/y fields)                                                                    │  │
│  │  • animation/flight_tracks.json                                                                                                 │  │
│  │  • animation/conflict_points.json                                                                                               │  │
│  │  • Ready for 3D web visualization                                                                                              │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    STEP 6: DATA AUDIT                                                                                  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                    audit_conflict.py                                                                                             │  │
│  │                                                                                                                               │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                                    │  │
│  │  │ Load All    │───▶│ Compare     │───▶│ Round       │───▶│ Generate    │───▶│ Save        │                                    │  │
│  │  │ Data        │    │ Sources     │    │ Times       │    │ Markdown    │    │ Audit       │                                    │  │
│  │  │ Sources      │    │ (3 files)   │    │ (0 decimals)│    │ Tables      │    │ Report      │                                    │  │
│  │  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘                                    │  │
│  │                                                                                                                               │  │
│  │  • Load potential_conflict_data.json                                                                                                │  │
│  │  • Load routes_with_added_interpolated_points.json                                                                              │  │
│  │  • Load animation_data.json                                                                                                     │  │
│  │  • Compare conflict data across all sources                                                                                     │  │
│  │  • Round time values to zero decimal places                                                                                     │  │
│  │  • Generate readable Markdown tables                                                                                            │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    OUTPUTS                                                                                        │  │
│  │  • audit_conflict_output.txt - Markdown audit report                                                                             │  │
│  │  • Raw data comparison across all processing stages                                                                              │  │
│  │  • Time values rounded to zero decimal places                                                                                   │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    FINAL OUTPUTS                                                                                      │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    ANALYSIS REPORTS                                                                               │  │
│  │  • conflict_list.txt - Detailed conflict analysis                                                                                │  │
│  │  • temp/potential_conflict_data.json - Raw analysis data                                                                         │  │
│  │  • audit_conflict_output.txt - Data integrity audit                                                                              │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    VISUALIZATION FILES                                                                             │  │
│  │  • merged_flightplans.kml - Google Earth visualization                                                                          │  │
│  │  • Individual KML files for each flight plan                                                                                     │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    FRONTEND DATA                                                                                  │  │
│  │  • animation/animation_data.json - Complete animation data (simplified)                                                           │  │
│  │  • animation/flight_tracks.json - Individual flight paths                                                                        │  │
│  │  • animation/conflict_points.json - Conflict locations                                                                           │  │
│  │  • animation/cesium_flight_anim.html - 3D web visualization                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    SCHEDULING DATA                                                                                │  │
│  │  • pilot_briefing.txt - Pilot briefing document                                                                                 │  │
│  │  • temp/routes_with_added_interpolated_points.json - With departure metadata                                                      │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    END                                                                                                │
│                                                                                                                                    │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    PERFORMANCE METRICS                                                                             │  │
│  │  • Total Processing Time: 0.4 seconds                                                                                            │  │
│  │  • Files Processed: 16 XML files                                                                                                 │  │
│  │  • Conflicts Detected: Filtered by altitude > 5000 ft                                                                            │  │
│  │  • Output Files Generated: 6+ files                                                                                              │  │
│  │  • Error Rate: 0% (after Unicode cleanup)                                                                                        │  │
│  │  • Circular Dependencies: Eliminated                                                                                             │  │
│  │  • Data Structure: Simplified (no x/y fields)                                                                                    │  │
│  └─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

## Key Improvements in Data Flow

### Before (Circular Dependency):
```
Scheduling ←→ Animation Generation
     ↓              ↓
pilot_briefing.txt  animation_data.json
```

### After (Linear Flow):
```
Conflict Analysis → Scheduling → Animation Generation
       ↓              ↓              ↓
potential_conflict_data.json → routes_with_metadata.json → animation_data.json
```

## Decision Points and Quality Gates

### Quality Gates at Each Step:

1. **Prerequisites Check**
   - ✅ 16 XML files present
   - ✅ All scripts exist
   - ✅ Directories created

2. **XML Extraction**
   - ✅ All XML files parsed successfully
   - ✅ Waypoint data extracted
   - ✅ KML files generated

3. **Conflict Analysis**
   - ✅ Conflicts detected using thresholds
   - ✅ Altitude filtering applied (>5000 ft)
   - ✅ Reports generated

4. **KML Merge**
   - ✅ Individual KML files found
   - ✅ Files merged successfully
   - ✅ Conflict markers added

5. **Scheduling & Metadata**
   - ✅ Departure times calculated
   - ✅ Metadata added to interpolated points
   - ✅ No circular dependency with animation

6. **Animation Generation**
   - ✅ Metadata-based schedule loading
   - ✅ Simplified data structure (no x/y fields)
   - ✅ Linear data flow maintained

7. **Data Audit**
   - ✅ All data sources compared
   - ✅ Time values rounded to zero decimals
   - ✅ Markdown audit report generated

### Error Handling:
- Unicode/emoji characters removed from all scripts
- File existence checks at each step
- Graceful failure handling with error messages
- Logging of all operations with timestamps
- Metadata fallback when missing

### Success Criteria:
- Complete workflow execution without errors
- All output files generated with correct data
- Frontend visualization ready for use
- **Linear data flow maintained**
- **No circular dependencies**
- **Simplified data structures** 