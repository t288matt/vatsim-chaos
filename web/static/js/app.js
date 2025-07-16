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
        
        // Message overlay close button
        document.getElementById('messageCloseBtn').addEventListener('click', () => {
            this.hideMessage();
        });
    }
    
    showMessage(message, type = 'info') {
        const overlay = document.getElementById('messageOverlay');
        const content = document.querySelector('.message-content');
        const text = document.getElementById('messageText');
        
        // Remove existing classes
        content.className = 'message-content';
        
        // Add type-specific class
        content.classList.add(type);
        
        // Set message text
        text.textContent = message;
        
        // Show overlay
        overlay.style.display = 'block';
        
        // Auto-hide after 5 seconds for success/info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                this.hideMessage();
            }, 5000);
        }
    }
    
    hideMessage() {
        document.getElementById('messageOverlay').style.display = 'none';
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
            const briefing = await response.json();
            
            if (briefing.error) {
                app.showMessage(briefing.error, 'error');
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
}

// Initialize the application when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new App();
}); 