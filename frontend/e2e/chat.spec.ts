import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('displays chat interface on home page', async ({ page }) => {
    // Check for main chat elements
    await expect(page.getByPlaceholderText('Type your message...')).toBeVisible();
    await expect(page.getByRole('button', { name: /send message/i })).toBeVisible();
    await expect(page.getByRole('combobox')).toBeVisible(); // Mode selector
  });

  test('sends a message and displays it in chat', async ({ page }) => {
    // Mock the API response
    await page.route('**/api/query/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'This is a test response from the assistant.',
          sources: [],
          mode: 'hybrid',
        }),
      });
    });

    const messageInput = page.getByPlaceholderText('Type your message...');
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
    await page.route('**/api/query/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'Response via Enter key',
          sources: [],
          mode: 'hybrid',
        }),
      });
    });

    const messageInput = page.getByPlaceholderText('Type your message...');

    await messageInput.fill('Test message');
    await messageInput.press('Enter');

    await expect(page.getByText('Test message')).toBeVisible();
    await expect(page.getByText('Response via Enter key')).toBeVisible();
  });

  test('adds new line with Shift+Enter', async ({ page }) => {
    const messageInput = page.getByPlaceholderText('Type your message...');

    await messageInput.fill('Line 1');
    await messageInput.press('Shift+Enter');
    await messageInput.type('Line 2');

    const value = await messageInput.inputValue();
    expect(value).toContain('\n');
  });

  test('changes query mode', async ({ page }) => {
    const modeSelector = page.getByRole('combobox');

    // Open mode selector
    await modeSelector.click();

    // Select "Local" mode
    await page.getByRole('option', { name: 'Local' }).click();

    // Verify mode is selected
    await expect(modeSelector).toContainText('Local');
  });

  test('displays conversation history', async ({ page }) => {
    await page.route('**/api/query/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'Response',
          sources: [],
          mode: 'hybrid',
        }),
      });
    });

    const messageInput = page.getByPlaceholderText('Type your message...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    // Send first message
    await messageInput.fill('First message');
    await sendButton.click();
    await expect(page.getByText('First message')).toBeVisible();

    // Send second message
    await messageInput.fill('Second message');
    await sendButton.click();
    await expect(page.getByText('Second message')).toBeVisible();

    // Both messages should be visible
    await expect(page.getByText('First message')).toBeVisible();
    await expect(page.getByText('Second message')).toBeVisible();
  });

  test('handles API errors gracefully', async ({ page }) => {
    await page.route('**/api/query/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Internal server error',
        }),
      });
    });

    const messageInput = page.getByPlaceholderText('Type your message...');
    const sendButton = page.getByRole('button', { name: /send message/i });

    await messageInput.fill('Test message');
    await sendButton.click();

    // Should show error message or toast
    await expect(page.getByText(/error/i)).toBeVisible({ timeout: 5000 });
  });

  test('disables input while loading', async ({ page }) => {
    // Delay the API response to test loading state
    await page.route('**/api/query/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 1000));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          response: 'Delayed response',
          sources: [],
          mode: 'hybrid',
        }),
      });
    });

    const messageInput = page.getByPlaceholderText('Type your message...');
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

