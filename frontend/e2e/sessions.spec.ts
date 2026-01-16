import { test, expect, Page, type Route } from '@playwright/test';
import { v4 as uuidv4 } from 'uuid';

/**
 * Helper to set up common API mocks for session tests.
 */
async function setupCommonMocks(
  page: Page,
  sessions: Array<{ id: string; title: string }> = []
) {
  // Track sessions for dynamic updates
  const sessionStore = new Map(sessions.map((s) => [s.id, s]));

  // Mock sessions list
  const sessionsHandler = async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sessions: Array.from(sessionStore.values()).map((s) => ({
            id: s.id,
            title: s.title,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            deleted_at: null,
            message_count: 0,
            last_message_preview: null,
          })),
          has_more: false,
          next_cursor: null,
        }),
      });
    } else if (route.request().method() === 'POST') {
      // Create session
      const newId = uuidv4();
      const newSession = { id: newId, title: 'New Chat' };
      sessionStore.set(newId, newSession);
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: newId,
          title: 'New Chat',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    } else {
      await route.continue();
    }
  };

  await page.route(/\/api\/chat\/sessions(?:\?.*)?$/, sessionsHandler);

  // Mock health endpoint
  await page.route('**/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'healthy',
        version: '1.0.0',
        rag_initialized: true,
        models: {},
      }),
    });
  });

  // Mock ready endpoint
  await page.route('**/ready', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ready: true,
        status: 'ready',
      }),
    });
  });

  // Mock config endpoint
  await page.route(/\/api\/config\/.*$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        backend: { host: 'localhost', port: 8000, cors_origins: ['*'] },
        models: {
          llm: { provider: 'openai', model_name: 'gpt-4' },
          embedding: { provider: 'openai', model_name: 'text-embedding-3-small' },
        },
        storage: { working_dir: './data', upload_dir: './uploads' },
        processing: {
          parser: 'default',
          enable_image_processing: true,
          enable_table_processing: true,
          enable_equation_processing: true,
        },
      }),
    });
  });

  return { sessionStore };
}

test.describe('Session Management', () => {
  test('displays session list in sidebar', async ({ page }) => {
    const sessionA = { id: uuidv4(), title: 'Session A' };
    const sessionB = { id: uuidv4(), title: 'Session B' };

    await setupCommonMocks(page, [sessionA, sessionB]);
    await page.goto('/chat');

    // Both sessions should be visible in sidebar
    await expect(page.getByText('Session A')).toBeVisible();
    await expect(page.getByText('Session B')).toBeVisible();
  });

  test('renames session via sidebar menu', async ({ page }) => {
    const session = { id: uuidv4(), title: 'Original Title' };
    await setupCommonMocks(page, [session]);

    // Mock session detail
    await page.route(new RegExp(`/api/chat/sessions/${session.id}(?:\\?.*)?$`), async (route) => {
      if (route.request().method() === 'PATCH') {
        const body = JSON.parse(route.request().postData() || '{}');
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: session.id,
            title: body.title || session.title,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            deleted_at: null,
            metadata: {},
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: session.id,
            title: session.title,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            deleted_at: null,
            metadata: {},
          }),
        });
      }
    });

    await page.route(`**/api/chat/sessions/${session.id}/messages*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: [],
          has_more: false,
          next_cursor: null,
        }),
      });
    });

    await page.goto(`/chat/${session.id}`);

    const sidebar = page.locator('aside');
    const sessionLink = sidebar.getByRole('link', { name: 'Original Title' });

    // Wait for the session to be visible in sidebar
    await expect(sessionLink).toBeVisible();

    // Hover over the session to reveal the options button
    const sessionItem = sessionLink.locator('..');
    await sessionItem.hover();

    // Click the session options button
    await sessionItem.getByRole('button', { name: 'Session options' }).click();

    // Click rename
    await page.getByRole('menuitem', { name: 'Rename' }).click();

    // Type new name and save
    const renameInput = sidebar.getByRole('textbox');
    await renameInput.fill('Renamed Session');
    await renameInput.press('Enter');

    // Should show renamed title (optimistic update)
    await expect(sidebar.getByRole('link', { name: 'Renamed Session' })).toBeVisible({
      timeout: 3000,
    });
  });

  test('deletes session via sidebar menu', async ({ page }) => {
    const session = { id: uuidv4(), title: 'To Delete' };
    await setupCommonMocks(page, [session]);

    // Mock delete endpoint
    await page.route(new RegExp(`/api/chat/sessions/${session.id}(?:\\?.*)?$`), async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: session.id,
            deleted: true,
            hard: false,
            deleted_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: session.id,
            title: session.title,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
            deleted_at: null,
            metadata: {},
          }),
        });
      }
    });

    await page.route(`**/api/chat/sessions/${session.id}/messages*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: [],
          has_more: false,
          next_cursor: null,
        }),
      });
    });

    await page.goto(`/chat/${session.id}`);

    const sidebar = page.locator('aside');
    const sessionLink = sidebar.getByRole('link', { name: 'To Delete' });

    // Wait for session to be visible in sidebar
    await expect(sessionLink).toBeVisible();

    // Hover over the session
    const sessionItem = sessionLink.locator('..');
    await sessionItem.hover();

    // Click the session options button
    await sessionItem.getByRole('button', { name: 'Session options' }).click();

    // Click delete
    await page.getByRole('menuitem', { name: 'Delete' }).click();

    // Session should be removed (optimistic update)
    await expect(sidebar.getByRole('link', { name: 'To Delete' })).not.toBeVisible({ timeout: 3000 });

    // Should navigate to /chat
    await expect(page).toHaveURL(/\/chat$/);
  });

  test('navigates to Documents library from sidebar', async ({ page }) => {
    await setupCommonMocks(page);

    // Mock documents details (LibraryView uses /details)
    await page.route('**/api/documents/details', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          documents: [],
          total: 0,
        }),
      });
    });

    await page.goto('/chat');

    // Click on Documents link in sidebar
    await page.locator('aside').getByRole('link', { name: 'Documents' }).click();

    // Should navigate to documents library
    await expect(page).toHaveURL(/\/documents\/library/);

    // Should show Document Library content
    await expect(page.getByText(/document library/i)).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Multi-Session Isolation', () => {
  test('messages are isolated between sessions', async ({ page }) => {
    const sessionA = { id: uuidv4(), title: 'Session A' };
    const sessionB = { id: uuidv4(), title: 'Session B' };

    await setupCommonMocks(page, [sessionA, sessionB]);

    // Store messages per session
    const messagesA = [
      {
        id: uuidv4(),
        session_id: sessionA.id,
        role: 'user',
        content: 'Message in Session A',
        created_at: new Date().toISOString(),
        metadata: {},
      },
      {
        id: uuidv4(),
        session_id: sessionA.id,
        role: 'assistant',
        content: 'Response in Session A',
        created_at: new Date().toISOString(),
        metadata: {},
      },
    ];

    const messagesB = [
      {
        id: uuidv4(),
        session_id: sessionB.id,
        role: 'user',
        content: 'Message in Session B',
        created_at: new Date().toISOString(),
        metadata: {},
      },
      {
        id: uuidv4(),
        session_id: sessionB.id,
        role: 'assistant',
        content: 'Response in Session B',
        created_at: new Date().toISOString(),
        metadata: {},
      },
    ];

    // Mock session A
    await page.route(`**/api/chat/sessions/${sessionA.id}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionA.id,
          title: sessionA.title,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionA.id}/messages*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: messagesA,
          has_more: false,
          next_cursor: null,
        }),
      });
    });

    // Mock session B
    await page.route(`**/api/chat/sessions/${sessionB.id}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionB.id,
          title: sessionB.title,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionB.id}/messages*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages: messagesB,
          has_more: false,
          next_cursor: null,
        }),
      });
    });

    // Go to Session A
    await page.goto(`/chat/${sessionA.id}`);

    // Should see Session A messages
    await expect(page.getByText('Message in Session A')).toBeVisible();
    await expect(page.getByText('Response in Session A')).toBeVisible();

    // Should NOT see Session B messages
    await expect(page.getByText('Message in Session B')).not.toBeVisible();

    // Click on Session B in sidebar
    await page.getByText('Session B').click();

    // Should see Session B messages
    await expect(page.getByText('Message in Session B')).toBeVisible();
    await expect(page.getByText('Response in Session B')).toBeVisible();

    // Should NOT see Session A messages
    await expect(page.getByText('Message in Session A')).not.toBeVisible();
  });
});

test.describe('Session Persistence', () => {
  test('session persists after page refresh', async ({ page }) => {
    const session = { id: uuidv4(), title: 'Persistent Session' };
    const messages = [
      {
        id: uuidv4(),
        session_id: session.id,
        role: 'user',
        content: 'Hello before refresh',
        created_at: new Date().toISOString(),
        metadata: {},
      },
      {
        id: uuidv4(),
        session_id: session.id,
        role: 'assistant',
        content: 'Response before refresh',
        created_at: new Date().toISOString(),
        metadata: {},
      },
    ];

    await setupCommonMocks(page, [session]);

    await page.route(`**/api/chat/sessions/${session.id}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: session.id,
          title: session.title,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${session.id}/messages*`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          messages,
          has_more: false,
          next_cursor: null,
        }),
      });
    });

    // Go to session
    await page.goto(`/chat/${session.id}`);

    // Verify messages are visible
    await expect(page.getByText('Hello before refresh')).toBeVisible();
    await expect(page.getByText('Response before refresh')).toBeVisible();

    // Refresh the page
    await page.reload();

    // Session should still be in sidebar
    await expect(page.locator('aside').getByRole('link', { name: 'Persistent Session' })).toBeVisible();

    // Messages should still be visible (re-fetched from backend)
    await expect(page.getByText('Hello before refresh')).toBeVisible();
    await expect(page.getByText('Response before refresh')).toBeVisible();
  });
});
