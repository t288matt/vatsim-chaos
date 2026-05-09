import { describe, it, expect } from 'vitest';
import { calculateElapsedSeconds, isValidTimeFormat } from '../../modules/processor';

describe('Processor utilities', () => {
    it('calculates elapsed seconds correctly', () => {
        const start = Date.now() - 5000; // 5 seconds ago
        const elapsed = calculateElapsedSeconds(start);
        expect(elapsed).toBeGreaterThanOrEqual(4);
        expect(elapsed).toBeLessThanOrEqual(6);
    });

    it('returns 0 for null start time', () => {
        expect(calculateElapsedSeconds(null)).toBe(0);
    });

    it('validates time format correctly', () => {
        expect(isValidTimeFormat('14:00')).toBe(true);
        expect(isValidTimeFormat('09:30')).toBe(true);
        expect(isValidTimeFormat('25:00')).toBe(false);
        expect(isValidTimeFormat('abc')).toBe(false);
        expect(isValidTimeFormat('')).toBe(false);
    });
});
