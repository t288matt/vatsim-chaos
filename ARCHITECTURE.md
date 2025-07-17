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

The ATC Conflict Generation System is a comprehensive Python-based application designed to analyze SimBrief XML flight plans and generate realistic air traffic control conflicts. The system consists of a Flask web backend and a modern vanilla JavaScript frontend that provides an intuitive interface for file management, processing, and 3D visualization.

### **Key Features**
- **XML Flight Plan Processing**: Parses SimBrief XML files to extract flight data
- **3D Conflict Analysis**: Identifies potential conflicts in 3D space
- **Schedule Generation**: Creates departure schedules to resolve conflicts
- **Web Interface**: Modern, responsive UI with drag-and-drop file upload
- **3D Visualization**: Cesium-based 3D map with real-time animation
- **Pilot Briefing**: Comprehensive analysis results with export capabilities

### **Technology Stack**
- **Backend**: Python 3.13, Flask, XML processing libraries
- **Frontend**: Vanilla HTML5/CSS3/ES6+ JavaScript
- **3D Visualization**: Cesium.js embedded iframe
- **Containerization**: Docker with multi-stage builds
- **Deployment**: GitHub Actions with automated builds

---

## Core Architecture Principles

### **1. Single Source of Truth**
- All flight data originates from SimBrief XML files
- Centralized data processing pipeline ensures consistency
- Shared data structures across all components

### **2. Modular Design**
- **Backend Modules**: Independent Python scripts for specific tasks
- **Frontend Components**: Separate JavaScript classes for each major feature
- **Clear Interfaces**: Well-defined APIs between components

### **3. Data-Driven Approach**
- Configuration through environment variables
- JSON-based data exchange between components
- Structured logging for debugging and monitoring

### **4. Progressive Enhancement**
- Core functionality works without JavaScript
- Responsive design adapts to all screen sizes
- Accessibility-first design principles

---

## System Components

### **Backend Components**

#### **1. Core Processing Scripts**
- **`execute.py`**: Main orchestration script for the complete workflow
- **`extract_simbrief_xml_flightplan.py`**: XML parsing and flight data extraction
- **`find_potential_conflicts.py`**: 3D spatial conflict detection
- **`merge_kml_flightplans.py`**: KML file generation for visualization
- **`generate_schedule_conflicts.py`**: Departure schedule generation
- **`generate_animation.py`**: 3D animation data creation
- **`audit_conflict.py`**: Data integrity verification

#### **2. Web Interface (`web/`)**
- **`app.py`**: Flask web server with REST API endpoints
- **`config.py`**: Application configuration management
- **Static Assets**: CSS, JavaScript, and template files

#### **3. Shared Components**
- **`shared_types.py`**: Common data structures and type definitions
- **`env.py`**: Environment variable management
- **`airports.json`**: Airport database for validation

### **Frontend Components**

#### **1. File Manager (`fileManager.js`)**
**Purpose**: Handles all file-related operations including upload, validation, selection, and management.

**Key Features**:
- **Drag-and-Drop Upload**: HTML5 File API with visual feedback
- **File Validation**: Client-side and server-side XML validation with retry logic
- **Library Management**: Persistent file storage with metadata
- **Selection Interface**: Multi-select with checkbox controls
- **Progress Tracking**: Real-time upload progress indicators
- **Duplicate Detection**: Identifies and marks duplicate routes
- **Error Handling**: Comprehensive error recovery and user feedback

**Technical Implementation**:
```javascript
class FileManager {
  constructor() {
    this.files = [];
    this.selectedFiles = new Set();
    this.fileValidationCache = new Map();
    this.uploadQueue = [];
    this.isUploading = false;
  }
  
  async uploadFiles(files) {
    // Handle file upload with validation and retry logic
  }
  
  async validateFileWithRetry(filename, maxRetries = 3) {
    // Server-side XML validation with exponential backoff
  }
  
  renderFileList() {
    // Dynamic file list with validation status indicators
  }
}
```

#### **2. Processing Engine (`processor.js`)**
**Purpose**: Manages the complete analysis workflow execution with progress tracking and error handling.

**Key Features**:
- **Workflow Orchestration**: Executes execute.py pipeline
- **Progress Tracking**: Real-time step-by-step progress with timeout handling
- **Error Handling**: Comprehensive error recovery and retry logic
- **Status Updates**: Live processing status display
- **Prerequisites Validation**: Checks for duplicate routes, file validity
- **Timeout Management**: Handles long-running processes gracefully

**Technical Implementation**:
```javascript
class Processor {
  constructor() {
    this.isProcessing = false;
    this.statusCheckInterval = null;
    this.processingStartTime = null;
    this.maxProcessingTime = 300000; // 5 minutes
    this.retryCount = 0;
    this.maxRetries = 3;
  }
  
  async validateProcessingPrerequisites(selectedFiles) {
    // Check for duplicate routes, file validity, size limits
  }
  
  async monitorProgress() {
    // Real-time progress monitoring with exponential backoff
  }
}
```

#### **3. Map Viewer (`mapViewer.js`)**
**Purpose**: Provides 3D visualization of flight paths, conflicts, and real-time animation using Cesium.

**Key Features**:
- **Cesium Integration**: Embedded 3D globe with flight visualization
- **Real-time Animation**: Aircraft movement with altitude labels
- **Conflict Visualization**: Highlighted conflict points
- **Timeline Controls**: Play/pause/seek functionality
- **Camera Controls**: Zoom, pan, and rotation
- **Error Recovery**: Retry mechanisms for map loading failures

**Technical Implementation**:
```javascript
class MapViewer {
  constructor() {
    this.mapContainer = document.getElementById('mapContainer');
    this.cesiumIframe = null;
  }
  
  initializeMap() {
    // Create iframe to embed Cesium animation
    this.cesiumIframe = document.createElement('iframe');
    this.cesiumIframe.src = '/animation/status_bar_development.html';
  }
  
  refreshMap() {
    // Reload iframe to refresh animation with new data
  }
}
```

#### **4. Application Controller (`app.js`)**
**Purpose**: Main application coordinator and briefing management.

**Key Features**:
- **Component Coordination**: Manages all frontend components
- **Briefing Management**: Modal popup with export capabilities
- **Global Event Handling**: Keyboard shortcuts and accessibility
- **Error Reporting**: Centralized error handling and user feedback

**Technical Implementation**:
```javascript
class App {
  constructor() {
    this.fileManager = new FileManager();
    this.processor = new Processor();
    this.mapViewer = new MapViewer();
    this.briefingManager = new BriefingManager();
  }
}

class BriefingManager {
  async showBriefing() {
    // Fetch and display briefing content in modal
  }
  
  printBriefing() {
    // Print-friendly formatting
  }
  
  downloadBriefing() {
    // Download as text file
  }
}
```

---

## Data Flow Architecture

### **Complete System Data Flow**
```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Client                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   File Manager  │  │         Map Viewer              │  │
│  │   (Left Panel)  │  │      (Right Panel)             │  │
│  │                 │  │                                 │  │
│  │ • Upload Area   │  │ • Cesium 3D Map                │  │
│  │ • File Library  │  │ • Flight Visualization         │  │
│  │ • Process Btn   │  │ • Conflict Markers             │  │
│  │ • Briefing Btn  │  │ • Timeline Controls            │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Backend API                       │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   File Upload   │  │      Processing Engine          │  │
│  │   & Validation  │  │                                 │  │
│  │                 │  │ • execute.py workflow          │  │
│  │ • XML Validation│  │ • Conflict Analysis            │  │
│  │ • Size Limits   │  │ • Schedule Generation          │  │
│  │ • Duplicate Chk │  │ • Animation Export             │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    File System Storage                     │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────────────────────┐  │
│  │   Uploads Dir   │  │      Results Directory          │  │
│  │                 │  │                                 │  │
│  │ • XML Files     │  │ • animation_data.json          │  │
│  │ • Temp Storage  │  │ • conflict_points.json         │  │
│  │ • Metadata      │  │ • pilot_briefing.txt           │  │
│  └─────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### **Request-Response Flow**
```
1. User Upload → FileManager.uploadFiles()
   ↓
2. Server Validation → Flask API /upload
   ↓
3. File Storage → File System (uploads/)
   ↓
4. User Selection → FileManager.getSelectedFiles()
   ↓
5. Processing Request → ProcessingEngine.executeWorkflow()
   ↓
6. Backend Execution → execute.py pipeline
   ↓
7. Result Generation → animation_data.json, conflict_points.json
   ↓
8. Frontend Update → MapViewer.loadAnimationData()
   ↓
9. Display Results → Pilot Briefing Modal
```

### **Real-time Updates**
```
Processing Engine → WebSocket/SSE → UI Components
     ↓                    ↓              ↓
execute.py → Progress Events → Progress Indicators
     ↓                    ↓              ↓
File System → Change Events → Map & Briefing Updates
```

---

## Configuration & Environment

### **Environment Variables**
- **`UPLOAD_FOLDER`**: Directory for uploaded XML files
- **`MAX_CONTENT_LENGTH`**: Maximum file upload size (16MB)
- **`FLASK_ENV`**: Development/production environment
- **`DEBUG`**: Enable debug logging and error details

### **File Structure**
```
Chaos2/
├── web/                    # Web interface
│   ├── app.py             # Flask application
│   ├── config.py          # Configuration management
│   ├── static/            # Static assets
│   │   ├── css/main.css   # Styling (VATSIM-inspired)
│   │   └── js/            # JavaScript modules
│   │       ├── app.js     # Main application controller
│   │       ├── fileManager.js  # File management
│   │       ├── processor.js    # Processing engine
│   │       └── mapViewer.js    # Map visualization
│   └── templates/         # HTML templates
│       └── index.html     # Main interface
├── animation/             # 3D visualization
│   ├── animation.html     # Cesium animation
│   └── status_bar_development.html  # Enhanced animation
├── logs/                  # Application logs
├── temp/                  # Temporary processing files
└── xml_files/            # Uploaded XML files
```

---

## Web Interface Architecture

### **Design Philosophy**
- **VATSIM-Inspired UI**: Professional ATC-style interface
- **Responsive Design**: Adapts to desktop, tablet, and mobile
- **Accessibility First**: WCAG 2.1 AA compliance
- **Performance Optimised**: Fast loading and smooth interactions
- **Progressive Enhancement**: Core functionality works without JavaScript

### **Technology Stack Decisions**
- **Vanilla Web Technologies**: HTML5, CSS3, ES6+ JavaScript
- **No Frameworks**: Eliminates dependency management overhead
- **Direct DOM Manipulation**: Simple, debuggable, lightweight
- **Universal Browser Support**: Works across all modern browsers
- **Flask Backend**: Lightweight Python web framework for API

### **UI Components**

#### **1. Header Section**
- **Title**: "🎯 Flight Conflict Generation"
- **Styling**: VATSIM-inspired gradient background with cyan accents
- **Responsive**: Adapts to different screen sizes

#### **2. Left Panel (File Management)**
- **Upload Area**: Drag-and-drop interface with visual feedback
- **Time Controls**: Start/end time inputs for event scheduling
- **File Library**: Persistent file storage with validation status
- **Selection Controls**: Select all/none, delete all functionality
- **Processing Controls**: Generate schedule and briefing buttons
- **Progress Section**: Real-time processing status display

#### **3. Right Panel (3D Visualization)**
- **Map Container**: Embedded Cesium iframe
- **Loading States**: Visual feedback during map loading
- **Error Handling**: Retry mechanisms for map failures
- **Responsive**: Adapts to different screen sizes

#### **4. Modal Components**
- **Pilot Briefing**: Comprehensive analysis results
- **Export Options**: Print and download functionality
- **Keyboard Navigation**: Escape key to close
- **Accessibility**: Screen reader friendly

### **Styling Architecture**
- **VATSIM-Inspired Design**: Professional ATC interface colors
- **CSS Custom Properties**: Consistent theming
- **Responsive Breakpoints**: Mobile-first design
- **Animation**: Smooth transitions and hover effects
- **Accessibility**: High contrast and keyboard navigation

### **JavaScript Architecture**
- **Modular Design**: Separate classes for each major feature
- **Event-Driven**: Clean separation of concerns
- **Error Handling**: Comprehensive error recovery
- **Performance**: Efficient DOM manipulation
- **Maintainability**: Clear code structure and documentation

---

## Animation & Visualization

### **Cesium Integration**
- **3D Globe**: Interactive 3D map with flight visualization
- **Real-time Animation**: Aircraft movement with altitude labels
- **Conflict Markers**: Highlighted conflict points
- **Timeline Controls**: Play/pause/seek functionality
- **Camera Controls**: Zoom, pan, and rotation

### **Animation Data Structure**
```json
{
  "flights": [
    {
      "id": "flight_1",
      "waypoints": [
        {"lat": -33.946, "lon": 151.177, "alt": 21, "time": "08:00"},
        {"lat": -35.165, "lon": 147.466, "alt": 724, "time": "08:45"}
      ],
      "conflicts": [{"lat": -34.555, "lon": 149.333, "time": "08:30"}]
    }
  ],
  "conflicts": [
    {
      "location": {"lat": -34.555, "lon": 149.333},
      "time": "08:30",
      "severity": "high",
      "aircraft": ["flight_1", "flight_2"]
    }
  ]
}
```

### **Visualization Features**
- **Flight Paths**: 3D polylines with altitude information
- **Conflict Markers**: Red spheres at conflict locations
- **Time Slider**: Interactive timeline for animation control
- **Altitude Labels**: Real-time altitude display
- **Camera Tracking**: Automatic camera positioning

---

## Deployment & Containerization

### **Docker Configuration**
- **Multi-stage Build**: Optimized for production
- **Python 3.13**: Latest Python version
- **Flask Development Server**: For development
- **Production Ready**: Gunicorn for production deployment

### **GitHub Actions**
- **Automated Builds**: On every push and pull request
- **Docker Image**: Published to GitHub Container Registry
- **Dependabot Integration**: Automated dependency updates
- **Quality Checks**: Linting and testing

### **Environment Management**
- **Development**: Local Flask development server
- **Production**: Docker container with Gunicorn
- **Configuration**: Environment variables for flexibility
- **Logging**: Structured logging for monitoring

---

## Development Workflow

### **Local Development**
1. **Clone Repository**: `git clone https://github.com/t288matt/vatsim-chaos.git`
2. **Install Dependencies**: `pip install -r web/requirements.txt`
3. **Set Environment**: Configure `.env` file
4. **Run Development Server**: `cd web && python app.py`
5. **Access Application**: Open `http://localhost:5000`

### **Testing Workflow**
1. **Upload XML Files**: Drag-and-drop SimBrief XML files
2. **Validate Files**: Automatic validation with retry logic
3. **Select Files**: Choose files for processing
4. **Set Time Range**: Configure start/end times
5. **Generate Schedule**: Execute conflict analysis
6. **View Results**: 3D visualization and pilot briefing

### **Code Organization**
- **Backend**: Python scripts in root directory
- **Frontend**: Web interface in `web/` directory
- **Documentation**: Comprehensive architecture and user guides
- **Configuration**: Environment-based configuration

### **Quality Assurance**
- **Error Handling**: Comprehensive error recovery
- **Input Validation**: Client-side and server-side validation
- **Performance**: Optimized for large file processing
- **Accessibility**: WCAG 2.1 AA compliance
- **Security**: File upload validation and sanitization

---

## Recent Enhancements

### **Frontend Improvements (2025)**
- **Enhanced File Management**: Better validation, retry logic, duplicate detection
- **Improved Processing**: Better error handling, timeout management, progress tracking
- **Time Controls**: Added start/end time inputs for event scheduling
- **Better UI/UX**: Enhanced styling, responsive design, accessibility improvements
- **Map Integration**: Embedded Cesium iframe for 3D visualization

### **Backend Enhancements**
- **Dependabot Integration**: Automated dependency updates
- **Docker Optimization**: Multi-stage builds for production
- **Error Handling**: Comprehensive error recovery and logging
- **Performance**: Optimized file processing and validation

### **Architecture Improvements**
- **Modular Design**: Clear separation of concerns
- **API Design**: RESTful endpoints with proper error handling
- **Data Flow**: Streamlined data processing pipeline
- **Documentation**: Comprehensive architecture and user guides

---

This architecture provides a solid foundation for the ATC Conflict Generation System, with clear separation of concerns, comprehensive error handling, and a modern, responsive user interface that meets the needs of air traffic control professionals.