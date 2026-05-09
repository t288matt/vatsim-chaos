// Global Window interface augmentation.
// TypeScript picks up .d.ts files automatically — no import needed in consuming modules.

import type { FileManager } from '../modules/fileManager';

declare global {
    interface Window {
        fileManager: FileManager;
        showToast?: (message: string, type?: string) => void;
    }
}

export {};
