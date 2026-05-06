import { test } from '@playwright/test';

test('capture baseline screenshots', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await page.screenshot({ path: 'tests/visual/snapshots/baseline-main.png', fullPage: true });
});
