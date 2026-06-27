// VATSIM-Chaos entry point — Phase 5 TypeScript bundle
// Instantiates all modules and wires up global references.

import '../web/static/css/main.css';

import { FileManager } from './modules/fileManager';
import { Processor }   from './modules/processor';
import { MapViewer }   from './modules/mapViewer';
import { BriefingManager, showToast } from './modules/app';

console.log('VATSIM-Chaos initialising');

document.addEventListener('DOMContentLoaded', () => {
    const fileManager = new FileManager();
    // Processor, MapViewer, and BriefingManager are constructed for their
    // EventBus subscriptions and DOM event listeners; no further reference needed.
    new Processor();
    new MapViewer();
    new BriefingManager();

    fileManager.loadFileLibrary();

    // Expose minimal globals needed during the HTML migration transition
    window.fileManager = fileManager;
    window.showToast   = showToast;
});
