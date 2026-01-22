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

  test('copies user and assistant messages', async ({ page }) => {
    const sessionId = uuidv4();
    const assistantText = 'This is a copy test response from the assistant.';

    await page.addInitScript(() => {
      // Capture clipboard writes in a test-friendly way.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__copiedText = null;

      const clipboard = {
        writeText: async (text: string) => {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (window as any).__copiedText = text;
        },
      };

      Object.defineProperty(navigator, 'clipboard', {
        value: clipboard,
        configurable: true,
      });
    });

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

    await messageInput.fill('Hello, assistant!');
    await sendButton.click();

    await expect(page.getByText('Hello, assistant!')).toBeVisible();
    await expect(page.getByText(assistantText)).toBeVisible();

    const assistantCopyButton = page.getByRole('button', { name: 'Copy assistant message' });
    await expect(assistantCopyButton).toBeVisible();

    await assistantCopyButton.click();
    await expect.poll(() => page.evaluate(() => (window as never as { __copiedText: string | null }).__copiedText))
      .toBe(assistantText);

    // Wait for copy toast to disappear so it doesn't block hover events.
    await expect(page.locator('section[aria-label^="Notifications"] li[data-sonner-toast]')).toHaveCount(0);

    await page.getByText('Hello, assistant!').hover();
    const userCopyButton = page.getByRole('button', { name: 'Copy user message' });
    await expect(userCopyButton).toBeVisible();

    await userCopyButton.click();
    await expect.poll(() => page.evaluate(() => (window as never as { __copiedText: string | null }).__copiedText))
      .toBe('Hello, assistant!');
  });

  test('retries assistant message and keeps variants history', async ({ page }) => {
    const sessionId = uuidv4();
    const assistantText1 = 'First assistant response';
    const assistantText2 = 'Second assistant response (retry)';
    let assistantMessageId: string | null = null;
    let lastRequestId: string | null = null;

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

    // Mock streaming turn API (SSE) - first assistant response
    await page.route(`**/api/chat/sessions/${sessionId}/turn:stream`, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      lastRequestId = body.request_id;
      assistantMessageId = uuidv4();

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText1 })}`,
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
                id: assistantMessageId,
                session_id: sessionId,
                role: 'assistant',
                content: assistantText1,
                created_at: new Date().toISOString(),
                metadata: { request_id: body.request_id },
              },
              error: null,
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    // Mock retry streaming endpoint (SSE) - updates assistant message in-place with variants
    await page.route(`**/api/chat/sessions/${sessionId}/messages/*/retry:stream`, async (route) => {
      if (!assistantMessageId) throw new Error('assistantMessageId not set');
      const createdAt = new Date().toISOString();

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText2 })}`,
          '',
          `data: ${JSON.stringify({
            type: 'final',
            message: {
              id: assistantMessageId,
              session_id: sessionId,
              role: 'assistant',
              content: assistantText2,
              created_at: createdAt,
              metadata: {
                request_id: lastRequestId,
                variants: [assistantText1, assistantText2],
                variant_index: 1,
              },
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    await messageInput.fill('Retry me');
    await sendButton.click();

    await expect(page.getByText(assistantText1)).toBeVisible();

    const retryButton = page.getByRole('button', { name: 'Retry assistant message' });
    await expect(retryButton).toBeVisible();
    await retryButton.click();

    await expect(page.getByText(assistantText2)).toBeVisible();
    await expect(page.getByText('2/2')).toBeVisible();

    const prevVersion = page.getByRole('button', { name: 'Previous assistant version' });
    await prevVersion.click();
    await expect(page.getByText(assistantText1)).toBeVisible();
    await expect(page.getByText('1/2')).toBeVisible();

    const nextVersion = page.getByRole('button', { name: 'Next assistant version' });
    await nextVersion.click();
    await expect(page.getByText(assistantText2)).toBeVisible();
  });

  test('edits latest user message and regenerates assistant response', async ({ page }) => {
    const sessionId = uuidv4();
    const assistantText1 = 'Original assistant response';
    const assistantText2 = 'Assistant response after edit';
    let userMessageId: string | null = null;
    let assistantMessageId: string | null = null;
    let lastRequestId: string | null = null;

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

    // Mock streaming turn API (SSE) - first assistant response
    await page.route(`**/api/chat/sessions/${sessionId}/turn:stream`, async (route) => {
      const body = JSON.parse(route.request().postData() || '{}');
      lastRequestId = body.request_id;
      userMessageId = uuidv4();
      assistantMessageId = uuidv4();

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText1 })}`,
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
                metadata: { mode: 'hybrid', request_id: body.request_id },
              },
              assistant_message: {
                id: assistantMessageId,
                session_id: sessionId,
                role: 'assistant',
                content: assistantText1,
                created_at: new Date().toISOString(),
                metadata: { request_id: body.request_id },
              },
              error: null,
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    // Mock PATCH update user message endpoint
    await page.route(new RegExp(`/api/chat/sessions/${sessionId}/messages/[^/]+$`), async (route) => {
      if (route.request().method() !== 'PATCH') {
        await route.continue();
        return;
      }

      const body = JSON.parse(route.request().postData() || '{}');
      const messageId = route.request().url().split('/').pop() || uuidv4();
      const createdAt = new Date().toISOString();

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: messageId,
          session_id: sessionId,
          role: 'user',
          content: body.content,
          created_at: createdAt,
          metadata: { mode: 'hybrid', request_id: lastRequestId },
        }),
      });
    });

    // Mock retry streaming endpoint (SSE) - regenerate assistant based on edited prompt
    await page.route(`**/api/chat/sessions/${sessionId}/messages/*/retry:stream`, async (route) => {
      if (!assistantMessageId) throw new Error('assistantMessageId not set');
      const createdAt = new Date().toISOString();

      await route.fulfill({
        status: 200,
        contentType: 'text/event-stream',
        body: [
          `data: ${JSON.stringify({ type: 'delta', delta: assistantText2 })}`,
          '',
          `data: ${JSON.stringify({
            type: 'final',
            message: {
              id: assistantMessageId,
              session_id: sessionId,
              role: 'assistant',
              content: assistantText2,
              created_at: createdAt,
              metadata: {
                request_id: lastRequestId,
                variants: [assistantText1, assistantText2],
                variant_index: 1,
              },
            },
          })}`,
          '',
        ].join('\n\n'),
      });
    });

    await page.goto(`/chat/${sessionId}`);

    const messageInput = page.getByPlaceholder('Ask anything...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    await messageInput.fill('Edit me');
    await sendButton.click();

    await expect(page.getByText('Edit me')).toBeVisible();
    await expect(page.getByText(assistantText1)).toBeVisible();

    // Hover to reveal edit button
    await page.getByText('Edit me').hover();
    const editButton = page.getByRole('button', { name: 'Edit user message' });
    await expect(editButton).toBeVisible();
    await editButton.click();

    const textarea = page.getByPlaceholder('Edit your message...');
    await expect(textarea).toBeVisible();
    await textarea.fill('Edit me (updated)');

    const saveButton = page.getByRole('button', { name: /save & regenerate/i });
    await saveButton.click();

    await expect(page.getByText('Edit me (updated)')).toBeVisible();
    await expect(page.getByText(assistantText2)).toBeVisible();
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
