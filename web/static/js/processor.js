// Processor - Handles analysis workflow and progress tracking
class Processor {
    constructor() {
        this.processBtn = document.getElementById('processBtn');
        this.progressSection = document.getElementById('progressSection');
        this.progressContainer = document.getElementById('progressContainer');
        
        this.isProcessing = false;
        this.statusCheckInterval = null;
        this.processingStartTime = null;
        this.maxProcessingTime = 300000; // 5 minutes
        this.retryCount = 0;
        this.maxRetries = 3;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        this.processBtn.addEventListener('click', this.startProcessing.bind(this));
    }
    
    showMessage(message, type = 'info') {
        // Safely access the global app instance
        if (typeof app !== 'undefined' && app && app.showMessage) {
            app.showMessage(message, type);
        } else {
            // Fallback: use console or alert
            console.log(`[${type.toUpperCase()}] ${message}`);
            if (type === 'error') {
                alert(`Error: ${message}`);
            }
        }
    }
    
    async startProcessing() {
        if (this.isProcessing) {
            this.showMessage('Processing already in progress. Please wait.', 'warning');
            return;
        }
        
        const selectedFiles = app.fileManager.getSelectedFilesWithValidation();
        if (selectedFiles.length === 0) {
            this.showMessage('Please select at least one XML file to process.', 'warning');
            return;
        }
        
        // Edge case: Check for processing prerequisites
        const validationResults = await this.validateProcessingPrerequisites(selectedFiles);
        if (!validationResults.canProcess) {
            this.showMessage(validationResults.error, 'error');
            return;
        }
        
        // Edge case: Check if any files have no flights
        const emptyFiles = selectedFiles.filter(file => file.flight_count === 0);
        if (emptyFiles.length > 0) {
            const emptyNames = emptyFiles.map(f => f.filename).join(', ');
            const proceed = confirm(`Warning: Files with no flights detected: ${emptyNames}\n\nDo you want to continue processing?`);
            if (!proceed) {
                return;
            }
        }
        
        this.isProcessing = true;
        this.processingStartTime = Date.now();
        this.retryCount = 0;
        this.processBtn.disabled = true;
        this.processBtn.textContent = '🔄 Processing...';
        
        // Show progress section
        this.progressSection.style.display = 'block';
        
        try {
            const response = await fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    files: selectedFiles.map(f => f.filename)
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                this.showMessage('Processing started successfully!', 'success');
                this.monitorProgress();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Processing failed');
            }
        } catch (error) {
            this.handleProcessingError(error.message);
        }
    }
    
    async validateProcessingPrerequisites(selectedFiles) {
        // Edge case: Check if files are valid
        const invalidFiles = selectedFiles.filter(file => !file.valid);
        if (invalidFiles.length > 0) {
            const invalidNames = invalidFiles.map(f => f.filename).join(', ');
            return {
                canProcess: false,
                error: `Cannot process invalid files: ${invalidNames}`
            };
        }
        
        // Edge case: Check if too many files selected
        if (selectedFiles.length > 100) {
            return {
                canProcess: false,
                error: 'Too many files selected. Please select 100 or fewer files.'
            };
        }
        
        // Edge case: Check if any files have no flights
        const emptyFiles = selectedFiles.filter(file => file.flight_count === 0);
        if (emptyFiles.length > 0) {
            const emptyNames = emptyFiles.map(f => f.filename).join(', ');
            const proceed = confirm(`Warning: Files with no flights detected: ${emptyNames}\n\nDo you want to continue processing?`);
            if (!proceed) {
                return {
                    canProcess: false,
                    error: 'Processing cancelled by user.'
                };
            }
        }
        
        // Edge case: Check for same origin-destination pairs
        try {
            const response = await fetch('/validate-same-routes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    files: selectedFiles.map(f => f.filename)
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const routeValidation = await response.json();
            
            if (routeValidation.has_duplicates) {
                const duplicateDetails = routeValidation.duplicate_routes.map(route => 
                    `${route.origin}-${route.destination} (${route.count} files: ${route.files.join(', ')})`
                ).join('\n');
                
                const errorMessage = `⚠️ SYSTEM LIMITATION: Same Origin-Destination Routes Detected\n\n` +
                    `The system cannot process multiple flights with identical origin-destination pairs.\n\n` +
                    `Duplicate routes found:\n${duplicateDetails}\n\n` +
                    `To resolve this:\n` +
                    `• Use different aircraft types\n` +
                    `• Add intermediate waypoints to one flight\n` +
                    `• Use different cruise altitudes\n` +
                    `• Remove duplicate files\n\n` +
                    `Only the first flight with each route will be processed.`;
                
                const proceed = confirm(errorMessage + '\n\nDo you want to continue with only the first flight per route?');
                if (!proceed) {
                    return {
                        canProcess: false,
                        error: 'Processing cancelled due to duplicate routes.'
                    };
                } else {
                    this.showMessage('⚠️ Processing will continue with only the first flight per route. Some files will be ignored.', 'warning');
                }
            }
        } catch (error) {
            console.error('Route validation error:', error);
            this.showMessage('Warning: Could not validate routes. Processing may fail if duplicate routes exist.', 'warning');
        }
        
        // Edge case: Check if any files are too large
        const largeFiles = selectedFiles.filter(file => file.size > 10 * 1024 * 1024); // 10MB
        if (largeFiles.length > 0) {
            const largeNames = largeFiles.map(f => f.filename).join(', ');
            const proceed = confirm(`Large files detected: ${largeNames}\n\nProcessing may take longer than usual. Continue?`);
            if (!proceed) {
                return {
                    canProcess: false,
                    error: 'Processing cancelled by user.'
                };
            }
        }
        
        return { canProcess: true };
    }
    
    async monitorProgress() {
        const checkStatus = async () => {
            try {
                // Edge case: Check for processing timeout
                if (this.processingStartTime && (Date.now() - this.processingStartTime) > this.maxProcessingTime) {
                    this.handleProcessingTimeout();
                    return;
                }
                
                const response = await fetch('/status');
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                const status = await response.json();
                
                this.updateProgressDisplay(status);
                
                if (status.completed) {
                    this.handleProcessingComplete();
                } else if (status.failed) {
                    this.handleProcessingError(status.error);
                } else {
                    // Continue monitoring with exponential backoff
                    const delay = Math.min(1000 * Math.pow(1.5, this.retryCount), 10000);
                    this.statusCheckInterval = setTimeout(checkStatus, delay);
                }
            } catch (error) {
                console.error('Status check error:', error);
                this.retryCount++;
                
                if (this.retryCount >= this.maxRetries) {
                    this.handleProcessingError(`Status monitoring failed after ${this.maxRetries} attempts: ${error.message}`);
                } else {
                    // Exponential backoff for retries
                    const delay = Math.min(2000 * Math.pow(2, this.retryCount), 15000);
                    this.statusCheckInterval = setTimeout(checkStatus, delay);
                }
            }
        };
        
        checkStatus();
    }
    
    handleProcessingTimeout() {
        const errorMessage = 'Processing timed out after 5 minutes. The operation may still be running in the background.';
        this.handleProcessingError(errorMessage);
        
        // Show additional guidance
        this.showMessage('Check the server logs for more details. You can try processing again with fewer files.', 'warning');
    }
    
    updateProgressDisplay(status) {
        const steps = [
            'Extract flight plan data',
            'Analyze conflicts',
            'Merge KML files',
            'Schedule conflicts',
            'Export animation data',
            'Audit conflict data'
        ];
        
        let progressHtml = '<div class="progress-container">';
        steps.forEach((step, index) => {
            const isCompleted = index < status.current_step;
            const isCurrent = index === status.current_step;
            
            let icon = '⏳';
            let className = '';
            
            if (isCompleted) {
                icon = '✅';
                className = 'completed';
            } else if (isCurrent) {
                icon = '🔄';
                className = 'current';
            }
            
            progressHtml += `
                <div class="progress-step ${className}">
                    <span class="step-icon">${icon}</span>
                    <span class="step-text">${step}</span>
                </div>
            `;
        });
        progressHtml += '</div>';
        
        // Edge case: Show processing time
        if (this.processingStartTime) {
            const elapsed = Math.floor((Date.now() - this.processingStartTime) / 1000);
            progressHtml += `<div class="processing-time">Processing time: ${elapsed}s</div>`;
        }
        
        this.progressContainer.innerHTML = progressHtml;
    }
    
    async checkDataFilesExist() {
        try {
            // Check if key data files exist
            const filesToCheck = [
                '/temp/routes_with_added_interpolated_points.json',
                '/animation/animation_data.json',
                '/animation/conflict_points.json'
            ];
            
            for (const file of filesToCheck) {
                const response = await fetch(file);
                if (!response.ok) {
                    console.warn(`Data file not found: ${file}`);
                    return false;
                }
            }
            return true;
        } catch (error) {
            console.error('Error checking data files:', error);
            return false;
        }
    }
    
    handleProcessingComplete() {
        const processingTime = this.processingStartTime ? 
            Math.floor((Date.now() - this.processingStartTime) / 1000) : 0;
        
        this.showMessage(`Processing completed successfully in ${processingTime} seconds!`, 'success');
        this.resetProcessingState();
        
        // Enable briefing button
        document.getElementById('briefingBtn').disabled = false;
        
        // Add delay to allow data files to be written before refreshing map
        setTimeout(async () => {
            // Check if data files exist
            const dataFilesExist = await this.checkDataFilesExist();
            
            if (dataFilesExist) {
                // Refresh map with new data
                if (typeof mapViewer !== 'undefined' && mapViewer) {
                    console.log('Refreshing map with new data...');
                    mapViewer.refreshMap();
                } else {
                    console.warn('MapViewer not available for refresh');
                    // Fallback: reload the page to show new data
                    setTimeout(() => {
                        if (confirm('Processing completed! Reload page to see updated map?')) {
                            window.location.reload();
                        }
                    }, 1000);
                }
            } else {
                console.warn('Data files not found, suggesting page reload');
                this.showMessage('Processing completed but data files not found. Please reload the page to see results.', 'warning');
                setTimeout(() => {
                    if (confirm('Processing completed! Reload page to see updated map?')) {
                        window.location.reload();
                    }
                }, 1000);
            }
        }, 2000); // Wait 2 seconds for files to be written
        
        // Hide progress section after a delay
        setTimeout(() => {
            this.progressSection.style.display = 'none';
        }, 3000);
    }
    
    handleProcessingError(error) {
        this.showMessage('Processing failed: ' + error, 'error');
        this.resetProcessingState();
        
        // Show error in progress section with retry option
        this.progressContainer.innerHTML = `
            <div class="progress-error">
                <span class="step-icon">❌</span>
                <span class="step-text">Processing failed: ${error}</span>
                <button onclick="processor.retryProcessing()" class="retry-btn">🔄 Retry</button>
            </div>
        `;
    }
    
    async retryProcessing() {
        if (this.isProcessing) {
            this.showMessage('Processing already in progress.', 'warning');
            return;
        }
        
        this.retryCount = 0;
        await this.startProcessing();
    }
    
    resetProcessingState() {
        this.isProcessing = false;
        this.processingStartTime = null;
        this.retryCount = 0;
        this.processBtn.disabled = false;
        this.processBtn.textContent = '🚀 Process Analysis';
        
        // Clear status check interval
        if (this.statusCheckInterval) {
            clearTimeout(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
    }
    
    // Method to get current processing status
    getProcessingStatus() {
        return {
            isProcessing: this.isProcessing,
            selectedFiles: app.fileManager.getSelectedFilesWithValidation(),
            processingTime: this.processingStartTime ? 
                Math.floor((Date.now() - this.processingStartTime) / 1000) : 0,
            retryCount: this.retryCount
        };
    }
} 