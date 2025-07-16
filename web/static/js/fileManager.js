// File Manager - Handles file uploads and flight plan library management
class FileManager {
    constructor() {
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.fileList = document.getElementById('fileList');
        this.uploadStatus = document.getElementById('uploadStatus');
        this.selectionSummary = document.getElementById('selectionSummary');
        this.selectAllBtn = document.getElementById('selectAllBtn');
        this.selectNoneBtn = document.getElementById('selectNoneBtn');
        
        this.selectedFiles = new Set();
        this.files = [];
        this.fileValidationCache = new Map(); // Cache validation results
        this.uploadQueue = []; // Queue for handling multiple uploads
        this.isUploading = false;
        
        this.initializeEventListeners();
    }
    
    initializeEventListeners() {
        // Drag and drop functionality
        this.uploadArea.addEventListener('dragover', this.handleDragOver.bind(this));
        this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
        this.uploadArea.addEventListener('drop', this.handleDrop.bind(this));
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        
        // File selection controls
        this.selectAllBtn.addEventListener('click', this.selectAll.bind(this));
        this.selectNoneBtn.addEventListener('click', this.selectNone.bind(this));
    }
    
    handleDragOver(e) {
        e.preventDefault();
        this.uploadArea.classList.add('dragover');
    }
    
    handleDragLeave(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }
    
    async handleDrop(e) {
        e.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const files = Array.from(e.dataTransfer.files);
        await this.uploadFiles(files);
    }
    
    async handleFileSelect(e) {
        const files = Array.from(e.target.files);
        await this.uploadFiles(files);
        
        // Reset file input
        e.target.value = '';
    }
    
    async uploadFiles(files) {
        // Edge case: No files provided
        if (!files || files.length === 0) {
            this.showMessage('No files selected for upload.', 'warning');
            return;
        }
        
        // Edge case: Too many files at once
        if (files.length > 50) {
            this.showMessage('Too many files selected. Please upload 50 or fewer files at once.', 'error');
            return;
        }
        
        const xmlFiles = files.filter(file => {
            // Edge case: Check file type
            const isValidType = file.type === 'application/xml' || 
                              file.name.toLowerCase().endsWith('.xml');
            
            if (!isValidType) {
                this.showMessage(`Skipping non-XML file: ${file.name}`, 'warning');
                return false;
            }
            
            // Edge case: Check file size
            if (file.size > 16 * 1024 * 1024) { // 16MB limit
                this.showMessage(`File too large: ${file.name} (${this.formatFileSize(file.size)})`, 'error');
                return false;
            }
            
            // Edge case: Check for empty files
            if (file.size === 0) {
                this.showMessage(`Empty file skipped: ${file.name}`, 'warning');
                return false;
            }
            
            return true;
        });
        
        if (xmlFiles.length === 0) {
            this.showMessage('No valid XML files found for upload.', 'warning');
            return;
        }
        
        // Edge case: Check for duplicate filenames
        const duplicateFiles = this.findDuplicateFilenames(xmlFiles);
        if (duplicateFiles.length > 0) {
            const duplicateNames = duplicateFiles.map(f => f.name).join(', ');
            this.showMessage(`Duplicate filenames detected: ${duplicateNames}`, 'warning');
        }
        
        const formData = new FormData();
        xmlFiles.forEach(file => {
            formData.append('files', file);
        });
        
        try {
            this.isUploading = true;
            this.showUploadStatus(`Uploading ${xmlFiles.length} files...`, 'info');
            
            // Edge case: Network timeout handling
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
            
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                signal: controller.signal
            });
            
            clearTimeout(timeoutId);
            
            if (response.ok) {
                const result = await response.json();
                this.showUploadStatus(`${result.uploaded.length} files uploaded successfully!`, 'success');
                this.showMessage(`${result.uploaded.length} files uploaded successfully!`, 'success');
                
                // Reload flight plan library
                await this.loadFileLibrary();
                
                // Validate uploaded files with retry logic
                for (const uploadedFile of result.uploaded) {
                    await this.validateFileWithRetry(uploadedFile.name);
                }
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Upload failed');
            }
        } catch (error) {
            // Edge case: Handle different types of upload errors
            let errorMessage = 'Upload error: ';
            
            if (error.name === 'AbortError') {
                errorMessage += 'Upload timed out. Please try again.';
            } else if (error.message.includes('413')) {
                errorMessage += 'File size exceeds server limit.';
            } else if (error.message.includes('network')) {
                errorMessage += 'Network error. Please check your connection.';
            } else {
                errorMessage += error.message;
            }
            
            this.showUploadStatus(errorMessage, 'error');
            this.showMessage(errorMessage, 'error');
        } finally {
            this.isUploading = false;
        }
    }
    
    findDuplicateFilenames(files) {
        const seen = new Set();
        const duplicates = [];
        
        files.forEach(file => {
            if (seen.has(file.name)) {
                duplicates.push(file);
            } else {
                seen.add(file.name);
            }
        });
        
        return duplicates;
    }
    
    async validateFileWithRetry(filename, maxRetries = 3) {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const validation = await this.validateFile(filename);
                
                if (validation.valid) {
                    console.log(`File ${filename} validated successfully on attempt ${attempt}`);
                    return validation;
                } else {
                    console.warn(`File ${filename} validation failed on attempt ${attempt}: ${validation.error}`);
                    
                    if (attempt === maxRetries) {
                        this.showMessage(`File ${filename} validation failed after ${maxRetries} attempts`, 'error');
                    }
                }
            } catch (error) {
                console.error(`Validation attempt ${attempt} failed for ${filename}:`, error);
                
                if (attempt === maxRetries) {
                    this.showMessage(`File ${filename} validation failed: ${error.message}`, 'error');
                } else {
                    // Wait before retry
                    await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
                }
            }
        }
        
        return { valid: false, error: 'Validation failed after all retries' };
    }
    
    async validateFile(filename) {
        try {
            console.log(`[VALIDATE] Frontend requesting validation for: ${filename}`);
            const response = await fetch(`/validate/${filename}`);
            
            console.log(`[VALIDATE] Response status: ${response.status}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const validation = await response.json();
            console.log(`[VALIDATE] Validation response:`, validation);
            
            this.fileValidationCache.set(filename, validation);
            
            if (!validation.valid) {
                console.warn(`[VALIDATE] File ${filename} marked as invalid: ${validation.error}`);
                this.showMessage(`File ${filename} validation failed: ${validation.error}`, 'warning');
            } else {
                console.log(`[VALIDATE] File ${filename} validated successfully: ${validation.flight_count} flights found`);
            }
            
            return validation;
        } catch (error) {
            console.error(`[VALIDATE] Validation error for ${filename}:`, error);
            return { valid: false, error: 'Validation failed' };
        }
    }
    
    getFileValidation(filename) {
        const cached = this.fileValidationCache.get(filename);
        const result = cached || { valid: false, error: 'Not validated' };
        console.log(`[CACHE] Getting validation for ${filename}:`, result);
        return result;
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
    
    showUploadStatus(message, type) {
        this.uploadStatus.textContent = message;
        this.uploadStatus.className = `upload-status ${type}`;
        this.uploadStatus.style.display = 'block';
        
        // Hide status after 5 seconds for success/info messages
        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                this.uploadStatus.style.display = 'none';
            }, 5000);
        }
    }
    
    async loadFileLibrary() {
        try {
            const response = await fetch('/files');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            this.files = await response.json();
            this.renderFileList();
            
            // Validate all files that haven't been validated yet
            console.log('[LOAD] Validating all unvalidated files...');
            for (const file of this.files) {
                const validation = this.getFileValidation(file.name);
                if (!validation.valid && validation.error === 'Not validated') {
                    console.log(`[LOAD] Validating file: ${file.name}`);
                    await this.validateFileWithRetry(file.name);
                }
            }
            
            // Re-render the file list after validation
            this.renderFileList();
            
            // Select all files by default
            this.selectAll();
            
            // Check for duplicate routes after loading files
            await this.checkForDuplicateRoutes();
        } catch (error) {
            console.error('Error loading flight plan library:', error);
            this.showMessage('Error loading flight plan library: ' + error.message, 'error');
            
            // Edge case: Show cached files if available
            if (this.files.length > 0) {
                this.showMessage('Showing cached file list. Some files may not be up to date.', 'warning');
                this.renderFileList();
                // Select all files even in error case
                this.selectAll();
            }
        }
    }
    
    async checkForDuplicateRoutes() {
        if (this.files.length === 0) return;
        
        try {
            const response = await fetch('/validate-same-routes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    files: this.files.map(f => f.name)
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const routeValidation = await response.json();
            
            if (routeValidation.has_duplicates) {
                // Show warning about duplicate routes
                const duplicateDetails = routeValidation.duplicate_routes.map(route => 
                    `${route.origin}-${route.destination} (${route.count} files)`
                ).join(', ');
                
                this.showMessage(`⚠️ Duplicate routes detected: ${duplicateDetails}. Please delete duplicate files before generating schedule.`, 'warning');
                
                // Mark duplicate files visually
                this.markDuplicateFiles(routeValidation.duplicate_routes);
                
                // Disable the Generate Schedule button
                this.disableGenerateScheduleButton(routeValidation.duplicate_routes);
            } else {
                // No duplicates found, enable the button
                this.enableGenerateScheduleButton();
            }
        } catch (error) {
            console.error('Error checking for duplicate routes:', error);
        }
    }
    
    disableGenerateScheduleButton(duplicateRoutes) {
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = '🚫 Generate Schedule (Duplicates Detected)';
            processBtn.title = 'Please delete duplicate files before generating schedule';
            
            // Add visual styling for disabled state
            processBtn.classList.add('disabled-duplicates');
        }
        
        // Store duplicate routes info for reference
        this.duplicateRoutes = duplicateRoutes;
    }
    
    enableGenerateScheduleButton() {
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            processBtn.disabled = false;
            processBtn.textContent = '🚀 Generate Schedule';
            processBtn.title = '';
            processBtn.classList.remove('disabled-duplicates');
        }
        
        // Clear duplicate routes info
        this.duplicateRoutes = null;
    }
    
    markDuplicateFiles(duplicateRoutes) {
        // Add visual indicators for duplicate files
        duplicateRoutes.forEach(route => {
            route.files.forEach(filename => {
                const fileItem = document.querySelector(`[data-filename="${filename}"]`);
                if (fileItem) {
                    fileItem.classList.add('duplicate-route');
                    fileItem.setAttribute('title', `Duplicate route: ${route.origin}-${route.destination}`);
                }
            });
        });
    }
    
    renderFileList() {
        this.fileList.innerHTML = '';
        
        if (this.files.length === 0) {
            this.fileList.innerHTML = '<div class="file-item"><p style="text-align: center; color: #6c757d; padding: 20px;">No files uploaded yet</p></div>';
            return;
        }
        
        this.files.forEach(file => {
            const fileItem = this.createFileItem(file);
            this.fileList.appendChild(fileItem);
        });
        
        this.updateSelectionSummary();
    }
    
    createFileItem(file) {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.setAttribute('data-filename', file.name);
        
        const isSelected = this.selectedFiles.has(file.id);
        const validation = this.getFileValidation(file.name);
        
        console.log(`[UI] Creating file item for ${file.name}:`, {
            isSelected,
            validation: validation,
            valid: validation.valid,
            error: validation.error
        });
        
        // Show validation status with color coding but smaller
        let validationIndicator = '';
        if (validation.valid) {
            validationIndicator = '<span class="validation-indicator valid" title="Valid XML">✓</span>';
        } else if (validation.error && validation.error !== 'Not validated') {
            validationIndicator = '<span class="validation-indicator invalid" title="Invalid XML">✗</span>';
        } else {
            validationIndicator = '<span class="validation-indicator pending" title="Not validated">?</span>';
        }
        
        div.innerHTML = `
            <input type="checkbox" id="file_${file.id}" ${isSelected ? 'checked' : ''}>
            <label for="file_${file.id}">
                <span class="filename">${this.escapeHtml(file.name)}</span>
                ${validationIndicator}
            </label>
            <button class="delete-btn" title="Delete file" data-filename="${this.escapeHtml(file.name)}">
                🗑️
            </button>
        `;
        
        const checkbox = div.querySelector('input[type="checkbox"]');
        checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.selectedFiles.add(file.id);
            } else {
                this.selectedFiles.delete(file.id);
            }
            this.updateSelectionSummary();
        });
        
        // Add delete functionality
        const deleteBtn = div.querySelector('.delete-btn');
        deleteBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.deleteFile(file.name);
        });
        
        return div;
    }
    

    
    selectAll() {
        this.files.forEach(file => {
            this.selectedFiles.add(file.id);
        });
        this.renderFileList();
    }
    
    selectNone() {
        this.selectedFiles.clear();
        this.renderFileList();
    }
    
    updateSelectionSummary() {
        const count = this.selectedFiles.size;
        if (count === 0) {
            this.selectionSummary.textContent = 'No files selected';
        } else if (count === 1) {
            this.selectionSummary.textContent = '1 file selected';
        } else {
            this.selectionSummary.textContent = `${count} files selected`;
        }
        
        // Update Process Analysis button state
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            if (count === 0) {
                processBtn.disabled = true;
                processBtn.textContent = '🚀 Generate Schedule';
                processBtn.classList.remove('disabled-duplicates');
            } else {
                // Check if there are duplicate routes before enabling
                if (this.duplicateRoutes && this.duplicateRoutes.length > 0) {
                    processBtn.disabled = true;
                    processBtn.textContent = '🚫 Generate Schedule (Duplicates Detected)';
                    processBtn.title = 'Please delete duplicate files before generating schedule';
                    processBtn.classList.add('disabled-duplicates');
                } else {
                    processBtn.disabled = false;
                    processBtn.textContent = '🚀 Generate Schedule';
                    processBtn.title = '';
                    processBtn.classList.remove('disabled-duplicates');
                }
            }
        }
    }
    
    getSelectedFiles() {
        return Array.from(this.selectedFiles);
    }
    
    getSelectedFilesWithValidation() {
        const selectedFiles = this.getSelectedFiles();
        const filesWithValidation = [];
        
        for (const filename of selectedFiles) {
            const validation = this.getFileValidation(filename);
            filesWithValidation.push({
                filename,
                valid: validation.valid,
                flight_count: validation.flight_count || 0,
                error: validation.error
            });
        }
        
        return filesWithValidation;
    }
    
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
    
    async deleteFile(filename) {
        if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
            return;
        }
        
        try {
            console.log(`[DELETE] Attempting to delete file: ${filename}`);
            
            const response = await fetch(`/delete-file/${encodeURIComponent(filename)}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log(`[DELETE] File deleted successfully: ${filename}`);
                this.showMessage(`File "${filename}" deleted successfully`, 'success');
                
                // Remove from selected files if it was selected
                this.selectedFiles.delete(filename);
                
                // Reload the flight plan library to update the list
                await this.loadFileLibrary();
                
                // Re-check for duplicate routes after deletion
                await this.checkForDuplicateRoutes();
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Delete failed');
            }
        } catch (error) {
            console.error(`[DELETE] Error deleting file ${filename}:`, error);
            this.showMessage(`Failed to delete file "${filename}": ${error.message}`, 'error');
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
} 