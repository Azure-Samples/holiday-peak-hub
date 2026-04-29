import { test, expect, type Page } from '@playwright/test';

async function gotoProtectedRoute(
  page: Page,
  path: string,
  redirectPattern: RegExp,
) {
  await page.goto(path, { waitUntil: 'commit' }).catch((error: unknown) => {
    if (!(error instanceof Error) || !error.message.includes('net::ERR_ABORTED')) {
      throw error;
    }
  });

  await expect(page).toHaveURL(redirectPattern);
}

test.describe('critical flows baseline', () => {
  test('supports login and shopper navigation shell', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByRole('heading', { name: 'Welcome to Holiday Peak Hub' })).toBeVisible();

    await page.getByRole('link', { name: 'Browse Products' }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.goto('/shop');
    await expect(page).toHaveURL(/\/shop$/);

    await gotoProtectedRoute(page, '/cart', /\/auth\/login\?redirect=%2Fcart$/);

    await gotoProtectedRoute(page, '/checkout', /\/auth\/login\?redirect=%2Fcheckout$/);
  });

  test('supports staff review shell route', async ({ page }) => {
    await page.goto('/staff/review');
    await expect(page).toHaveURL(/\/auth\/login\?redirect=%2Fstaff%2Freview$/);
  });
});
