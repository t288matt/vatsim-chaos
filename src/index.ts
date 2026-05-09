import { FileManager } from './modules/fileManager';

console.log('VATSIM-Chaos initialising');

// Instantiate when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const fileManager = new FileManager();
    fileManager.loadFileLibrary();
    window.fileManager = fileManager; // temporary global for Phase 5 transition
});
