import { expect, test } from '@playwright/test';

async function stabilizePage(page: Parameters<typeof test>[0]['page']) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        scroll-behavior: auto !important;
      }
    `,
  });
}

test.describe('visual regression smoke', () => {
  test('captures the executive demo in light mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'light', reducedMotion: 'reduce' });
    await page.goto('/');
    await stabilizePage(page);
    await expect(page).toHaveScreenshot('executive-demo-light.png', { fullPage: false });
  });

  test('captures the executive demo in dark mode', async ({ page }) => {
    await page.emulateMedia({ colorScheme: 'dark', reducedMotion: 'reduce' });
    await page.goto('/');
    await stabilizePage(page);
    await expect(page).toHaveScreenshot('executive-demo-dark.png', { fullPage: false });
  });
});