# ATC Conflict Generation System - Architecture Document

## Table of Contents

1. [System Overview](#system-overview)
2. [Core Architecture Principles](#core-architecture-principles)
3. [System Components](#system-components)
4. [Data Flow Architecture](#data-flow-architecture)
5. [Configuration & Environment](#configuration--environment)
6. [Web Interface Architecture](#web-interface-architecture)
7. [Animation & Visualization](#animation--visualization)
8. [Deployment & Containerization](#deployment--containerization)
9. [Development Workflow](#development-workflow)

---

## System Overview

The ATC Conflict Generation System is a comprehensive Python-based application designed to analyze SimBrief XML flight plans and generate challenging air traffic control scenarios for VATSIM events. The system processes multiple flight plans simultaneously, detects 3D spatial conflicts, optimizes departure schedules, and provides both detailed reports and interactive visualizations.

### Key Features

- **Dual Interface Support**: Command-line scripts for batch processing and web interface for interactive workflows
- **First Conflict Detection**: Tracks only the initial conflict between aircraft pairs for ATC intervention planning
- **Flight ID System**: Uses unique flight IDs (FLT0001, FLT0002, etc.) for better conflict tracking
- **Single Source of Truth**: One comprehensive JSON file contains all flight data, conflicts, and scheduling
- **Real-time Visualization**: Interactive 3D web visualization with CesiumJS
- **Automated Dependency Management**: Dependabot integration for package updates

### System Purpose

The system helps VATSIM event organizers create challenging scenarios by:
1. **Conflict Analysis**: Identifying realistic air traffic conflicts
2. **Schedule Optimization**: Maximizing conflict opportunities while respecting separation rules
3. **Visualization**: Providing interactive 3D views of aircraft movements
4. **Documentation**: Generating pilot briefings and conflict reports

---

## Core Architecture Principles

### 1. Single Source of Truth
- **Foundation File**: `temp/routes_with_added_interpolated_points.json` contains all flight data
- **Interpolated Routes**: Additional points between waypoints for accurate conflict detection
- **Metadata Approach**: Departure schedules and conflict data stored as metadata
- **No Circular Dependencies**: Linear data flow eliminates complex interdependencies

### 2. Modular Design
- **Clear Separation**: Data extraction, analysis, scheduling, and visualization are separate modules
- **Single Responsibility**: Each component has a focused, well-defined purpose
- **Shared Types**: `shared_types.py` provides unified class definitions across modules
- **Configuration Centralization**: `env.py` contains all configurable parameters

### 3. Data-Driven Architecture
- **JSON-Based Exchange**: All components communicate via structured JSON data
- **Structured Outputs**: Consistent data formats for downstream processing
- **Validation Layers**: Multiple validation points ensure data integrity
- **Audit Capabilities**: Comprehensive data verification and reporting

### 4. Event-Focused Design
- **First Conflict Priority**: Tracks only initial conflicts between aircraft pairs
- **Separation Rules**: Enforces departure and route separation requirements
- **Schedule Optimization**: Balances conflict maximization with realistic timing
- **Pilot Briefing**: Generates comprehensive event documentation

---

## System Components

### Core Processing Scripts

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `execute.py` | Master orchestration script | None | Orchestrates workflow |
| `extract_simbrief_xml_flightplan.py` | XML parsing and data extraction | `*.xml` files | `temp/*_data.json`, `temp/*.kml` |
| `find_potential_conflicts.py` | Conflict detection and route interpolation | XML files, JSON data | `temp/potential_conflict_data.json`, `temp/routes_with_added_interpolated_points.json` |
| `generate_schedule_conflicts.py` | Schedule optimization and briefing generation | Conflict data, interpolated routes | `pilot_briefing.txt`, updated routes file |
| `generate_animation.py` | Animation data preparation | Interpolated routes | `animation/animation_data.json`, `animation/conflict_points.json` |
| `merge_kml_flightplans.py` | KML file merging | Individual KML files | `merged_flightplans.kml` |
| `audit_conflict.py` | Data integrity verification | All data files | `audit_conflict_output.txt` |

### 1. Data Extraction Layer (`extract_simbrief_xml_flightplan.py`)

**Responsibilities**:
- Parse SimBrief XML flight plan files
- Extract waypoints, coordinates, altitudes, and timing
- Convert to structured data formats (JSON/KML)
- Handle XML parsing errors gracefully
- Generate individual KML files for visualization

**Key Classes** (from `shared_types.py`):
- `FlightPlan`: Complete flight plan with origin, destination, and waypoints
- `Waypoint`: Individual navigation points with coordinates, altitude, and timing

**Outputs**:
- Individual KML files for each flight plan
- JSON data files for structured analysis
- 40-colour visualization scheme for route identification

### 2. Conflict Analysis Engine (`find_potential_conflicts.py`)

**Responsibilities**:
- Perform 3D spatial conflict detection
- Analyze both waypoint and enroute conflicts
- Optimize departure times for maximum conflicts
- Generate comprehensive conflict scenarios
- **Identify and track only first conflicts between aircraft pairs**
- **Create the single source of truth foundation with interpolated routes**

**Core Algorithms**:
- **Distance Calculation**: Haversine formula for lateral separation
- **Route Interpolation**: Configurable spacing (default 1.5nm) between waypoints
- **Phase Detection**: TOC/TOD-based climb/cruise/descent determination
- **Conflict Filtering**: Altitude thresholds and duplicate detection
- **First Conflict Detection**: Tracks earliest conflict between each aircraft pair

**Conflict Criteria**:
- Lateral separation < 3 nautical miles
- Vertical separation < 900 feet
- Aircraft altitude > 5000 feet
- Duplicate filtering within 4 NM
- **First conflict only**: Only the earliest conflict between aircraft pairs is reported

### 3. Scheduling & Briefing Layer (`generate_schedule_conflicts.py`)

**Responsibilities**:
- Read conflict analysis data and respect intended scheduling
- Sort flights by intended departure time (earliest first)
- Schedule flights at their intended times instead of forcing "most conflicts" flight to depart first
- Add departure schedule metadata to interpolated points file
- Output pilot_briefing.txt (authoritative, includes schedule and conflicts)

**Key Features**:
- **Fixed Scheduling Algorithm**: Uses conflict analysis departure times instead of "most conflicts" rule
- **Eliminated Circular Dependency**: No longer depends on animation_data.json
- **Metadata Approach**: Adds departure schedule to `temp/routes_with_added_interpolated_points.json`
- **Direct Interpolation**: Uses interpolated points file for conflict position calculations

**Separation Rules**:
- **Departure Separation**: Minimum 2 minutes between departures from the same airport
- **Same Route Separation**: Minimum 5 minutes between flights with identical origin-destination

### 4. Animation Data Export Layer (`generate_animation.py`)

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

**Dynamic Camera Positioning**:
- **Global Coverage**: Works for any flight routes worldwide
- **Automatic Calculation**: Analyses all departure and arrival airports from flight data
- **90% Coverage**: Ensures airports are well within the view with 10% padding
- **Adaptive Zoom**: Automatically adjusts zoom level based on airport distances
- **Minimum View Size**: Prevents excessive zoom for very close airports

### 6. Data Audit Layer (`audit_conflict.py`)

**Responsibilities**:
- Verify data integrity across all system components
- Cross-reference conflict data with animation data
- Validate departure schedules and separation rules
- Generate comprehensive audit reports

---

## Data Flow Architecture

### Primary Data Flow

```
XML Files → extract_simbrief_xml_flightplan.py → temp/*_data.json
                                                           ↓
find_potential_conflicts.py → temp/routes_with_added_interpolated_points.json (SINGLE SOURCE OF TRUTH)
                                                           ↓
generate_schedule_conflicts.py → pilot_briefing.txt + updated routes file
                                                           ↓
generate_animation.py → animation/animation_data.json
                                                           ↓
Web Interface → Interactive Visualization
```

### Single Source of Truth: `temp/routes_with_added_interpolated_points.json`

**Why This File is Critical**:
1. **Route Interpolation**: The conflict detection algorithm needs to check for conflicts not just at waypoints, but also **between** waypoints. To do this accurately, it interpolates additional points along each route at regular intervals (every 1.5 nautical miles by default).

2. **Enhanced Conflict Detection**: By adding interpolated points, the system can detect conflicts that occur between the original waypoints, which is crucial for realistic ATC scenarios where aircraft don't just conflict at navigation points.

3. **Data Structure**: The interpolated points file contains:
   - Original waypoints from the flight plans
   - Additional interpolated points between waypoints
   - Each point has lat/lon/altitude/time data
   - This becomes the foundation for all downstream processing

4. **Single Source of Truth Foundation**: This file becomes the base that other scripts build upon. `generate_schedule_conflicts.py` then adds departure schedule metadata to it, and `generate_animation.py` reads from it.

### Data Dependencies

**Linear Flow**:
- No circular dependencies between components
- Each component builds upon the previous one
- Metadata approach eliminates complex interdependencies
- Clear separation between analysis and visualization

**Key Data Files**:
- `temp/*_data.json`: Individual flight data from XML parsing
- `temp/potential_conflict_data.json`: Conflict analysis results
- `temp/routes_with_added_interpolated_points.json`: **Single source of truth**
- `pilot_briefing.txt`: Final schedule and conflict documentation
- `animation/animation_data.json`: Web visualization data

---

## Configuration & Environment

### Environment Configuration (`env.py`)

**Conflict Detection Parameters**:
- `LATERAL_SEPARATION_THRESHOLD = 3.0` (nautical miles)
- `VERTICAL_SEPARATION_THRESHOLD = 900` (feet)
- `MIN_ALTITUDE_THRESHOLD = 5000` (feet)
- `NO_CONFLICT_AIRPORT_DISTANCES = ["YSSY/35", "YSCB/15"]`

**Scheduling Parameters**:
- `MIN_DEPARTURE_SEPARATION_MINUTES = 2`
- `MIN_SAME_ROUTE_SEPARATION_MINUTES = 5`
- `BATCH_SIZE = 1` (conflict score recalculation)
- `TIME_TOLERANCE_MINUTES = 2`
- `MAX_DEPARTURE_TIME_MINUTES = 120`

**Route Interpolation**:
- `INTERPOLATION_SPACING_NM = 1.5` (nautical miles between interpolated points)

**Display Configuration**:
- `TRANSITION_ALTITUDE_FT = 10500` (feet/flight level transition)

### Shared Types (`shared_types.py`)

**Unified Class Definitions**:
- `FlightPlan`: Complete flight plan with waypoints and metadata
- `Waypoint`: Navigation waypoint with coordinates and flight data

**Key Features**:
- Consistent behavior across all modules
- JSON serialization capabilities
- Time formatting for both standard and SimBrief formats
- Route identification and management

---

## Web Interface Architecture

### Directory Structure (`web/`)

```
web/
├── app.py                 # Flask backend server
├── config.py             # Web-specific configuration
├── requirements.txt      # Python dependencies
├── static/
│   ├── css/
│   │   └── main.css     # Styling and responsive design
│   └── js/
│       ├── app.js       # Main application logic
│       ├── fileManager.js # File upload and management
│       ├── processor.js  # Workflow execution
│       └── mapViewer.js # 3D visualization integration
└── templates/
    └── index.html       # Main web interface
```

### Backend Architecture (`web/app.py`)

**Flask Application**:
- REST API endpoints for file management and processing
- XML validation and duplicate route detection
- File upload handling and storage
- Processing workflow orchestration

**Key Endpoints**:
- `/validate-same-routes` (POST): Checks for duplicate origin-destination pairs
- `/validate/<filename>` (GET): Validates individual XML file structure
- `/files` (GET): Lists uploaded files with metadata
- `/process` (POST): Executes the complete analysis workflow
- `/delete-file/<filename>` (DELETE): Removes individual files
- `/delete-all-files` (DELETE): Removes all files from library

**Frontend-Backend Validation Architecture**:
- **Backend XML Parsing**: Uses `extract_simbrief_xml_flightplan.py` for consistent validation
- **Route Duplicate Detection**: Backend checks for same origin-destination pairs across files
- **Frontend Dependencies**: Frontend cannot parse XML independently due to browser limitations
- **Validation Flow**: Frontend → Backend API → XML parsing → Route analysis → Frontend display

### Frontend Architecture

**JavaScript Components**:

1. **File Manager** (`fileManager.js`):
   - Drag-and-drop file upload
   - File validation and duplicate detection
   - File library management with selection controls
   - DELETE ALL functionality with confirmation

2. **Processor** (`processor.js`):
   - Workflow execution and progress tracking
   - Real-time status updates
   - Error handling and recovery
   - Result file management

3. **Map Viewer** (`mapViewer.js`):
   - 3D visualization integration
   - Animation data loading
   - Interactive controls

4. **Main Application** (`app.js`):
   - Component initialization and coordination
   - Event handling and routing
   - User interface management

**User Experience Features**:
- **Visual Indicators**: Duplicate routes highlighted in file list
- **Warning Dialogs**: Detailed explanations of system limitations
- **Progress Tracking**: Real-time processing status updates
- **Error Recovery**: Automatic retry logic and graceful failure handling
- **Responsive Design**: Works on desktop and mobile devices

---

## Animation & Visualization

### Animation System (`animation/`)

**Files**:
- `animation.html`: Main 3D visualization interface
- `animation_data.json`: Complete flight data for visualization
- `conflict_points.json`: Conflict location data
- `status_bar_development.html`: Timeline and control interface

**CesiumJS Integration**:
- Real-time 3D aircraft animation
- Dynamic altitude labels and conflict alerts
- Timeline controls for playback control
- Camera auto-zoom and positioning
- Conflict point visualization

**Features**:
- **Simulation Speed Control**: -120x backward to +120x forward
- **Dynamic Camera Positioning**: Automatically calculates optimal view
- **Conflict Visualization**: Real-time conflict point display
- **Altitude Display**: Feet below transition altitude, flight levels above
- **Timeline Controls**: Playback, pause, speed adjustment

### KML Generation (`merge_kml_flightplans.py`)

**Purpose**:
- Merge individual KML files into single Google Earth file
- Provide static visualization option
- Enable offline route analysis

**Output**:
- `merged_flightplans.kml`: Complete route visualization for Google Earth

---

## Deployment & Containerization

### Docker Architecture

**Files**:
- `Dockerfile`: Container image definition
- `docker-compose.yml`: Multi-container orchestration
- `.dockerignore`: File exclusion rules
- `DOCKER_PLAN.md`: Detailed deployment documentation

**Container Features**:
- **Multi-stage Build**: Optimized image size
- **Volume Mounting**: Persistent data storage
- **Port Mapping**: Web interface accessibility
- **Environment Variables**: Configurable deployment

### GitHub Integration

**Automated Workflows**:
- **Dependabot**: Automated Python dependency updates
- **GitHub Actions**: Automated testing and deployment
- **Container Registry**: Automated Docker image builds

**Configuration** (`.github/dependabot.yml`):
- Weekly dependency monitoring
- Security-focused updates
- Automatic pull request generation
- Safe update strategy (minor/patch only)

---

## Development Workflow

### Development Environment

**Local Development**:
- Python 3.8+ environment
- Flask development server for web interface
- Direct script execution for testing
- Git version control with feature branches

**Testing Strategy**:
- Unit tests for core algorithms
- Integration tests for data flow
- End-to-end testing for complete workflows
- Manual testing for user interface

### Code Organization

**Modular Structure**:
- Clear separation of concerns
- Shared types for consistency
- Configuration centralization
- Comprehensive documentation

**Best Practices**:
- Type hints and documentation
- Error handling and logging
- Consistent code formatting
- Version control with meaningful commits

### Documentation

**Architecture Documents**:
- `ARCHITECTURE.md`: This comprehensive system overview
- `FRONTEND_ARCHITECTURE.md`: Detailed web interface documentation
- `USER_GUIDE.md`: End-user documentation
- `README.md`: Project overview and setup instructions

**Code Documentation**:
- Inline comments and docstrings
- Type hints for all functions
- Clear variable and function naming
- Comprehensive error messages

---

## System Integration

### External Dependencies

**Python Packages**:
- Flask: Web framework
- lxml: XML parsing
- numpy: Mathematical operations
- requests: HTTP client (if needed)

**Frontend Libraries**:
- CesiumJS: 3D visualization
- Modern JavaScript (ES6+)
- CSS3 for styling

### Data Formats

**Input Formats**:
- SimBrief XML flight plans
- Standard aviation data formats

**Output Formats**:
- JSON: Data exchange and storage
- KML: Google Earth visualization
- TXT: Human-readable reports
- HTML: Web visualization

### Performance Considerations

**Optimization Strategies**:
- Efficient conflict detection algorithms
- Batch processing for large datasets
- Caching for repeated calculations
- Lazy loading for visualization data

**Scalability**:
- Modular design supports component scaling
- Configurable parameters for performance tuning
- Memory-efficient data structures
- Asynchronous processing where appropriate

---

## Future Enhancements

### Planned Improvements

1. **Enhanced Conflict Detection**:
   - Weather integration
   - Airspace restrictions
   - More sophisticated separation rules

2. **Advanced Visualization**:
   - Real-time ATC radar simulation
   - Multi-viewport support
   - Enhanced conflict prediction

3. **Automation Features**:
   - Automated event generation
   - Conflict prediction algorithms
   - Integration with VATSIM APIs

4. **Performance Optimizations**:
   - Parallel processing for large datasets
   - GPU acceleration for visualization
   - Caching and optimization strategies

### Maintenance Strategy

**Regular Updates**:
- Dependabot for dependency management
- Security patches and bug fixes
- Feature enhancements and improvements
- Documentation updates

**Quality Assurance**:
- Automated testing workflows
- Code review processes
- Performance monitoring
- User feedback integration

---

*This architecture document provides a comprehensive overview of the ATC Conflict Generation System. For detailed implementation specifics, refer to the individual component documentation and source code.*