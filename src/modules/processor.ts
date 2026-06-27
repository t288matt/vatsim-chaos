// Processor — TypeScript reimplementation of web/static/js/processor.js
// Handles the analysis workflow and progress tracking.
// NOTE: web/static/js/processor.js is intentionally preserved; it is still
// loaded by web/templates/index.html until the HTML migration occurs.

import { bus } from './eventBus';
import { showToast } from './app';
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
    private hideTimeout: ReturnType<typeof setTimeout> | null;
    private mapRefreshTimeout: ReturnType<typeof setTimeout> | null;
    private _processingButtonText = 'Generate Schedule';

    // Cache of the latest files:selected payload from FileManager
    private selectedFiles: SelectedFile[] = [];
    private _hasDuplicates = false;
    private _eventSource: EventSource | null = null;
    private _unsubscribeFilesSelected: (() => void) | null = null;
    private _unsubscribeDuplicatesDetected: (() => void) | null = null;

    constructor() {
        this.processBtn    = document.getElementById('processBtn') as HTMLButtonElement | null;
        this.processPanel  = document.getElementById('processPanel');

        this.isProcessing        = false;
        this.statusCheckInterval = null;
        this.processingStartTime = null;

        this.hideTimeout         = null;
        this.mapRefreshTimeout   = null;

        // Subscribe to file selection changes from FileManager via the shared bus;
        // store the unsubscribe token so repeated instantiations don't accumulate listeners
        this._unsubscribeFilesSelected = bus.on('files:selected', (payload: { files: SelectedFile[] }) => {
            this.selectedFiles = payload.files;
            this.updateButtonState();
        });

        this._unsubscribeDuplicatesDetected = bus.on('duplicates:detected', ({ hasDuplicates }) => {
            this._hasDuplicates = hasDuplicates;
            this.updateButtonState();
        });

        this.initializeEventListeners();
    }

    private initializeEventListeners(): void {
        this.processBtn?.addEventListener('click', this.startProcessing.bind(this));
    }

    private showMessage(message: string, type = 'info'): void {
        showToast(message, type);
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

    monitorProgress(): void {
        const es = new EventSource('/status-stream');
        this._eventSource = es;

        es.onmessage = (e: MessageEvent) => {
            try {
                const status: ProcessingStatus = JSON.parse(e.data as string);

                if (
                    this.processingStartTime !== null &&
                    Date.now() - this.processingStartTime > this.maxProcessingTime
                ) {
                    es.close();
                    this._eventSource = null;
                    this.handleProcessingTimeout();
                    return;
                }

                const elapsed = calculateElapsedSeconds(this.processingStartTime);
                const elapsedEl = document.getElementById('elapsedTime');
                if (elapsedEl) elapsedEl.textContent = `${elapsed}s elapsed`;

                const currentStep = status.current_step ?? -1;
                document.querySelectorAll('.step-timeline__item').forEach((el, i) => {
                    el.classList.toggle('step-timeline__item--done',   i < currentStep);
                    el.classList.toggle('step-timeline__item--active', i === currentStep);
                    const statusEl = el.querySelector('.step-timeline__status');
                    if (statusEl) {
                        if (i < currentStep)        statusEl.textContent = 'Done';
                        else if (i === currentStep) statusEl.textContent = 'Running…';
                        else                        statusEl.textContent = '';
                    }
                });

                if (status.completed) {
                    es.close();
                    this._eventSource = null;
                    this.handleProcessingComplete();
                } else if (status.failed) {
                    es.close();
                    this._eventSource = null;
                    this.handleProcessingError(status.error ?? 'Unknown error');
                }
            } catch (err) {
                console.error('[PROCESSOR] Error parsing SSE message:', err);
            }
        };

        es.onerror = () => {
            es.close();
            this._eventSource = null;
            this.handleProcessingError('Lost connection to server during processing');
        };
    }

    handleProcessingTimeout(): void {
        const errorMessage = 'Processing timed out after 5 minutes. The operation may still be running in the background.';
        this.handleProcessingError(errorMessage);
        this.showMessage(
            'Check the server logs for more details. You can try processing again with fewer files.',
            'warning',
        );
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

        await this.startProcessing();
    }

    resetProcessingState(): void {
        this.isProcessing        = false;
        this.processingStartTime = null;


        // Restore button to original state
        if (this.processBtn) {
            this.processBtn.classList.remove('btn--loading');
            this.processBtn.disabled    = false;
            this.processBtn.textContent = this._processingButtonText;
            this.processBtn.setAttribute('aria-busy', 'false');
            console.assert(!this.processBtn.disabled, 'processBtn.disabled must be false when btn--loading class is removed');
        }

        // Clear all pending timeouts
        if (this._eventSource) {
            this._eventSource.close();
            this._eventSource = null;
        }
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

    private updateButtonState(): void {
        if (!this.processBtn || this.isProcessing) return;
        if (this.selectedFiles.length === 0) {
            this.processBtn.disabled = true;
            this.processBtn.textContent = 'Generate Schedule';
            this.processBtn.title = '';
            this.processBtn.classList.remove('disabled-duplicates');
        } else if (this._hasDuplicates) {
            this.processBtn.disabled = true;
            this.processBtn.textContent = 'Generate Schedule (Duplicates Detected)';
            this.processBtn.title = 'Please delete duplicate files before generating schedule';
            this.processBtn.classList.add('disabled-duplicates');
        } else {
            this.processBtn.disabled = false;
            this.processBtn.textContent = 'Generate Schedule';
            this.processBtn.title = '';
            this.processBtn.classList.remove('disabled-duplicates');
        }
    }

    /** Unsubscribe from all bus events and clear pending timers. Call when the instance is no longer needed. */
    destroy(): void {
        if (this._unsubscribeFilesSelected) {
            this._unsubscribeFilesSelected();
            this._unsubscribeFilesSelected = null;
        }
        if (this._unsubscribeDuplicatesDetected) {
            this._unsubscribeDuplicatesDetected();
            this._unsubscribeDuplicatesDetected = null;
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
    } {
        return {
            isProcessing:   this.isProcessing,
            selectedFiles:  this.selectedFiles,
            processingTime: calculateElapsedSeconds(this.processingStartTime),
        };
    }
}
