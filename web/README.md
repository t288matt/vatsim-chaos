# ATC Conflict Generation System - Web Interface

## Overview

This web interface provides a browser-based user interface for the ATC Conflict Generation System, allowing users to upload XML files, process conflicts, and view results in an interactive 3D map.

## Features

### 🎯 Core Functionality
- **File Upload**: Drag-and-drop XML file upload with validation
- **File Library**: Manage uploaded files with checkbox selection
- **Processing**: Execute the complete analysis workflow with progress tracking
- **3D Visualization**: Embedded Cesium map showing flight paths and conflicts
- **Pilot Briefing**: Modal popup with formatted briefing content

### 🎨 User Interface
- **Modern Design**: Clean, responsive interface with gradient backgrounds
- **Real-time Feedback**: Progress indicators and status messages
- **Error Handling**: Comprehensive error handling with user-friendly messages
- **Responsive Layout**: Works on desktop, tablet, and mobile devices

## Installation

### Prerequisites
- Python 3.7+
- Flask web framework
- Existing ATC Conflict Generation System scripts

### Setup
1. **Install Dependencies**:
   ```bash
   cd web
   pip install -r requirements.txt
   ```

2. **Start the Web Server**:
   ```bash
   python app.py
   ```

3. **Access the Interface**:
   Open your browser and navigate to `http://localhost:5000`

## Usage

### 1. Upload Files
- **Drag and Drop**: Drag XML files directly into the upload area
- **File Browser**: Click the upload area to browse and select files
- **Validation**: Only XML files are accepted

### 2. Select Files for Processing
- **Checkbox Selection**: Use checkboxes to select files from the library
- **Quick Selection**: Use "Select All" or "Select None" buttons
- **Selection Summary**: See how many files are selected

### 3. Process Analysis
- **Start Processing**: Click the "Process Analysis" button
- **Progress Tracking**: Watch real-time progress through 6 processing steps
- **Status Updates**: Get notifications when processing completes or fails

### 4. View Results
- **3D Map**: View flight paths and conflicts in the embedded Cesium viewer
- **Pilot Briefing**: Click "Pilot Briefing" to view formatted results
- **Print/Download**: Export briefing content as text file

## Architecture

### File Structure
```
web/
├── app.py                 # Flask backend application
├── requirements.txt       # Python dependencies
├── README.md             # This documentation
├── static/
│   ├── css/
│   │   └── main.css      # Styling and layout
│   ├── js/
│   │   ├── app.js        # Main application controller
│   │   ├── fileManager.js # File upload and management
│   │   ├── processor.js  # Analysis workflow handling
│   │   └── mapViewer.js  # Cesium map integration
│   └── uploads/          # XML file storage
└── templates/
    └── index.html        # Main HTML template
```

### Technology Stack
- **Backend**: Flask (Python)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Map**: Embedded Cesium viewer (existing animation.html)
- **File Storage**: Local file system

### API Endpoints
- `GET /` - Main interface
- `POST /upload` - File upload
- `GET /files` - List uploaded files
- `POST /process` - Start analysis workflow
- `GET /status` - Get processing status
- `GET /briefing` - Get pilot briefing content
- `GET /animation/<filename>` - Serve animation files
- `GET /temp/<filename>` - Serve temporary files

## Development

### Running in Development Mode
```bash
cd web
python app.py
```

The server will start on `http://localhost:5000` with debug mode enabled.

### File Processing Flow
1. **Upload**: Files stored in `static/uploads/`
2. **Processing**: Files copied to parent directory for script execution
3. **Results**: Generated files accessible via Flask routes
4. **Map**: Cesium viewer loads data from processed results

### Customization

#### Styling
Edit `static/css/main.css` to modify the appearance:
- Color schemes
- Layout dimensions
- Responsive breakpoints
- Animation effects

#### Functionality
Modify JavaScript files in `static/js/`:
- `app.js`: Global application logic
- `fileManager.js`: File upload and management
- `processor.js`: Analysis workflow
- `mapViewer.js`: Map integration

#### Backend
Edit `app.py` to modify:
- API endpoints
- File processing logic
- Error handling
- Configuration settings

## Troubleshooting

### Common Issues

#### File Upload Fails
- Check file size (max 16MB)
- Ensure files are valid XML format
- Verify upload directory permissions

#### Processing Fails
- Check that Python scripts exist in parent directory
- Verify file permissions for script execution
- Check console logs for detailed error messages

#### Map Doesn't Load
- Ensure animation.html exists in parent directory
- Check browser console for JavaScript errors
- Verify Cesium library is accessible

#### Port Already in Use
- Change port in `app.py`: `app.run(port=5001)`
- Or kill existing process using port 5000

### Debug Mode
Enable debug mode for detailed error messages:
```python
app.run(debug=True, host='0.0.0.0', port=5000)
```

## Security Considerations

### File Upload Security
- File type validation (XML only)
- File size limits (16MB max)
- Secure filename handling
- Path traversal protection

### Data Protection
- Input sanitization
- Output encoding
- Session management
- Error information protection

## Performance

### Optimization Tips
- **File Uploads**: Large files processed in chunks
- **Map Loading**: Lazy loading of Cesium viewer
- **Processing**: Background thread execution
- **Caching**: Browser caching for static assets

### Performance Targets
- **Page Load**: < 3 seconds
- **File Upload**: < 30 seconds for 10MB file
- **Processing**: < 5 minutes for typical workload
- **Map Loading**: < 10 seconds for processed data

## Future Enhancements

### Planned Features
- **User Accounts**: Multi-user support with authentication
- **Project Management**: Save and load different analysis projects
- **Export Options**: Export results in various formats
- **Advanced Visualization**: Additional map layers and controls
- **Real-time Collaboration**: Multiple users working on same analysis

### Docker Integration
- **Containerization**: Package entire application in Docker
- **Volume Management**: Persistent storage for uploaded files
- **Port Configuration**: Expose necessary ports for web access
- **Environment Variables**: Configurable settings for deployment

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review console logs for error messages
3. Verify all dependencies are installed
4. Ensure proper file permissions

## License

This web interface is part of the ATC Conflict Generation System and follows the same licensing terms as the main project. 