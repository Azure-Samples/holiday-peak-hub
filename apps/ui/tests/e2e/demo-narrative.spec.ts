import { expect, test } from '@playwright/test';

test.describe('executive demo narrative', () => {
  test('keeps the scene arc and enriched drawer reachable', async ({ page }) => {
    await page.goto('/');

    await expect(page.getByText('Search p95')).toBeVisible();
    await expect(page.getByText('Choose the story you want to prove next')).toBeVisible();

    const firstProfileButton = page.getByRole('button', { name: /Open profile for/i }).first();
    await firstProfileButton.click();

    await expect(page.getByText('Interface Contract')).toBeVisible();
    await expect(page.getByText('Mini Playground')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Open trace explorer' })).toBeVisible();
  });
});