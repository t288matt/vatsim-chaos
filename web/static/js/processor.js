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
        this.processBtn.textContent = '🔄 Generating...';
        
        // Show progress section
        this.progressSection.style.display = 'block';
        
        try {
            // Get time parameters from the frontend
            const startTime = document.getElementById('startTime').value || '14:00';
            const endTime = document.getElementById('endTime').value || '18:00';
            
            const response = await fetch('/process', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    files: selectedFiles.map(f => f.filename),
                    startTime: startTime,
                    endTime: endTime
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
                
                const errorMessage = `⚠️ DUPLICATE ROUTES DETECTED\n\n` +
                    `The system cannot process multiple flights with identical origin-destination pairs.\n\n` +
                    `Duplicate routes found:\n${duplicateDetails}\n\n` +
                    `Please delete duplicate files before generating schedule.\n\n` +
                    `To resolve this:\n` +
                    `• Delete duplicate files\n` +
                    `• Use different aircraft types\n` +
                    `• Add intermediate waypoints to one flight\n` +
                    `• Use different cruise altitudes`;
                
                this.showMessage('⚠️ Please delete duplicate files before generating schedule.', 'error');
                return {
                    canProcess: false,
                    error: 'Processing blocked due to duplicate routes. Please delete duplicates first.'
                };
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
                
                await this.updateProgressDisplay(status);
                
                if (status.completed) {
                    this.handleProcessingComplete();
                } else if (status.failed) {
                    this.handleProcessingError(status.error);
                } else {
                    // Continue monitoring with 3-second polling
                    const delay = Math.min(3000 * Math.pow(1.5, this.retryCount), 15000);
                    this.statusCheckInterval = setTimeout(checkStatus, delay);
                }
            } catch (error) {
                console.error('Status check error:', error);
                this.retryCount++;
                
                // NEW: Check if processing actually completed despite status tracking failure
                if (this.retryCount >= this.maxRetries) {
                    await this.checkForCompletedProcessing();
                } else {
                    // Exponential backoff for retries (3s base)
                    const delay = Math.min(3000 * Math.pow(2, this.retryCount), 20000);
                    this.statusCheckInterval = setTimeout(checkStatus, delay);
                }
            }
        };
        
        checkStatus();
    }
    
    async checkForCompletedProcessing() {
        console.log('[PROCESSING] Status tracking failed, checking for completed processing...');
        
        try {
            // Check if key output files exist to determine if processing completed
            const filesToCheck = [
                '/temp/potential_conflict_data.json',
                '/animation/animation_data.json',
                '/animation/conflict_points.json',
                '/merged_flightplans.kml',
                '/pilot_briefing.txt'
            ];
            
            let completedFiles = 0;
            let totalFiles = filesToCheck.length;
            
            for (const file of filesToCheck) {
                try {
                    const response = await fetch(file);
                    if (response.ok) {
                        completedFiles++;
                    }
                } catch (e) {
                    console.warn(`File check failed for ${file}:`, e);
                }
            }
            
            // If most files exist, assume processing completed successfully
            const completionRatio = completedFiles / totalFiles;
            console.log(`[PROCESSING] Found ${completedFiles}/${totalFiles} output files (${Math.round(completionRatio * 100)}% completion)`);
            
            if (completionRatio >= 0.6) { // 60% or more files exist
                console.log('[PROCESSING] Processing completed successfully - auto-refreshing map');
                this.handleProcessingComplete();
                return;
            } else if (completionRatio >= 0.3) { // 30-59% files exist
                console.log('[PROCESSING] Partial completion detected - auto-refreshing map');
                this.handleProcessingComplete();
                return;
            } else {
                // Less than 30% files exist, likely failed
                console.log('[PROCESSING] Insufficient output files found - processing may have failed');
            }
            
        } catch (error) {
            console.error('[PROCESSING] Error checking for completed processing:', error);
        }
    }
    
    handleProcessingTimeout() {
        const errorMessage = 'Processing timed out after 5 minutes. The operation may still be running in the background.';
        this.handleProcessingError(errorMessage);
        
        // Show additional guidance
        this.showMessage('Check the server logs for more details. You can try processing again with fewer files.', 'warning');
    }
    
    async updateProgressDisplay(status) {
        const steps = [
            'Extract flight plan data',
            'Analyse conflicts',
            'Merge KML files',
            'Schedule conflicts',
            'Export animation data',
            'Audit conflict data'
        ];
        
        // NEW: Check for actual file completion if status tracking is unreliable
        let actualProgress = await this.determineActualProgress();
        
        let progressHtml = '<div class="progress-container">';
        steps.forEach((step, index) => {
            const isCompleted = index < status.current_step || (actualProgress && index < actualProgress);
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
    
    async determineActualProgress() {
        try {
            // Check for key files to determine actual progress
            const fileChecks = [
                { step: 0, files: ['/temp/FLT0001_data.json'] }, // Extract step
                { step: 1, files: ['/temp/potential_conflict_data.json'] }, // Analyse step
                { step: 2, files: ['/merged_flightplans.kml'] }, // Merge step
                { step: 3, files: ['/temp/routes_with_added_interpolated_points.json'] }, // Schedule step
                { step: 4, files: ['/animation/animation_data.json'] }, // Export step
                { step: 5, files: ['/pilot_briefing.txt'] } // Audit step
            ];
            
            let lastCompletedStep = -1;
            
            for (const check of fileChecks) {
                let stepCompleted = true;
                for (const file of check.files) {
                    try {
                        const response = await fetch(file);
                        if (!response.ok) {
                            stepCompleted = false;
                            break;
                        }
                    } catch (e) {
                        stepCompleted = false;
                        break;
                    }
                }
                
                if (stepCompleted) {
                    lastCompletedStep = check.step;
                } else {
                    break; // Stop at first incomplete step
                }
            }
            
            return lastCompletedStep >= 0 ? lastCompletedStep + 1 : null;
        } catch (error) {
            console.error('[PROGRESS] Error determining actual progress:', error);
            return null;
        }
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
        
        console.log(`[PROCESSOR] Processing completed successfully in ${processingTime} seconds`);
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
                    console.log('[PROCESSOR] Auto-refreshing map with new data...');
                    mapViewer.refreshMap();
                } else {
                    console.warn('[PROCESSOR] MapViewer not available, auto-reloading page...');
                    window.location.reload();
                }
            } else {
                console.warn('[PROCESSOR] Data files not found, auto-reloading page...');
                window.location.reload();
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
        this.processBtn.textContent = '🚀 Generate Schedule';
        
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