import { test, expect } from '@playwright/test';

test('no visual regression after CSS variables', async ({ page }) => {
    await page.goto('http://localhost:5000');
    await expect(page).toHaveScreenshot('main-after-variables.png', {
        maxDiffPixelRatio: 0.02
    });
});
