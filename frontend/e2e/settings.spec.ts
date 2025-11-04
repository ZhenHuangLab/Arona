import { test, expect } from '@playwright/test';

test.describe('Settings Modal', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');

    // Mock health check API
    await page.route('**/health', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
        }),
      });
    });

    // Mock config API
    await page.route('**/api/config/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          llm: {
            provider: 'openai',
            model: 'gpt-4',
            api_key: '***',
            base_url: 'https://api.openai.com/v1',
          },
          embedding: {
            provider: 'openai',
            model: 'text-embedding-3-small',
          },
          working_dir: './rag_storage',
        }),
      });
    });
  });

  test('opens settings modal', async ({ page }) => {
    // Click settings button (gear icon)
    await page.getByRole('button', { name: /settings/i }).click();

    // Modal should be visible
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText(/settings/i)).toBeVisible();
  });

  test('displays health status tab', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();

    // Click on Health tab
    await page.getByRole('tab', { name: /health/i }).click();

    // Should show health status
    await expect(page.getByText(/status/i)).toBeVisible();
    await expect(page.getByText(/healthy/i)).toBeVisible();
  });

  test('displays configuration tab', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();

    // Click on Configuration tab
    await page.getByRole('tab', { name: /configuration/i }).click();

    // Should show config details
    await expect(page.getByText(/llm/i)).toBeVisible();
    await expect(page.getByText(/embedding/i)).toBeVisible();
  });

  test('closes settings modal with close button', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();

    // Modal should be visible
    await expect(page.getByRole('dialog')).toBeVisible();

    // Click close button
    await page.getByRole('button', { name: /close/i }).click();

    // Modal should be hidden
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('closes settings modal with Escape key', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();

    // Modal should be visible
    await expect(page.getByRole('dialog')).toBeVisible();

    // Press Escape
    await page.keyboard.press('Escape');

    // Modal should be hidden
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('displays LLM configuration details', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();
    await page.getByRole('tab', { name: /configuration/i }).click();

    // Should show LLM details
    await expect(page.getByText(/openai/i)).toBeVisible();
    await expect(page.getByText(/gpt-4/i)).toBeVisible();
  });

  test('displays embedding configuration details', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();
    await page.getByRole('tab', { name: /configuration/i }).click();

    // Should show embedding details
    await expect(page.getByText(/text-embedding-3-small/i)).toBeVisible();
  });

  test('handles health check errors', async ({ page }) => {
    // Override health check to return error
    await page.route('**/health', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Service unavailable',
        }),
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /settings/i }).click();
    await page.getByRole('tab', { name: /health/i }).click();

    // Should show error state
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 5000 });
  });

  test('handles config fetch errors', async ({ page }) => {
    // Override config to return error
    await page.route('**/api/config/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Failed to fetch config',
        }),
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /settings/i }).click();
    await page.getByRole('tab', { name: /configuration/i }).click();

    // Should show error state
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 5000 });
  });

  test('refreshes health status', async ({ page }) => {
    let callCount = 0;

    await page.route('**/health', async (route) => {
      callCount++;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'healthy',
          timestamp: new Date().toISOString(),
          call: callCount,
        }),
      });
    });

    await page.goto('/');
    await page.getByRole('button', { name: /settings/i }).click();
    await page.getByRole('tab', { name: /health/i }).click();

    // Click refresh button if available
    const refreshButton = page.getByRole('button', { name: /refresh/i });
    if (await refreshButton.isVisible()) {
      await refreshButton.click();
      
      // Should have made multiple calls
      expect(callCount).toBeGreaterThan(1);
    }
  });

  test('switches between tabs', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();

    // Start on Health tab
    await page.getByRole('tab', { name: /health/i }).click();
    await expect(page.getByText(/status/i)).toBeVisible();

    // Switch to Configuration tab
    await page.getByRole('tab', { name: /configuration/i }).click();
    await expect(page.getByText(/llm/i)).toBeVisible();

    // Switch back to Health tab
    await page.getByRole('tab', { name: /health/i }).click();
    await expect(page.getByText(/status/i)).toBeVisible();
  });
});

