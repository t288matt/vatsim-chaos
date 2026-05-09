// File Manager — TypeScript reimplementation of web/static/js/fileManager.js
// Handles file uploads, flight plan library management, and validation.
// NOTE: web/static/js/fileManager.js is intentionally preserved; it is still
// loaded by web/templates/index.html until the HTML migration occurs.

import { EventBus, bus } from './eventBus';
import type { ApiResponse, FileInfo, ValidationResult } from '../types/api';

// ---------------------------------------------------------------------------
// Typed EventBus payload map for FileManager events
// ---------------------------------------------------------------------------

interface FileManagerEvents {
    'files:uploaded': { count: number };
    'files:loaded': { files: FileInfo[] };
    // CachedValidation is used here because validated data may have partial fields
    // (e.g. flight_count absent when the file is invalid and was never parsed).
    'validation:changed': { filename: string; result: CachedValidation };
    'files:selected': { files: Array<{ filename: string; valid: boolean; flight_count: number; error?: string }> };
}

const typedBus = new EventBus<FileManagerEvents>();

// ---------------------------------------------------------------------------
// Exported utility functions (tested by Vitest)
// ---------------------------------------------------------------------------

/**
 * Format a byte count into a human-readable string.
 * Returns '512 B' (no decimal) for values below 1 KB.
 */
export function formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'] as const;
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(i === 0 ? 0 : 1)} ${sizes[i]}`;
}

/**
 * Returns true if the filename is non-empty and ends with `.xml`
 * (case-insensitive).
 */
export function isValidXmlFilename(filename: string): boolean {
    return filename.length > 0 && filename.toLowerCase().endsWith('.xml');
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Format a Unix timestamp (or ms) to DD-MM-YYYY. */
function formatDate(timestamp: number): string {
    const date = new Date(timestamp);
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}-${month}-${year}`;
}

/**
 * Display a toast notification.
 * Falls back to console output when window.showToast is not available
 * (e.g. during tests or when the legacy JS has not been loaded).
 */
function showToast(message: string, type = 'info'): void {
    if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
        window.showToast(message, type);
    } else {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }
}

// ---------------------------------------------------------------------------
// Cached validation shape used internally
// ---------------------------------------------------------------------------

interface CachedValidation extends Partial<ValidationResult> {
    valid: boolean;
    error?: string;
}

// ---------------------------------------------------------------------------
// FileManager class
// ---------------------------------------------------------------------------

export class FileManager {
    private uploadArea: HTMLElement | null;
    private fileInput: HTMLInputElement | null;
    private uploadStatus: HTMLElement | null;
    private selectionCount: HTMLElement | null;
    private fileCountBadge: HTMLElement | null;
    private selectAllBtn: HTMLElement | null;
    private selectNoneBtn: HTMLElement | null;
    private deleteAllBtn: HTMLElement | null;

    private isUploading = false;

    private selectedFiles: Set<string>;
    private files: FileInfo[];
    private fileValidationCache: Map<string, CachedValidation>;
    private duplicateRoutes: Array<{ origin: string; destination: string; count: number; files: string[] }> | null;

    constructor() {
        this.uploadArea        = document.getElementById('uploadArea');
        this.fileInput         = document.getElementById('fileInput') as HTMLInputElement | null;
        this.uploadStatus      = document.getElementById('uploadStatus');
        this.selectionCount    = document.getElementById('selectionCount');
        this.fileCountBadge    = document.getElementById('fileCountBadge');
        this.selectAllBtn      = document.getElementById('selectAllBtn');
        this.selectNoneBtn     = document.getElementById('selectNoneBtn');
        this.deleteAllBtn      = document.getElementById('deleteAllBtn');

        this.selectedFiles        = new Set();
        this.files                = [];
        this.fileValidationCache  = new Map();
        this.duplicateRoutes      = null;

        this.initializeEventListeners();
    }

    private initializeEventListeners(): void {
        if (this.uploadArea) {
            this.uploadArea.addEventListener('dragover',  this.handleDragOver.bind(this));
            this.uploadArea.addEventListener('dragleave', this.handleDragLeave.bind(this));
            this.uploadArea.addEventListener('drop',      this.handleDrop.bind(this));
            this.uploadArea.addEventListener('click',     () => this.fileInput?.click());
            this.uploadArea.addEventListener('keydown',   (e: Event) => {
                const ke = e as KeyboardEvent;
                if (ke.key === 'Enter' || ke.key === ' ') {
                    ke.preventDefault();
                    this.fileInput?.click();
                }
            });
        }

        if (this.fileInput) {
            this.fileInput.addEventListener('change', this.handleFileSelect.bind(this));
        }

        this.selectAllBtn?.addEventListener('click',  this.selectAll.bind(this));
        this.selectNoneBtn?.addEventListener('click', this.selectNone.bind(this));
        this.deleteAllBtn?.addEventListener('click',  this.deleteAll.bind(this));

        const clearSelectionBtn = document.getElementById('clearSelectionBtn');
        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', this.selectNone.bind(this));
        }
    }

    private handleDragOver(e: Event): void {
        e.preventDefault();
        this.uploadArea?.classList.add('dragover');
    }

    private handleDragLeave(e: Event): void {
        e.preventDefault();
        this.uploadArea?.classList.remove('dragover');
    }

    private async handleDrop(e: Event): Promise<void> {
        e.preventDefault();
        this.uploadArea?.classList.remove('dragover');
        const de = e as DragEvent;
        const files = Array.from(de.dataTransfer?.files ?? []);
        await this.uploadFiles(files);
    }

    private async handleFileSelect(e: Event): Promise<void> {
        const target = e.target as HTMLInputElement;
        const files = Array.from(target.files ?? []);
        await this.uploadFiles(files);
        target.value = '';
    }

    async uploadFiles(files: File[]): Promise<void> {
        if (this.isUploading) {
            showToast('Upload already in progress. Please wait.', 'warning');
            return;
        }

        if (!files || files.length === 0) {
            showToast('No files selected for upload.', 'warning');
            return;
        }

        if (files.length > 50) {
            showToast('Too many files selected. Please upload 50 or fewer files at once.', 'error');
            return;
        }

        const xmlFiles = files.filter(file => {
            const isValidType = file.type === 'application/xml' ||
                                file.name.toLowerCase().endsWith('.xml');

            if (!isValidType) {
                showToast(`Skipping non-XML file: ${file.name}`, 'warning');
                return false;
            }

            if (file.size > 16 * 1024 * 1024) {
                showToast(`File too large: ${file.name} (${formatFileSize(file.size)})`, 'error');
                return false;
            }

            if (file.size === 0) {
                showToast(`Empty file skipped: ${file.name}`, 'warning');
                return false;
            }

            return true;
        });

        if (xmlFiles.length === 0) {
            showToast('No valid XML files found for upload.', 'warning');
            return;
        }

        const duplicateFiles = this.findDuplicateFilenames(xmlFiles);
        if (duplicateFiles.length > 0) {
            const duplicateNames = duplicateFiles.map(f => f.name).join(', ');
            showToast(`Duplicate filenames detected: ${duplicateNames}`, 'warning');
        }

        const formData = new FormData();
        xmlFiles.forEach(file => formData.append('files', file));

        this.isUploading = true;
        try {
            this.showUploadStatus(`Uploading ${xmlFiles.length} files...`, 'info');

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000);

            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
                signal: controller.signal,
            });

            clearTimeout(timeoutId);

            const body: ApiResponse<{ uploaded: Array<{ name: string }> }> = await response.json();

            if (!body.ok) {
                throw new Error(body.error || 'Upload failed');
            }

            const uploaded = body.data.uploaded;
            this.showUploadStatus(`${uploaded.length} files uploaded successfully!`, 'success');
            showToast(`${uploaded.length} files uploaded successfully!`, 'success');

            // Emit EventBus notification
            typedBus.emit('files:uploaded', { count: uploaded.length });

            await this.loadFileLibrary();

            for (const uploadedFile of uploaded) {
                await this.validateFileWithRetry(uploadedFile.name);
            }
        } catch (error) {
            let errorMessage = 'Upload error: ';
            const err = error as Error;

            if (err.name === 'AbortError') {
                errorMessage += 'Upload timed out. Please try again.';
            } else if (err.message.includes('413')) {
                errorMessage += 'File size exceeds server limit.';
            } else if (err.message.includes('network')) {
                errorMessage += 'Network error. Please check your connection.';
            } else {
                errorMessage += err.message;
            }

            this.showUploadStatus(errorMessage, 'error');
            showToast(errorMessage, 'error');
        } finally {
            this.isUploading = false;
        }
    }

    private findDuplicateFilenames(files: File[]): File[] {
        const seen = new Set<string>();
        const duplicates: File[] = [];

        files.forEach(file => {
            if (seen.has(file.name)) {
                duplicates.push(file);
            } else {
                seen.add(file.name);
            }
        });

        return duplicates;
    }

    async validateFileWithRetry(filename: string, maxRetries = 3): Promise<CachedValidation> {
        for (let attempt = 1; attempt <= maxRetries; attempt++) {
            try {
                const validation = await this.validateFile(filename);

                if (validation.valid) {
                    console.log(`File ${filename} validated successfully on attempt ${attempt}`);
                    return validation;
                } else {
                    console.warn(`File ${filename} validation failed on attempt ${attempt}: ${validation.error}`);

                    if (attempt === maxRetries) {
                        showToast(`File ${filename} validation failed after ${maxRetries} attempts`, 'error');
                    }
                }
            } catch (error) {
                const err = error as Error;
                console.error(`Validation attempt ${attempt} failed for ${filename}:`, err);

                if (attempt === maxRetries) {
                    showToast(`File ${filename} validation failed: ${err.message}`, 'error');
                } else {
                    await new Promise(resolve => setTimeout(resolve, 1000 * attempt));
                }
            }
        }

        return { valid: false, error: 'Validation failed after all retries' };
    }

    async validateFile(filename: string): Promise<CachedValidation> {
        try {
            console.log(`[VALIDATE] Frontend requesting validation for: ${filename}`);
            const response = await fetch(`/validate/${filename}`);
            console.log(`[VALIDATE] Response status: ${response.status}`);

            const body: ApiResponse<ValidationResult> = await response.json();
            console.log(`[VALIDATE] Validation response:`, body);

            if (!body.ok) {
                const errMsg = body.error || 'Validation failed';
                console.warn(`[VALIDATE] File ${filename} marked as invalid: ${errMsg}`);
                showToast(`File ${filename} validation failed: ${errMsg}`, 'warning');
                const result: CachedValidation = { valid: false, error: errMsg };
                this.fileValidationCache.set(filename, result);
                typedBus.emit('validation:changed', { filename, result });
                return result;
            }

            const validation = body.data;
            const cached: CachedValidation = { ...validation };
            this.fileValidationCache.set(filename, cached);

            if (!validation.valid) {
                console.warn(`[VALIDATE] File ${filename} marked as invalid: ${validation.error}`);
                showToast(`File ${filename} validation failed: ${validation.error}`, 'warning');
            } else {
                console.log(`[VALIDATE] File ${filename} validated successfully: ${validation.flight_count} flights found`);
            }

            typedBus.emit('validation:changed', { filename, result: cached });
            return cached;
        } catch (error) {
            const err = error as Error;
            console.error(`[VALIDATE] Validation error for ${filename}:`, err);
            return { valid: false, error: 'Validation failed' };
        }
    }

    getFileValidation(filename: string): CachedValidation {
        const cached = this.fileValidationCache.get(filename);
        const result = cached || { valid: false, error: 'Not validated' };
        console.log(`[CACHE] Getting validation for ${filename}:`, result);
        return result;
    }

    private showUploadStatus(message: string, type: string): void {
        if (!this.uploadStatus) return;
        this.uploadStatus.textContent = message;
        this.uploadStatus.className = `upload-status ${type}`;
        this.uploadStatus.style.display = 'block';

        if (type === 'success' || type === 'info') {
            setTimeout(() => {
                if (this.uploadStatus) this.uploadStatus.style.display = 'none';
            }, 5000);
        }
    }

    async loadFileLibrary(): Promise<void> {
        try {
            const response = await fetch('/files');
            const body: ApiResponse<FileInfo[]> = await response.json();

            if (!body.ok) {
                throw new Error(body.error || `HTTP ${response.status}`);
            }

            this.files = body.data;
            this.renderFileList();

            console.log('[LOAD] Validating all unvalidated files...');
            for (const file of this.files) {
                const validation = this.getFileValidation(file.name);
                if (!validation.valid && validation.error === 'Not validated') {
                    console.log(`[LOAD] Validating file: ${file.name}`);
                    await this.validateFileWithRetry(file.name);
                }
            }

            this.renderFileList();
            this.selectAll();
            await this.checkForDuplicateRoutes();

            typedBus.emit('files:loaded', { files: this.files });
        } catch (error) {
            const err = error as Error;
            console.error('Error loading flight plan library:', err);
            showToast('Error loading flight plan library: ' + err.message, 'error');

            if (this.files.length > 0) {
                showToast('Showing cached file list. Some files may not be up to date.', 'warning');
                this.renderFileList();
                this.selectAll();
            }
        }
    }

    async checkForDuplicateRoutes(): Promise<void> {
        if (this.files.length === 0) return;

        try {
            const response = await fetch('/validate-same-routes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: this.files.map(f => f.name) }),
            });

            const routeBody: ApiResponse<{
                has_duplicates: boolean;
                duplicate_routes: Array<{ origin: string; destination: string; count: number; files: string[] }>;
            }> = await response.json();

            if (!routeBody.ok) {
                throw new Error(routeBody.error || 'Route validation failed');
            }

            const routeValidation = routeBody.data;

            if (routeValidation.has_duplicates) {
                const duplicateDetails = routeValidation.duplicate_routes
                    .map(route => `${route.origin}-${route.destination} (${route.count} files)`)
                    .join(', ');

                showToast(
                    `Duplicate routes detected: ${duplicateDetails}. Please delete duplicate files before generating schedule.`,
                    'warning',
                );

                this.markDuplicateFiles(routeValidation.duplicate_routes);
                this.disableGenerateScheduleButton(routeValidation.duplicate_routes);
            } else {
                this.enableGenerateScheduleButton();
            }
        } catch (error) {
            console.error('Error checking for duplicate routes:', error);
        }
    }

    private disableGenerateScheduleButton(
        duplicateRoutes: Array<{ origin: string; destination: string; count: number; files: string[] }>,
    ): void {
        const processBtn = document.getElementById('processBtn') as HTMLButtonElement | null;
        if (processBtn) {
            processBtn.disabled = true;
            processBtn.textContent = 'Generate Schedule (Duplicates Detected)';
            processBtn.title = 'Please delete duplicate files before generating schedule';
            processBtn.classList.add('disabled-duplicates');
        }
        this.duplicateRoutes = duplicateRoutes;
    }

    private enableGenerateScheduleButton(): void {
        const processBtn = document.getElementById('processBtn') as HTMLButtonElement | null;
        if (processBtn) {
            processBtn.disabled = false;
            processBtn.textContent = 'Generate Schedule';
            processBtn.title = '';
            processBtn.classList.remove('disabled-duplicates');
        }
        this.duplicateRoutes = null;
    }

    private markDuplicateFiles(
        duplicateRoutes: Array<{ origin: string; destination: string; count: number; files: string[] }>,
    ): void {
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

    renderFileList(): void {
        const emptyState        = document.getElementById('emptyState');
        const fileListContainer = document.getElementById('fileList');
        const selectionBar      = document.getElementById('selectionBar');

        if (this.files.length === 0) {
            if (emptyState)        emptyState.hidden        = false;
            if (fileListContainer) fileListContainer.hidden = true;
            if (selectionBar)      selectionBar.hidden      = true;
            this.updateSelectionSummary();
            return;
        }

        if (emptyState)        emptyState.hidden        = true;
        if (fileListContainer) fileListContainer.hidden  = false;
        if (selectionBar)      selectionBar.hidden       = false;

        if (!fileListContainer) return;
        fileListContainer.innerHTML = '';

        this.files.forEach(file => {
            const filename   = file.name || file.id || '';
            const isSelected = this.selectedFiles.has(filename);
            const validation = this.getFileValidation(filename);
            const isValid    = validation && validation.valid === true;
            const isInvalid  = validation && validation.valid === false && validation.error !== 'Not validated';

            // Route info from the first flight in the validation result
            const firstFlight   = validation && validation.flights && validation.flights[0];
            const origin        = firstFlight?.origin ?? null;
            const destination   = firstFlight?.destination ?? null;
            const routeText     = (origin && destination) ? `${origin} → ${destination}` : 'Route unknown';

            const sizeKb = file.size ? `${Math.round(file.size / 1024)} KB` : '';

            let badgeHtml  = '';
            let badgeClass = '';
            if (isValid) {
                badgeClass = 'file-item-v2__badge--valid';
                badgeHtml  = `<svg aria-label="Valid" role="img" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
            } else if (isInvalid) {
                badgeClass = 'file-item-v2__badge--invalid';
                badgeHtml  = `<svg aria-label="Invalid" role="img" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`;
            } else {
                badgeClass = 'file-item-v2__badge--pending';
                badgeHtml  = `<svg aria-label="Validating" role="img" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
            }

            const itemClasses = ['file-item-v2'];
            if (isSelected) itemClasses.push('file-item-v2--selected');
            if (isInvalid)  itemClasses.push('file-item-v2--invalid');

            const safeFilename = filename.replace(/"/g, '&quot;');
            const checkboxId   = `file-cb-${filename.replace(/[^a-zA-Z0-9]/g, '-')}`;

            const itemEl = document.createElement('div');
            itemEl.className          = itemClasses.join(' ');
            itemEl.dataset.filename   = filename;
            itemEl.setAttribute('role', 'listitem');
            itemEl.innerHTML = `
                <input type="checkbox" class="file-item-v2__checkbox" id="${checkboxId}"
                       aria-label="Select ${safeFilename}"
                       ${isSelected ? 'checked' : ''}>
                <div class="file-item-v2__info">
                    <div class="file-item-v2__name" title="${safeFilename}">${this.escapeHtml(filename)}</div>
                    <div class="file-item-v2__route">${routeText}</div>
                    ${sizeKb ? `<div class="file-item-v2__meta">${sizeKb} · ${formatDate(file.upload_date)}</div>` : ''}
                </div>
                <span class="file-item-v2__badge ${badgeClass}">${badgeHtml}</span>
                <button class="file-item-v2__delete" aria-label="Delete ${safeFilename}" title="Delete file">
                    <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                </button>
            `;

            const checkbox = itemEl.querySelector('.file-item-v2__checkbox') as HTMLInputElement;
            checkbox.addEventListener('change', () => {
                if (checkbox.checked) {
                    this.selectedFiles.add(filename);
                    itemEl.classList.add('file-item-v2--selected');
                } else {
                    this.selectedFiles.delete(filename);
                    itemEl.classList.remove('file-item-v2--selected');
                }
                this.updateSelectionSummary();
                this.checkForDuplicateRoutes();

                typedBus.emit('files:selected', { files: this.getSelectedFilesWithValidation() });
                // Cross-module: Processor subscribes on the shared bus singleton
                bus.emit('files:selected', { files: this.getSelectedFilesWithValidation() });
            });

            const deleteBtn = itemEl.querySelector('.file-item-v2__delete') as HTMLButtonElement;
            deleteBtn.addEventListener('click', (e: Event) => {
                e.stopPropagation();
                this.deleteFile(filename);
            });

            itemEl.addEventListener('click', (e: Event) => {
                const target = e.target as Node;
                if (target === checkbox || target === deleteBtn || deleteBtn.contains(target)) return;
                checkbox.checked = !checkbox.checked;
                checkbox.dispatchEvent(new Event('change'));
            });

            fileListContainer.appendChild(itemEl);
        });

        this.updateSelectionSummary();
    }

    selectAll(): void {
        this.files.forEach(file => this.selectedFiles.add(file.name));
        this.renderFileList();
        typedBus.emit('files:selected', { files: this.getSelectedFilesWithValidation() });
        // Cross-module: Processor subscribes on the shared bus singleton
        bus.emit('files:selected', { files: this.getSelectedFilesWithValidation() });
    }

    selectNone(): void {
        this.selectedFiles.clear();
        this.renderFileList();
        typedBus.emit('files:selected', { files: [] });
        // Cross-module: Processor subscribes on the shared bus singleton
        bus.emit('files:selected', { files: [] });
    }

    async deleteAll(): Promise<void> {
        console.log('[DELETE ALL] Method called');

        if (this.files.length === 0) {
            showToast('No files to delete.', 'warning');
            return;
        }

        const confirmMessage = `Are you sure you want to delete ALL ${this.files.length} files? This action cannot be undone.`;
        if (!confirm(confirmMessage)) {
            console.log('[DELETE ALL] User cancelled');
            return;
        }

        try {
            showToast(`Deleting ${this.files.length} files...`, 'info');

            const response = await fetch('/delete-all-files', {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
            });

            const body: ApiResponse<{ message: string }> = await response.json();
            console.log('[DELETE ALL] Response:', body);

            if (!body.ok) {
                throw new Error(body.error || 'Delete all failed');
            }

            showToast(body.data.message, 'success');
            this.selectedFiles.clear();
            await this.loadFileLibrary();
        } catch (error) {
            const err = error as Error;
            console.error('[DELETE ALL] Error deleting all files:', err);
            showToast(`Error deleting files: ${err.message}`, 'error');
        }
    }

    private updateSelectionSummary(): void {
        const selectedCount = this.selectedFiles.size;
        const totalCount    = this.files.length;
        const selectionBar  = document.getElementById('selectionBar');

        if (this.selectionCount) {
            this.selectionCount.textContent = `${selectedCount} of ${totalCount} selected`;
        }

        if (this.fileCountBadge) {
            this.fileCountBadge.textContent = String(totalCount);
        }

        if (selectionBar) {
            selectionBar.hidden = selectedCount === 0 || totalCount === 0;
        }

        const processBtn = document.getElementById('processBtn') as HTMLButtonElement | null;
        if (processBtn) {
            if (selectedCount === 0) {
                processBtn.disabled = true;
                processBtn.textContent = 'Generate Schedule';
                processBtn.classList.remove('disabled-duplicates');
            } else if (this.duplicateRoutes && this.duplicateRoutes.length > 0) {
                processBtn.disabled = true;
                processBtn.textContent = 'Generate Schedule (Duplicates Detected)';
                processBtn.title = 'Please delete duplicate files before generating schedule';
                processBtn.classList.add('disabled-duplicates');
            } else {
                processBtn.disabled = false;
                processBtn.textContent = 'Generate Schedule';
                processBtn.title = '';
                processBtn.classList.remove('disabled-duplicates');
            }
        }
    }

    getSelectedFiles(): string[] {
        return Array.from(this.selectedFiles);
    }

    getSelectedFilesWithValidation(): Array<{
        filename: string;
        valid: boolean;
        flight_count: number;
        error: string | undefined;
    }> {
        return this.getSelectedFiles().map(filename => {
            const validation = this.getFileValidation(filename);
            return {
                filename,
                valid:        validation.valid,
                flight_count: validation.flight_count ?? 0,
                error:        validation.error,
            };
        });
    }

    async deleteFile(filename: string): Promise<void> {
        if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
            return;
        }

        try {
            console.log(`[DELETE] Attempting to delete file: ${filename}`);

            const response = await fetch(`/delete-file/${encodeURIComponent(filename)}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
            });

            const body: ApiResponse<{ message: string }> = await response.json();
            if (!body.ok) {
                throw new Error(body.error || 'Delete failed');
            }

            console.log(`[DELETE] File deleted successfully: ${filename}`);
            showToast(`File "${filename}" deleted successfully`, 'success');

            this.selectedFiles.delete(filename);
            this.fileValidationCache.delete(filename);

            await this.loadFileLibrary();
            await this.checkForDuplicateRoutes();
        } catch (error) {
            const err = error as Error;
            console.error(`[DELETE] Error deleting file ${filename}:`, err);
            showToast(`Failed to delete file "${filename}": ${err.message}`, 'error');
        }
    }

    private escapeHtml(text: string): string {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
