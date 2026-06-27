// App — TypeScript reimplementation of web/static/js/app.js
// Contains the App orchestrator, BriefingManager, and showToast utility.
// NOTE: web/static/js/app.js is intentionally preserved; it is still
// loaded by web/templates/index.html until the HTML migration occurs.

import type { ApiResponse } from '../types/api';

// ---------------------------------------------------------------------------
// showToast — global toast notification helper
// ---------------------------------------------------------------------------

export function showToast(message: string, type = 'success', duration = 4000): void {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        container.setAttribute('role', 'status');
        container.setAttribute('aria-live', 'polite');
        container.setAttribute('aria-atomic', 'false');
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className   = `toast toast--${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
        if (container && !container.children.length) container.remove();
    }, duration);
}

// ---------------------------------------------------------------------------
// BriefingManager — modal, print, and download for the pilot briefing
// ---------------------------------------------------------------------------

export class BriefingManager {
    private modal: HTMLElement | null;
    private content: HTMLElement | null;
    private closeBtn: HTMLElement | null;
    private briefingBtn: HTMLButtonElement | null;
    private printBtn: HTMLElement | null;
    private downloadBtn: HTMLElement | null;
    private _triggerElement: Element | null;
    private _focusTrapHandler: ((e: Event) => void) | null;

    constructor() {
        this.modal       = document.getElementById('briefingModal');
        this.content     = document.getElementById('briefingContent');
        this.closeBtn    = document.querySelector('.close');
        this.briefingBtn = document.getElementById('briefingBtn') as HTMLButtonElement | null;
        this.printBtn    = document.getElementById('printBriefingBtn');
        this.downloadBtn = document.getElementById('downloadBriefingBtn');

        this._triggerElement    = null;
        this._focusTrapHandler  = null;

        this.initializeEventListeners();
        this.checkBriefingAvailability();
    }

    private initializeEventListeners(): void {
        this.briefingBtn?.addEventListener('click',  this.showBriefing.bind(this));
        this.closeBtn?.addEventListener('click',     this.hideBriefing.bind(this));
        this.printBtn?.addEventListener('click',     this.printBriefing.bind(this));
        this.downloadBtn?.addEventListener('click',  this.downloadBriefing.bind(this));

        // Close modal when clicking outside
        window.addEventListener('click', (e: MouseEvent) => {
            if (e.target === this.modal) this.hideBriefing();
        });

        // Close modal with Escape key
        document.addEventListener('keydown', (e: KeyboardEvent) => {
            if (e.key === 'Escape' && this.modal?.style.display === 'block') {
                this.hideBriefing();
            }
        });
    }

    async showBriefing(): Promise<void> {
        // Save the element that triggered the modal so focus can be restored on close
        this._triggerElement = document.activeElement;

        try {
            const response = await fetch('/briefing');
            const body: ApiResponse<{ content: string }> = await response.json();

            if (!body.ok) {
                showToast(body.error || 'Error loading briefing', 'error');
                return;
            }

            const briefing = body.data;

            if (!briefing.content) {
                showToast('No briefing content received', 'error');
                return;
            }

            if (this.content) {
                this.content.innerHTML = `
                    <div class="briefing-content">
                        <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace; font-size: 0.9rem; line-height: 1.4;">${briefing.content}</pre>
                    </div>
                `;
            }

            if (!this.modal) return;
            this.modal.style.display = 'block';

            const mainEl = document.querySelector('main');
            if (mainEl) (mainEl as HTMLElement & { inert: boolean }).inert = true;

            // Focus trap — keep keyboard navigation inside the open modal
            const focusableSelectors =
                'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
            const focusable = Array.from(
                this.modal.querySelectorAll<HTMLElement>(focusableSelectors),
            );
            if (!focusable.length) return;

            const firstFocusable = focusable[0];
            const lastFocusable  = focusable[focusable.length - 1];
            firstFocusable.focus();

            this._focusTrapHandler = (e: Event) => {
                const ke = e as KeyboardEvent;
                if (ke.key !== 'Tab') return;
                if (ke.shiftKey) {
                    if (document.activeElement === firstFocusable) {
                        ke.preventDefault();
                        lastFocusable.focus();
                    }
                } else {
                    if (document.activeElement === lastFocusable) {
                        ke.preventDefault();
                        firstFocusable.focus();
                    }
                }
            };
            this.modal.addEventListener('keydown', this._focusTrapHandler);
        } catch (error) {
            showToast('Error loading briefing: ' + (error as Error).message, 'error');
        }
    }

    hideBriefing(): void {
        if (this.modal) this.modal.style.display = 'none';

        const mainEl = document.querySelector('main');
        if (mainEl) (mainEl as HTMLElement & { inert: boolean }).inert = false;

        // Remove focus trap
        if (this._focusTrapHandler && this.modal) {
            this.modal.removeEventListener('keydown', this._focusTrapHandler);
            this._focusTrapHandler = null;
        }

        // Restore focus to the element that opened the modal
        if (this._triggerElement && 'focus' in this._triggerElement) {
            (this._triggerElement as HTMLElement).focus();
            this._triggerElement = null;
        }
    }

    printBriefing(): void {
        const pre = this.content?.querySelector('pre');
        if (!pre) return;

        const content = pre.textContent ?? '';
        const printWindow = window.open('', '_blank');
        if (!printWindow) return;

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

    downloadBriefing(): void {
        const pre = this.content?.querySelector('pre');
        if (!pre) return;

        const content = pre.textContent ?? '';
        const blob = new Blob([content], { type: 'text/plain' });
        const url  = URL.createObjectURL(blob);
        const a    = document.createElement('a');
        a.href     = url;
        a.download = 'pilot_briefing.txt';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    async checkBriefingAvailability(): Promise<void> {
        try {
            const response = await fetch('/briefing', { method: 'HEAD' });
            if (this.briefingBtn) this.briefingBtn.disabled = !response.ok;
            console.log(`[BRIEFING] Pilot briefing ${response.ok ? 'available — button enabled' : 'not yet available — button disabled'}`);
        } catch (error) {
            console.warn('[BRIEFING] Error checking briefing availability:', error);
            if (this.briefingBtn) this.briefingBtn.disabled = true;
        }
    }
}

