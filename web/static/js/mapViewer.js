// Map Viewer - Handles embedded Cesium animation
class MapViewer {
    constructor() {
        this.mapContainer = document.getElementById('mapContainer');
        this.mapLoading = document.getElementById('mapLoading');
        this.cesiumIframe = null;
        
        this.initializeMap();
    }
    
    initializeMap() {
        // Create iframe to embed the status bar development animation
        this.cesiumIframe = document.createElement('iframe');
        this.cesiumIframe.src = '/animation/status_bar_development.html';
        this.cesiumIframe.style.width = '100%';
        this.cesiumIframe.style.height = '100%';
        this.cesiumIframe.style.border = 'none';
        this.cesiumIframe.id = 'cesiumIframe';
        
        // Hide loading indicator when iframe loads
        this.cesiumIframe.onload = () => {
            this.mapLoading.style.display = 'none';
            console.log('Cesium map loaded successfully');
        };
        
        // Show loading indicator initially
        this.mapLoading.style.display = 'block';
        
        // Add iframe to container
        this.mapContainer.appendChild(this.cesiumIframe);
        
        // Handle iframe load errors
        this.cesiumIframe.onerror = () => {
            this.showMapError('Failed to load 3D map');
        };
    }
    
    refreshMap() {
        if (this.cesiumIframe) {
            // Reload the iframe to refresh the status bar animation with new data
            this.mapLoading.style.display = 'block';
            this.cesiumIframe.src = this.cesiumIframe.src;
            
            // Hide loading after a delay to allow map to load
            setTimeout(() => {
                this.mapLoading.style.display = 'none';
            }, 2000);
        }
    }
    
    showMapError(message) {
        this.mapLoading.innerHTML = `
            <div style="color: #dc3545; text-align: center;">
                <p>❌ ${message}</p>
                <button onclick="mapViewer.refreshMap()" style="margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    Retry
                </button>
            </div>
        `;
        this.mapLoading.style.display = 'block';
    }
    
    // Method to communicate with the embedded Cesium viewer
    sendMessageToMap(message) {
        if (this.cesiumIframe && this.cesiumIframe.contentWindow) {
            this.cesiumIframe.contentWindow.postMessage(message, '*');
        }
    }
    
    // Method to check if map is ready
    isMapReady() {
        return this.cesiumIframe && this.cesiumIframe.contentWindow;
    }
    
    // Method to get map container dimensions
    getMapDimensions() {
        const rect = this.mapContainer.getBoundingClientRect();
        return {
            width: rect.width,
            height: rect.height
        };
    }
} 