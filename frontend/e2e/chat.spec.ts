import { test, expect, Page, type Route } from '@playwright/test';
import { v4 as uuidv4 } from 'uuid';

/**
 * Helper to set up common API mocks for chat tests.
 * Mocks sessions list, health, ready, and config endpoints.
 */
async function setupCommonMocks(page: Page, sessions: Array<{ id: string; title: string }> = []) {
  // Mock sessions list
  const sessionsHandler = async (route: Route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          sessions: sessions.map((s) => ({
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
}

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await setupCommonMocks(page);
  });

  test('shows empty state on /chat', async ({ page }) => {
    await page.goto('/chat');

    await expect(page.getByText('Welcome to Arona Chat')).toHaveCount(0);
    await expect(page.getByPlaceholder('Ask anything...')).toBeVisible();
    await expect(page.locator('aside').getByRole('button', { name: /new chat/i })).toHaveCount(0);
  });

  test('creates new session only after first send', async ({ page }) => {
    // Mock session detail for any newly-created session ID
    await page.route(/\/api\/chat\/sessions\/[^/]+$/, async (route) => {
      const sessionId = route.request().url().split('/').pop() || uuidv4();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'New Chat',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    // Mock messages list (empty initially)
    await page.route(/\/api\/chat\/sessions\/[^/]+\/messages.*/, async (route) => {
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

    // Mock streaming turn API (SSE) for any session
    await page.route(/\/api\/chat\/sessions\/[^/]+\/turn:stream$/, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      const sessionId = route.request().url().split('/').slice(-2)[0] || uuidv4();
      const assistantText = 'Hello! This is a test response.';

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText })}`,
          '',
          `data: ${JSON.stringify({
            type: 'final',
            response: {
              turn_id: body.request_id,
              status: 'completed',
              user_message: {
                id: uuidv4(),
                session_id: sessionId,
                role: 'user',
                content: body.query,
                created_at: new Date().toISOString(),
                metadata: { mode: 'hybrid' },
              },
              assistant_message: {
                id: uuidv4(),
                session_id: sessionId,
                role: 'assistant',
                content: assistantText,
                created_at: new Date().toISOString(),
                metadata: {},
              },
              error: null,
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    await page.goto('/chat');

    const messageInput = page.getByPlaceholder('Ask anything...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    await messageInput.fill('Hello from draft');
    await sendButton.click();

    // Should navigate to new session URL
    await expect(page).toHaveURL(/\/chat\/[a-f0-9-]+/);
    await expect(page.getByText('Hello from draft')).toBeVisible();
  });

  test('sends message via new turn API and displays response', async ({ page }) => {
    const sessionId = uuidv4();

    // Mock session detail
    await page.route(`**/api/chat/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    // Mock messages list (empty initially)
    await page.route(`**/api/chat/sessions/${sessionId}/messages*`, async (route) => {
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

    // Mock streaming turn API (SSE)
    await page.route(`**/api/chat/sessions/${sessionId}/turn:stream`, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      const userMessageId = uuidv4();
      const assistantMessageId = uuidv4();
      const assistantText = 'This is a test response from the assistant.';

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: 'This is a test ' })}`,
          '',
          `data: ${JSON.stringify({ type: 'delta', delta: 'response from the assistant.' })}`,
          '',
          `data: ${JSON.stringify({
            type: 'final',
            response: {
              turn_id: body.request_id,
              status: 'completed',
              user_message: {
                id: userMessageId,
                session_id: sessionId,
                role: 'user',
                content: body.query,
                created_at: new Date().toISOString(),
                metadata: { mode: 'hybrid' },
              },
              assistant_message: {
                id: assistantMessageId,
                session_id: sessionId,
                role: 'assistant',
                content: assistantText,
                created_at: new Date().toISOString(),
                metadata: {},
              },
              error: null,
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    // Type and send a message
    await messageInput.fill('Hello, assistant!');
    await sendButton.click();

    // Check that user message appears
    await expect(page.getByText('Hello, assistant!')).toBeVisible();

    // Check that assistant response appears
    await expect(page.getByText('This is a test response from the assistant.')).toBeVisible();

    // Check that input is cleared
    await expect(messageInput).toHaveValue('');
  });

  test('sends message using Enter key', async ({ page }) => {
    const sessionId = uuidv4();

    // Setup session mocks
    await page.route(`**/api/chat/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionId}/messages*`, async (route) => {
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

    await page.route(`**/api/chat/sessions/${sessionId}/turn:stream`, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      const assistantText = 'Response via Enter key';

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText })}`,
          '',
          `data: ${JSON.stringify({
            type: 'final',
            response: {
              turn_id: body.request_id,
              status: 'completed',
              user_message: {
                id: uuidv4(),
                session_id: sessionId,
                role: 'user',
                content: body.query,
                created_at: new Date().toISOString(),
                metadata: { mode: 'hybrid' },
              },
              assistant_message: {
                id: uuidv4(),
                session_id: sessionId,
                role: 'assistant',
                content: assistantText,
                created_at: new Date().toISOString(),
                metadata: {},
              },
              error: null,
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');
    await messageInput.fill('Test message');
    await messageInput.press('Enter');

    await expect(page.getByText('Test message')).toBeVisible();
    await expect(page.getByText('Response via Enter key')).toBeVisible();
  });

  test('adds new line with Shift+Enter', async ({ page }) => {
    const sessionId = uuidv4();

    // Setup session mocks
    await page.route(`**/api/chat/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionId}/messages*`, async (route) => {
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

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');

    await messageInput.fill('Line 1');
    await messageInput.press('Shift+Enter');
    await messageInput.type('Line 2');

    const value = await messageInput.inputValue();
    expect(value).toContain('\n');
  });

  test('does not show query mode selector', async ({ page }) => {
    const sessionId = uuidv4();

    // Setup session mocks
    await page.route(`**/api/chat/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionId}/messages*`, async (route) => {
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

    await page.goto(`/chat/${sessionId}`);
    await expect(page.getByRole('combobox')).toHaveCount(0);
  });

  test('handles API errors gracefully', async ({ page }) => {
    const sessionId = uuidv4();

    await page.route(`**/api/chat/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionId}/messages*`, async (route) => {
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

    await page.route(`**/api/chat/sessions/${sessionId}/turn:stream`, async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: { code: 'INTERNAL_ERROR', message: 'Internal server error' },
        }),
      });
    });

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    await messageInput.fill('Test message');
    await sendButton.click();

    // Should show error message or toast
    await expect(page.getByText(/failed to send message/i)).toBeVisible({ timeout: 5000 });
  });

  test('disables input while loading', async ({ page }) => {
    const sessionId = uuidv4();

    await page.route(`**/api/chat/sessions/${sessionId}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: sessionId,
          title: 'Test Session',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          deleted_at: null,
          metadata: {},
        }),
      });
    });

    await page.route(`**/api/chat/sessions/${sessionId}/messages*`, async (route) => {
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

    // Delay the API response to test loading state
    await page.route(`**/api/chat/sessions/${sessionId}/turn:stream`, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      await new Promise((resolve) => setTimeout(resolve, 1000));
      const assistantText = 'Delayed response';
      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText })}`,
          '',
          `data: ${JSON.stringify({
            type: 'final',
            response: {
              turn_id: body.request_id,
              status: 'completed',
              user_message: {
                id: uuidv4(),
                session_id: sessionId,
                role: 'user',
                content: body.query,
                created_at: new Date().toISOString(),
                metadata: { mode: 'hybrid' },
              },
              assistant_message: {
                id: uuidv4(),
                session_id: sessionId,
                role: 'assistant',
                content: assistantText,
                created_at: new Date().toISOString(),
                metadata: {},
              },
              error: null,
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    await messageInput.fill('Test');
    await sendButton.click();

    // Input should be disabled during loading
    await expect(messageInput).toBeDisabled();

    // Wait for response
    await expect(page.getByText('Delayed response')).toBeVisible({ timeout: 3000 });

    // Input should be enabled again
    await expect(messageInput).toBeEnabled();
  });
});
