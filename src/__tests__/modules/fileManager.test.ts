import { describe, it, expect } from 'vitest';
import { formatFileSize, isValidXmlFilename } from '../../modules/fileManager';

describe('FileManager utilities', () => {
    it('formats bytes correctly', () => {
        expect(formatFileSize(1024)).toBe('1.0 KB');
        expect(formatFileSize(1048576)).toBe('1.0 MB');
        expect(formatFileSize(512)).toBe('512 B');
    });

    it('validates XML filenames', () => {
        expect(isValidXmlFilename('plan.xml')).toBe(true);
        expect(isValidXmlFilename('plan.txt')).toBe(false);
        expect(isValidXmlFilename('')).toBe(false);
    });
});
