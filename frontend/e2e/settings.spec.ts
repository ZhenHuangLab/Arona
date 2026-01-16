import { test, expect, type Page, type Route } from '@playwright/test';

async function mockSidebarSessions(page: Page) {
  const handler = async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        sessions: [],
        has_more: false,
        next_cursor: null,
      }),
    });
  };

  await page.route(/\/api\/chat\/sessions(?:\?.*)?$/, handler);
}

async function mockHealth(page: Page, status: number = 200) {
  await page.route('**/health', async (route) => {
    if (status !== 200) {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Service unavailable' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'healthy',
        version: '1.0.0',
        rag_initialized: true,
        models: {},
        timestamp: new Date().toISOString(),
      }),
    });
  });
}

async function mockReady(page: Page, status: number = 200) {
  await page.route('**/ready', async (route) => {
    if (status !== 200) {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not ready' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ready: true,
        status: 'ready',
      }),
    });
  });
}

async function mockConfig(page: Page, status: number = 200) {
  await page.route(/\/api\/config\/.*$/, async (route) => {
    if (status !== 200) {
      await route.fulfill({
        status,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Failed to fetch config' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        backend: { host: 'localhost', port: 8000, cors_origins: ['*'], env_file_loaded: '.env' },
        models: {
          llm: { provider: 'openai', model_name: 'gpt-4', base_url: 'https://api.openai.com/v1' },
          embedding: { provider: 'openai', model_name: 'text-embedding-3-small' },
          reranker: { enabled: false, provider: 'local_gpu', model_name: '' },
        },
        storage: { working_dir: './rag_storage', upload_dir: './uploads' },
        processing: {
          parser: 'mineru',
          enable_image_processing: true,
          enable_table_processing: true,
          enable_equation_processing: true,
        },
      }),
    });
  });
}

test.describe('Settings Modal', () => {
  test.beforeEach(async ({ page }) => {
    await mockSidebarSessions(page);
    await mockHealth(page);
    await mockReady(page);
    await mockConfig(page);
    await page.goto('/chat');
  });

  test('opens and closes settings modal', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Settings & Configuration')).toBeVisible();

    // There are multiple "Close" buttons (icon + footer); click the footer one.
    await page.getByRole('dialog').getByRole('button', { name: 'Close' }).first().click();
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('shows backend health and configuration sections', async ({ page }) => {
    await page.getByRole('button', { name: /settings/i }).click();

    await expect(page.getByRole('heading', { name: 'Backend Health' })).toBeVisible();
    await expect(page.getByText('Health Status', { exact: true })).toBeVisible();
    await expect(page.getByText('Readiness', { exact: true })).toBeVisible();
    await expect(page.getByText('healthy')).toBeVisible();

    await expect(page.getByRole('heading', { name: 'Configuration', exact: true })).toBeVisible();
    await expect(page.getByText('LLM Provider')).toBeVisible();
    await expect(page.getByText('Embedding Model')).toBeVisible();
    await expect(page.getByText(/gpt-4/i)).toBeVisible();
  });

  test('shows error state when backend health endpoints fail', async ({ page }) => {
    // Override health/ready to fail for this test
    await mockHealth(page, 500);
    await mockReady(page, 500);

    await page.getByRole('button', { name: /settings/i }).click();
    await expect(page.getByText(/failed to connect to backend/i)).toBeVisible({ timeout: 5000 });
  });

  test('shows error state when config endpoint fails', async ({ page }) => {
    await mockConfig(page, 500);

    await page.getByRole('button', { name: /settings/i }).click();
    await expect(page.getByText(/failed to load configuration/i)).toBeVisible({ timeout: 5000 });
  });
});
