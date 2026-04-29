import { expect, test } from '@playwright/test';

async function loginAsAdmin(page: Parameters<typeof test>[0]['page']) {
  await page.goto('/auth/login?redirect=/admin');
  await page.getByRole('button', { name: /Sign in as Admin/i }).click();
  await expect(page).toHaveURL(/\/admin$/);
}

test.describe('admin cockpit readiness', () => {
  test('launchpad and cockpit tabs load with introspection payloads', async ({ page }) => {
    await loginAsAdmin(page);

    await expect(page.getByText('One cockpit for the full retail agent fleet.')).toBeVisible();
    await expect(page.getByText('All 26 agents')).toBeVisible();

    const fleetLinks = await page
      .locator('a[href^="/admin/"]')
      .evaluateAll((links) => Array.from(new Set(links.map((link) => (link as HTMLAnchorElement).getAttribute('href') || ''))));

    const cockpitLinks = fleetLinks.filter((href) => href.split('/').length === 4);
    expect(cockpitLinks.length).toBeGreaterThanOrEqual(20);
    expect(cockpitLinks).toContain('/admin/ecommerce/catalog');

    await page.goto('/admin/ecommerce/catalog');
    await expect(page.getByRole('tablist', { name: /cockpit views/i })).toBeVisible({ timeout: 15000 });
    await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Prompts' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Tools' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Resilience' })).toBeVisible();

    const dashboardResponse = await page.request.get('/api/admin/ecommerce/catalog?time_range=1h');
    expect(dashboardResponse.ok()).toBeTruthy();
    const dashboardJson = await dashboardResponse.json();

    expect(Array.isArray(dashboardJson.prompt_catalog)).toBeTruthy();
    expect(Array.isArray(dashboardJson.mcp_tools)).toBeTruthy();
    expect(typeof dashboardJson.self_healing).toBe('object');
  });
});