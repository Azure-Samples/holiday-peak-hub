import { test, expect } from '@playwright/test';

test.describe('critical flows baseline', () => {
  test('supports login and shopper navigation shell', async ({ page }) => {
    await page.goto('/auth/login');
    await expect(page.getByRole('heading', { name: 'Welcome to Holiday Peak Hub' })).toBeVisible();

    await page.getByRole('link', { name: 'Browse Products' }).click();
    await expect(page).toHaveURL(/\/$/);

    await page.goto('/shop');
    await expect(page).toHaveURL(/\/category\?slug=all$/);

    await page.goto('/cart');
    await expect(page).toHaveURL(/\/auth\/login\?redirect=%2Fcart$/);

    await page.goto('/checkout');
    await expect(page).toHaveURL(/\/auth\/login\?redirect=%2Fcheckout$/);
  });

  test('supports staff review shell route', async ({ page }) => {
    await page.goto('/staff/review');
    await expect(page).toHaveURL(/\/auth\/login\?redirect=%2Fstaff%2Freview$/);
  });
});
