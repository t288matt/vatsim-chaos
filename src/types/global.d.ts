// Global Window interface augmentation.
// TypeScript picks up .d.ts files automatically — no import needed in consuming modules.

import type { FileManager } from '../modules/fileManager';

declare global {
    interface Window {
        fileManager: FileManager;
        // showToast is assigned at DOMContentLoaded by src/index.ts.
        // Optional here because FileManager's internal showToast helper guards
        // against the case where the bundle has not yet been initialised (e.g. tests).
        showToast?: (message: string, type?: string) => void;
    }
}

export {};
