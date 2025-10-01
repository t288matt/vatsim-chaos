// Main application controller
class App {
    constructor() {
        this.fileManager = null;
        this.processor = null;
        this.mapViewer = null;
        this.briefingManager = null;
        
        this.initializeComponents();
        this.initializeEventListeners();
    }
    
    initializeComponents() {
        // Initialize all components
        this.fileManager = new FileManager();
        this.processor = new Processor();
        this.mapViewer = new MapViewer();
        this.briefingManager = new BriefingManager();
        
        // Load initial data
        this.fileManager.loadFileLibrary();
    }
    
    initializeEventListeners() {
        // Global event listeners
        document.addEventListener('DOMContentLoaded', () => {
            console.log('ATC Conflict Analysis System initialized');
        });
    }
    
    showMessage(message, type = 'info') {
        // Simple console logging instead of overlay
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
    
    hideMessage() {
        // No-op since we removed the overlay
    }
}

// Briefing Manager
class BriefingManager {
    constructor() {
        this.modal = document.getElementById('briefingModal');
        this.content = document.getElementById('briefingContent');
        this.closeBtn = document.querySelector('.close');
        this.briefingBtn = document.getElementById('briefingBtn');
        this.printBtn = document.getElementById('printBriefingBtn');
        this.downloadBtn = document.getElementById('downloadBriefingBtn');
        
        this.initializeEventListeners();
        this.checkBriefingAvailability();
    }
    
    initializeEventListeners() {
        this.briefingBtn.addEventListener('click', this.showBriefing.bind(this));
        this.closeBtn.addEventListener('click', this.hideBriefing.bind(this));
        this.printBtn.addEventListener('click', this.printBriefing.bind(this));
        this.downloadBtn.addEventListener('click', this.downloadBriefing.bind(this));
        
        // Close modal when clicking outside
        window.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hideBriefing();
            }
        });
        
        // Close modal with Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.style.display === 'block') {
                this.hideBriefing();
            }
        });
    }
    
    async showBriefing() {
        try {
            const response = await fetch('/briefing');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const briefing = await response.json();
            
            if (briefing.error) {
                app.showMessage(briefing.error, 'error');
                return;
            }
            
            if (!briefing.content) {
                app.showMessage('No briefing content received', 'error');
                return;
            }
            
            this.content.innerHTML = `
                <div class="briefing-content">
                    <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 0.9rem; line-height: 1.4;">${briefing.content}</pre>
                </div>
            `;
            
            this.modal.style.display = 'block';
        } catch (error) {
            app.showMessage('Error loading briefing: ' + error.message, 'error');
        }
    }
    
    hideBriefing() {
        this.modal.style.display = 'none';
    }
    
    printBriefing() {
        const content = this.content.querySelector('pre').textContent;
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Pilot Briefing</title>
                    <style>
                        body { font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.4; margin: 20px; }
                        pre { white-space: pre-wrap; }
                    </style>
                </head>
                <body>
                    <h1>Pilot Briefing</h1>
                    <pre>${content}</pre>
                </body>
            </html>
        `);
        printWindow.document.close();
        printWindow.print();
    }
    
    downloadBriefing() {
        const content = this.content.querySelector('pre').textContent;
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'pilot_briefing.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    async checkBriefingAvailability() {
        try {
            // Check if briefing file exists by making a HEAD-like request
            const response = await fetch('/briefing');
            
            if (response.ok) {
                // Briefing file exists, enable the button
                this.briefingBtn.disabled = false;
                console.log('[BRIEFING] Pilot briefing available - button enabled');
            } else {
                // Briefing file doesn't exist yet, keep button disabled
                this.briefingBtn.disabled = true;
                console.log('[BRIEFING] Pilot briefing not yet available - button disabled');
            }
        } catch (error) {
            // On error, keep button disabled
            console.warn('[BRIEFING] Error checking briefing availability:', error);
            this.briefingBtn.disabled = true;
        }
    }
}

// Initialize the application when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new App();
}); 