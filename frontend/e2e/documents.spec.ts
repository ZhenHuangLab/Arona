import { test, expect, type Page, type Route } from '@playwright/test';

async function mockSidebarSessions(page: Page) {
  // Sidebar always loads sessions (even on /documents/* routes)
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

async function mockConfig(page: Page) {
  await page.route(/\/api\/config\/.*$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        backend: { host: 'localhost', port: 8000, cors_origins: ['*'], env_file_loaded: '.env' },
        models: {
          llm: { provider: 'openai', model_name: 'gpt-4' },
          embedding: { provider: 'openai', model_name: 'text-embedding-3-small' },
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

async function mockDocumentDetails(page: Page, docs: Array<{ filename: string }> = []) {
  await page.route('**/api/documents/details', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        documents: docs.map((d) => ({
          filename: d.filename,
          file_path: `/uploads/${d.filename}`,
          file_size: 1024,
          upload_date: new Date().toISOString(),
          status: 'indexed',
          storage_location: '/uploads',
        })),
        total: docs.length,
      }),
    });
  });
}

async function mockGraph(page: Page) {
  await page.route('**/api/graph/data**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        nodes: [{ id: '1', label: 'Node 1', type: 'entity' }],
        edges: [],
        stats: { total_nodes: 1, total_edges: 0 },
      }),
    });
  });

  await page.route('**/api/graph/stats**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ total_nodes: 1, total_edges: 0 }),
    });
  });
}

test.describe('Documents', () => {
  test.beforeEach(async ({ page }) => {
    await mockSidebarSessions(page);
    await mockConfig(page);
    await mockGraph(page);
  });

  test('navigates to Document Library from sidebar', async ({ page }) => {
    await mockDocumentDetails(page, []);
    await page.goto('/chat');

    await page.locator('aside').getByRole('link', { name: 'Documents' }).click();
    await expect(page).toHaveURL(/\/documents\/library/);
    await expect(page.getByRole('heading', { name: 'Library' })).toBeVisible();
  });

  test('shows upload UI', async ({ page }) => {
    await mockDocumentDetails(page, []);
    // Upload is integrated into the Library page via a dialog.
    await page.goto('/documents/library');
    await page.getByRole('button', { name: 'Upload', exact: true }).click();

    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('heading', { name: /upload documents/i })).toBeVisible();
    await expect(page.getByText('Drop files here or click to browse')).toBeVisible();
    // The uploader uses a <label> styled as a button (via Button asChild)
    await expect(page.getByText('Select Files')).toBeVisible();
  });

  test('lists documents from /api/documents/details', async ({ page }) => {
    await mockDocumentDetails(page, [{ filename: 'doc1.pdf' }, { filename: 'doc2.txt' }]);

    await page.goto('/documents/library');
    await expect(page.getByText('doc1.pdf')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('doc2.txt')).toBeVisible({ timeout: 5000 });
  });

  test('renders graph canvas', async ({ page }) => {
    await mockDocumentDetails(page, []);
    await page.goto('/documents/graph');
    await expect(page.locator('canvas')).toBeVisible({ timeout: 5000 });
  });
});
