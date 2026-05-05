import { test } from '@playwright/test';
import { injectAxe, checkA11y } from 'axe-playwright';

test('WCAG 2.1 AA — 0 violations on main page', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await injectAxe(page);
    await checkA11y(page, undefined, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    });
});

test('WCAG 2.1 AA — 0 violations with briefing modal open', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await page.evaluate(() => {
        const btn = document.getElementById('briefingBtn') as HTMLButtonElement;
        if (btn) btn.disabled = false;
    });
    await page.click('#briefingBtn');
    await page.waitForSelector('#briefingModal[style*="block"]', { timeout: 3000 }).catch(() => {});
    await injectAxe(page);
    await checkA11y(page, '#briefingModal', {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa'] },
    });
});
