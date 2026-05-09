// Processor — TypeScript reimplementation of web/static/js/processor.js
// Handles the analysis workflow and progress tracking.
// NOTE: web/static/js/processor.js is intentionally preserved; it is still
// loaded by web/templates/index.html until the HTML migration occurs.

import { bus } from './eventBus';
import type { ApiResponse, ProcessingStatus } from '../types/api';

// ---------------------------------------------------------------------------
// Shared selected-file shape (mirrors FileManager's emit payload)
// ---------------------------------------------------------------------------

export interface SelectedFile {
    filename: string;
    valid: boolean;
    flight_count: number;
    error?: string;
}

// ---------------------------------------------------------------------------
// Exported utility functions (tested by Vitest)
// ---------------------------------------------------------------------------

/**
 * Returns the number of whole seconds elapsed since `startTime` (ms epoch).
 * Returns 0 when `startTime` is null.
 */
export function calculateElapsedSeconds(startTime: number | null): number {
    if (startTime === null) return 0;
    return Math.floor((Date.now() - startTime) / 1000);
}

/**
 * Returns true when `time` matches HH:MM with valid hour (0–23) and minute
 * (0–59).  Returns false for an empty string.
 */
export function isValidTimeFormat(time: string): boolean {
    if (!time) return false;
    const match = time.match(/^(\d{2}):(\d{2})$/);
    if (!match) return false;
    const hours = parseInt(match[1], 10);
    const minutes = parseInt(match[2], 10);
    return hours >= 0 && hours <= 23 && minutes >= 0 && minutes <= 59;
}

// ---------------------------------------------------------------------------
// Processor class
// ---------------------------------------------------------------------------

export class Processor {
    private processBtn: HTMLButtonElement | null;
    private processPanel: HTMLElement | null;

    private isProcessing: boolean;
    private statusCheckInterval: ReturnType<typeof setTimeout> | null;
    private processingStartTime: number | null;
    private readonly maxProcessingTime = 300_000; // 5 minutes
    private retryCount: number;
    private readonly maxRetries = 3;
    private hideTimeout: ReturnType<typeof setTimeout> | null;
    private mapRefreshTimeout: ReturnType<typeof setTimeout> | null;
    private _processingButtonText = 'Generate Schedule';

    // Cache of the latest files:selected payload from FileManager
    private selectedFiles: SelectedFile[] = [];
    private _unsubscribeFilesSelected: (() => void) | null = null;

    constructor() {
        this.processBtn    = document.getElementById('processBtn') as HTMLButtonElement | null;
        this.processPanel  = document.getElementById('processPanel');

        this.isProcessing        = false;
        this.statusCheckInterval = null;
        this.processingStartTime = null;
        this.retryCount          = 0;
        this.hideTimeout         = null;
        this.mapRefreshTimeout   = null;

        // Subscribe to file selection changes from FileManager via the shared bus;
        // store the unsubscribe token so repeated instantiations don't accumulate listeners
        this._unsubscribeFilesSelected = bus.on('files:selected', (payload: { files: SelectedFile[] }) => {
            this.selectedFiles = payload.files;
        });

        this.initializeEventListeners();
    }

    private initializeEventListeners(): void {
        this.processBtn?.addEventListener('click', this.startProcessing.bind(this));
    }

    private showMessage(message: string, type = 'info'): void {
        if (typeof window !== 'undefined' && typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            console.log(`[${type.toUpperCase()}] ${message}`);
        }
    }

    async startProcessing(): Promise<void> {
        if (this.isProcessing) {
            this.showMessage('Processing already in progress. Please wait.', 'warning');
            return;
        }

        const selectedFiles = this.selectedFiles;
        if (selectedFiles.length === 0) {
            this.showMessage('Please select at least one XML file to process.', 'warning');
            return;
        }

        // Edge case: check processing prerequisites
        const validationResults = await this.validateProcessingPrerequisites(selectedFiles);
        if (!validationResults.canProcess) {
            this.showMessage(validationResults.error ?? 'Cannot process files.', 'error');
            return;
        }

        this.isProcessing        = true;
        this.processingStartTime = Date.now();
        this.retryCount          = 0;

        // Store original button text as instance property
        this._processingButtonText = this.processBtn?.textContent ?? 'Generate Schedule';

        // Add loading state to button
        if (this.processBtn) {
            this.processBtn.classList.add('btn--loading');
            this.processBtn.disabled = true;
            this.processBtn.textContent = 'Generating…';
            this.processBtn.setAttribute('aria-busy', 'true');
            console.assert(this.processBtn.disabled, 'processBtn.disabled must be true when btn--loading class is added');
        }

        // Show process panel and reset timeline
        if (this.processPanel) this.processPanel.hidden = false;
        document.querySelectorAll('.step-timeline__item').forEach(el => {
            el.classList.remove('step-timeline__item--done', 'step-timeline__item--active');
            const statusEl = el.querySelector('.step-timeline__status');
            if (statusEl) statusEl.textContent = '';
        });
        const elapsedEl = document.getElementById('elapsedTime');
        if (elapsedEl) elapsedEl.textContent = '0s elapsed';
        this.showMessage('Processing started', 'info');

        try {
            const startTimeInput = (document.getElementById('startTime') as HTMLInputElement | null)?.value ?? '14:00';
            const endTimeInput   = (document.getElementById('endTime')   as HTMLInputElement | null)?.value ?? '18:00';

            // Validate time inputs
            const startTimeValue = isValidTimeFormat(startTimeInput) ? startTimeInput : '14:00';
            const endTimeValue   = isValidTimeFormat(endTimeInput)   ? endTimeInput   : '18:00';

            const response = await fetch('/process', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    files:     selectedFiles.map(f => f.filename),
                    startTime: startTimeValue,
                    endTime:   endTimeValue,
                }),
            });

            const body: ApiResponse<unknown> = await response.json();
            if (!body.ok) {
                throw new Error(body.error || 'Processing failed');
            }

            this.showMessage('Processing started successfully!', 'success');
            this.monitorProgress();
        } catch (error) {
            this.handleProcessingError((error as Error).message);
        }
    }

    async validateProcessingPrerequisites(
        selectedFiles: SelectedFile[],
    ): Promise<{ canProcess: boolean; error?: string }> {
        // Edge case: check if files are valid
        const invalidFiles = selectedFiles.filter(file => !file.valid);
        if (invalidFiles.length > 0) {
            const invalidNames = invalidFiles.map(f => f.filename).join(', ');
            return { canProcess: false, error: `Cannot process invalid files: ${invalidNames}` };
        }

        // Edge case: too many files selected
        if (selectedFiles.length > 100) {
            return { canProcess: false, error: 'Too many files selected. Please select 100 or fewer files.' };
        }

        // Edge case: files with no flights
        const emptyFiles = selectedFiles.filter(file => file.flight_count === 0);
        if (emptyFiles.length > 0) {
            const emptyNames = emptyFiles.map(f => f.filename).join(', ');
            const proceed = confirm(
                `Warning: Files with no flights detected: ${emptyNames}\n\nDo you want to continue processing?`,
            );
            if (!proceed) {
                return { canProcess: false, error: 'Processing cancelled by user.' };
            }
        }

        // Edge case: duplicate origin-destination pairs
        try {
            const response = await fetch('/validate-same-routes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ files: selectedFiles.map(f => f.filename) }),
            });

            const routeBody: ApiResponse<{
                has_duplicates: boolean;
                duplicate_routes: Array<{ origin: string; destination: string; count: number; files: string[] }>;
            }> = await response.json();

            if (!routeBody.ok) {
                throw new Error(routeBody.error || 'Route validation failed');
            }

            if (routeBody.data.has_duplicates) {
                this.showMessage('⚠️ Please delete duplicate files before generating schedule.', 'error');
                return {
                    canProcess: false,
                    error: 'Processing blocked due to duplicate routes. Please delete duplicates first.',
                };
            }
        } catch (error) {
            console.error('Route validation error:', error);
            this.showMessage(
                'Warning: Could not validate routes. Processing may fail if duplicate routes exist.',
                'warning',
            );
        }

        // Edge case: large files
        const largeFiles = selectedFiles.filter(
            // `size` is not part of SelectedFile — skip check gracefully
            (file): boolean => (file as SelectedFile & { size?: number }).size !== undefined &&
                               ((file as SelectedFile & { size?: number }).size ?? 0) > 10 * 1024 * 1024,
        );
        if (largeFiles.length > 0) {
            const largeNames = largeFiles.map(f => f.filename).join(', ');
            const proceed = confirm(
                `Large files detected: ${largeNames}\n\nProcessing may take longer than usual. Continue?`,
            );
            if (!proceed) {
                return { canProcess: false, error: 'Processing cancelled by user.' };
            }
        }

        return { canProcess: true };
    }

    async monitorProgress(): Promise<void> {
        const checkStatus = async (): Promise<void> => {
            try {
                // Edge case: check for processing timeout
                if (
                    this.processingStartTime !== null &&
                    Date.now() - this.processingStartTime > this.maxProcessingTime
                ) {
                    this.handleProcessingTimeout();
                    return;
                }

                const response = await fetch('/status');
                const statusBody: ApiResponse<ProcessingStatus> = await response.json();
                if (!statusBody.ok) {
                    throw new Error(statusBody.error || `HTTP ${response.status}`);
                }
                const status = statusBody.data;

                // Update elapsed time display
                const elapsed = calculateElapsedSeconds(this.processingStartTime);
                const elapsedEl = document.getElementById('elapsedTime');
                if (elapsedEl) elapsedEl.textContent = `${elapsed}s elapsed`;

                // Update step timeline indicators
                const currentStep = status.current_step ?? -1;
                const stepItems = document.querySelectorAll('.step-timeline__item');
                stepItems.forEach((el, i) => {
                    el.classList.toggle('step-timeline__item--done',   i < currentStep);
                    el.classList.toggle('step-timeline__item--active', i === currentStep);
                    const statusEl = el.querySelector('.step-timeline__status');
                    if (statusEl) {
                        if (i < currentStep)      statusEl.textContent = 'Done';
                        else if (i === currentStep) statusEl.textContent = 'Running…';
                        else                       statusEl.textContent = '';
                    }
                });

                if (status.completed) {
                    this.handleProcessingComplete();
                } else if (status.failed) {
                    this.handleProcessingError(status.error ?? 'Unknown error');
                } else {
                    // Continue monitoring — exponential backoff up to 15 s
                    const delay = Math.min(3000 * Math.pow(1.5, this.retryCount), 15_000);
                    this.statusCheckInterval = setTimeout(checkStatus, delay);
                }
            } catch (error) {
                console.error('Status check error:', error);
                this.retryCount++;

                if (this.retryCount >= this.maxRetries) {
                    await this.checkForCompletedProcessing();
                } else {
                    // Exponential backoff for retries (3 s base)
                    const delay = Math.min(3000 * Math.pow(2, this.retryCount), 20_000);
                    this.statusCheckInterval = setTimeout(checkStatus, delay);
                }
            }
        };

        checkStatus();
    }

    async checkForCompletedProcessing(): Promise<void> {
        console.log('[PROCESSING] Status tracking failed, checking for completed processing…');

        try {
            const filesToCheck = [
                '/temp/potential_conflict_data.json',
                '/animation/animation_data.json',
                '/animation/conflict_points.json',
                '/merged_flightplans.kml',
                '/pilot_briefing.txt',
            ];

            let completedFiles = 0;
            const totalFiles = filesToCheck.length;

            for (const file of filesToCheck) {
                try {
                    const response = await fetch(file);
                    if (response.ok) completedFiles++;
                } catch (e) {
                    console.warn(`File check failed for ${file}:`, e);
                }
            }

            const completionRatio = completedFiles / totalFiles;
            console.log(
                `[PROCESSING] Found ${completedFiles}/${totalFiles} output files (${Math.round(completionRatio * 100)}% completion)`,
            );

            if (completionRatio >= 0.3) {
                console.log('[PROCESSING] Sufficient output files found — processing complete');
                this.handleProcessingComplete();
            } else {
                console.log('[PROCESSING] Insufficient output files — processing may have failed');
            }
        } catch (error) {
            console.error('[PROCESSING] Error checking for completed processing:', error);
        }
    }

    handleProcessingTimeout(): void {
        const errorMessage = 'Processing timed out after 5 minutes. The operation may still be running in the background.';
        this.handleProcessingError(errorMessage);
        this.showMessage(
            'Check the server logs for more details. You can try processing again with fewer files.',
            'warning',
        );
    }

    async determineActualProgress(): Promise<number | null> {
        try {
            const fileChecks = [
                { step: 0, files: ['/temp/FLT0001_data.json'] },
                { step: 1, files: ['/temp/potential_conflict_data.json'] },
                { step: 2, files: ['/merged_flightplans.kml'] },
                { step: 3, files: ['/temp/routes_with_added_interpolated_points.json'] },
                { step: 4, files: ['/animation/animation_data.json'] },
                { step: 5, files: ['/pilot_briefing.txt'] },
            ];

            let lastCompletedStep = -1;

            for (const check of fileChecks) {
                let stepCompleted = true;
                for (const file of check.files) {
                    try {
                        const response = await fetch(file);
                        if (!response.ok) { stepCompleted = false; break; }
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

    async checkDataFilesExist(): Promise<boolean> {
        try {
            const filesToCheck = [
                '/temp/routes_with_added_interpolated_points.json',
                '/animation/animation_data.json',
                '/animation/conflict_points.json',
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

    handleProcessingComplete(): void {
        const processingTime = calculateElapsedSeconds(this.processingStartTime);

        console.log(`[PROCESSOR] Processing completed successfully in ${processingTime} seconds`);
        this.resetProcessingState();

        // Mark all steps complete
        document.querySelectorAll('.step-timeline__item').forEach(el => {
            el.classList.add('step-timeline__item--done');
            el.classList.remove('step-timeline__item--active');
            const statusEl = el.querySelector('.step-timeline__status');
            if (statusEl) statusEl.textContent = 'Done';
        });

        const statusRegion = document.getElementById('processingStatus');
        if (statusRegion) statusRegion.textContent = 'Processing complete.';

        this.showMessage('Processing complete — pilot briefing ready', 'success');

        // Enable briefing button
        const briefingBtn = document.getElementById('briefingBtn') as HTMLButtonElement | null;
        if (briefingBtn) briefingBtn.disabled = false;

        // Emit on shared bus so MapViewer can respond
        bus.emit('processing:completed', { processingTime });

        // Hide process panel after 3 seconds
        this.hideTimeout = setTimeout(() => {
            if (this.processPanel) this.processPanel.hidden = true;
            if (statusRegion) statusRegion.textContent = '';
        }, 3000);
    }

    handleProcessingError(error: string): void {
        this.showMessage('Processing failed: ' + error, 'error');
        this.resetProcessingState();

        // Show error on the currently active step
        document.querySelectorAll('.step-timeline__item--active').forEach(el => {
            el.classList.remove('step-timeline__item--active');
            el.classList.add('step-timeline__item--failed');
            const statusEl = el.querySelector('.step-timeline__status');
            if (statusEl) statusEl.textContent = 'Failed';
        });

        const statusRegion = document.getElementById('processingStatus');
        if (statusRegion) statusRegion.textContent = 'Processing failed.';

        // Hide panel after 5 seconds; store token so a retry can cancel it first
        this.hideTimeout = window.setTimeout(() => {
            if (this.processPanel) this.processPanel.hidden = true;
            if (statusRegion) statusRegion.textContent = '';
        }, 5000);
    }

    async retryProcessing(): Promise<void> {
        if (this.isProcessing) {
            this.showMessage('Processing already in progress.', 'warning');
            return;
        }

        this.retryCount = 0;
        await this.startProcessing();
    }

    resetProcessingState(): void {
        this.isProcessing        = false;
        this.processingStartTime = null;
        this.retryCount          = 0;

        // Restore button to original state
        if (this.processBtn) {
            this.processBtn.classList.remove('btn--loading');
            this.processBtn.disabled    = false;
            this.processBtn.textContent = this._processingButtonText;
            this.processBtn.setAttribute('aria-busy', 'false');
            console.assert(!this.processBtn.disabled, 'processBtn.disabled must be false when btn--loading class is removed');
        }

        // Clear all pending timeouts
        if (this.statusCheckInterval) {
            clearTimeout(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }
        if (this.mapRefreshTimeout) {
            clearTimeout(this.mapRefreshTimeout);
            this.mapRefreshTimeout = null;
        }
    }

    /** Unsubscribe from all bus events and clear pending timers. Call when the instance is no longer needed. */
    destroy(): void {
        if (this._unsubscribeFilesSelected) {
            this._unsubscribeFilesSelected();
            this._unsubscribeFilesSelected = null;
        }
        if (this.statusCheckInterval) {
            clearTimeout(this.statusCheckInterval);
        }
    }

    /** Returns a snapshot of current processing state. */
    getProcessingStatus(): {
        isProcessing: boolean;
        selectedFiles: SelectedFile[];
        processingTime: number;
        retryCount: number;
    } {
        return {
            isProcessing:   this.isProcessing,
            selectedFiles:  this.selectedFiles,
            processingTime: calculateElapsedSeconds(this.processingStartTime),
            retryCount:     this.retryCount,
        };
    }
}
