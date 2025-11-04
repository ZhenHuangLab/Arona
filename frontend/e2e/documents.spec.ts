import { test, expect } from '@playwright/test';
import path from 'path';

test.describe('Document Management', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('navigates to document upload view', async ({ page }) => {
    // Click on Documents navigation
    await page.getByRole('link', { name: /documents/i }).click();

    // Should show upload interface
    await expect(page.getByText(/drag & drop files/i)).toBeVisible();
  });

  test('displays file upload area', async ({ page }) => {
    await page.goto('/documents/upload');

    // Check for upload elements
    await expect(page.getByText(/drag & drop files/i)).toBeVisible();
    await expect(page.getByText(/or click to browse/i)).toBeVisible();
  });

  test('uploads a file successfully', async ({ page }) => {
    await page.goto('/documents/upload');

    // Mock the upload API
    await page.route('**/api/documents/upload-and-process', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          filename: 'test.pdf',
          file_path: '/uploads/test.pdf',
          status: 'success',
          message: 'Document processed successfully',
          chunks_created: 10,
        }),
      });
    });

    // Create a test file
    const fileContent = 'This is a test PDF content';
    const buffer = Buffer.from(fileContent);

    // Upload file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer,
    });

    // Should show success message
    await expect(page.getByText(/success/i)).toBeVisible({ timeout: 5000 });
  });

  test('shows upload progress', async ({ page }) => {
    await page.goto('/documents/upload');

    // Mock upload with delay
    await page.route('**/api/documents/upload-and-process', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 500));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          filename: 'test.pdf',
          file_path: '/uploads/test.pdf',
          status: 'success',
          message: 'Document processed successfully',
          chunks_created: 10,
        }),
      });
    });

    const fileContent = 'Test content';
    const buffer = Buffer.from(fileContent);

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer,
    });

    // Should show uploading state
    await expect(page.getByText(/uploading/i)).toBeVisible();
  });

  test('validates file type', async ({ page }) => {
    await page.goto('/documents/upload');

    // Try to upload an invalid file type
    const buffer = Buffer.from('Invalid file');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.jpg',
      mimeType: 'image/jpeg',
      buffer,
    });

    // Should show error message
    await expect(page.getByText(/file type not supported/i)).toBeVisible();
  });

  test('navigates to document library', async ({ page }) => {
    await page.goto('/documents/library');

    // Mock the list API
    await page.route('**/api/documents/list', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [
            { filename: 'doc1.pdf', file_path: '/uploads/doc1.pdf', file_size: 1024 },
            { filename: 'doc2.txt', file_path: '/uploads/doc2.txt', file_size: 512 },
          ],
          total: 2,
        }),
      });
    });

    // Reload to trigger API call
    await page.reload();

    // Should display documents
    await expect(page.getByText('doc1.pdf')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('doc2.txt')).toBeVisible({ timeout: 5000 });
  });

  test('displays empty state when no documents', async ({ page }) => {
    await page.goto('/documents/library');

    // Mock empty list
    await page.route('**/api/documents/list', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [],
          total: 0,
        }),
      });
    });

    await page.reload();

    // Should show empty state
    await expect(page.getByText(/no documents/i)).toBeVisible({ timeout: 5000 });
  });

  test('navigates to graph view', async ({ page }) => {
    await page.goto('/documents/graph');

    // Mock the graph API
    await page.route('**/api/graph/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          nodes: [
            { id: '1', label: 'Node 1', type: 'entity' },
            { id: '2', label: 'Node 2', type: 'entity' },
          ],
          edges: [
            { source: '1', target: '2', label: 'relates to' },
          ],
        }),
      });
    });

    // Should show graph visualization
    await expect(page.locator('canvas')).toBeVisible({ timeout: 5000 });
  });

  test('handles upload errors', async ({ page }) => {
    await page.goto('/documents/upload');

    // Mock upload failure
    await page.route('**/api/documents/upload-and-process', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Upload failed',
        }),
      });
    });

    const buffer = Buffer.from('Test content');

    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test.pdf',
      mimeType: 'application/pdf',
      buffer,
    });

    // Should show error message
    await expect(page.getByText(/upload failed/i)).toBeVisible({ timeout: 5000 });
  });
});

