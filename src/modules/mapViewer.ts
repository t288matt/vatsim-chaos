// MapViewer — TypeScript reimplementation of web/static/js/mapViewer.js
// Handles the embedded Cesium animation iframe.
// NOTE: web/static/js/mapViewer.js is intentionally preserved; it is still
// loaded by web/templates/index.html until the HTML migration occurs.

import { bus } from './eventBus';

export class MapViewer {
    private mapContainer: HTMLElement | null;
    private mapLoading: HTMLElement | null;
    private cesiumIframe: HTMLIFrameElement | null;
    private _unsubscribeProcessingCompleted: (() => void) | null = null;

    constructor() {
        this.mapContainer  = document.getElementById('mapContainer');
        this.mapLoading    = document.getElementById('mapLoading');
        this.cesiumIframe  = null;

        this.initializeMap();

        // Refresh the map automatically when processing completes; store token for cleanup
        this._unsubscribeProcessingCompleted = bus.on('processing:completed', () => {
            this.refreshMap();
        });
    }

    private initializeMap(): void {
        // Create iframe to embed the Cesium animation
        this.cesiumIframe     = document.createElement('iframe');
        this.cesiumIframe.src = '/animation/status_bar_development.html';
        this.cesiumIframe.style.width  = '100%';
        this.cesiumIframe.style.height = '100%';
        this.cesiumIframe.style.border = 'none';
        this.cesiumIframe.id           = 'cesiumIframe';

        // Hide loading indicator once the iframe content has loaded
        this.cesiumIframe.onload = () => {
            if (this.mapLoading) this.mapLoading.style.display = 'none';
            console.log('Cesium map loaded successfully');
        };

        // Show loading indicator initially
        if (this.mapLoading) this.mapLoading.style.display = 'block';

        this.mapContainer?.appendChild(this.cesiumIframe);

        // Handle iframe load errors
        this.cesiumIframe.onerror = () => {
            this.showMapError('Failed to load 3D map');
        };
    }

    refreshMap(): void {
        if (this.cesiumIframe) {
            // Reload the iframe to pick up freshly written animation data
            if (this.mapLoading) this.mapLoading.style.display = 'block';
            this.cesiumIframe.src = this.cesiumIframe.src;

            // Hide loading after a short delay to allow the map to load
            setTimeout(() => {
                if (this.mapLoading) this.mapLoading.style.display = 'none';
            }, 2000);
        }
    }

    showMapError(message: string): void {
        if (!this.mapLoading) return;

        // Clear existing content safely — avoids innerHTML XSS risk
        while (this.mapLoading.firstChild) {
            this.mapLoading.removeChild(this.mapLoading.firstChild);
        }

        const wrapper = document.createElement('div');
        wrapper.style.color = '#dc3545';
        wrapper.style.textAlign = 'center';

        const p = document.createElement('p');
        p.textContent = '❌ ' + message;
        wrapper.appendChild(p);

        const retryBtn = document.createElement('button');
        retryBtn.textContent = 'Retry';
        retryBtn.style.cssText = 'margin-top: 10px; padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;';
        retryBtn.addEventListener('click', () => this.refreshMap());
        wrapper.appendChild(retryBtn);

        this.mapLoading.appendChild(wrapper);
        this.mapLoading.style.display = 'block';
    }

    /** Send a postMessage to the embedded Cesium viewer. */
    sendMessageToMap(message: unknown): void {
        if (this.cesiumIframe?.contentWindow) {
            this.cesiumIframe.contentWindow.postMessage(message, '*');
        }
    }

    /** Returns true when the iframe's contentWindow is accessible. */
    isMapReady(): boolean {
        return !!(this.cesiumIframe?.contentWindow);
    }

    /** Returns the pixel dimensions of the map container element. */
    getMapDimensions(): { width: number; height: number } {
        const rect = this.mapContainer?.getBoundingClientRect() ?? { width: 0, height: 0 };
        return { width: rect.width, height: rect.height };
    }

    /** Unsubscribe from all bus events. Call when the instance is no longer needed. */
    destroy(): void {
        if (this._unsubscribeProcessingCompleted) {
            this._unsubscribeProcessingCompleted();
            this._unsubscribeProcessingCompleted = null;
        }
    }
}
