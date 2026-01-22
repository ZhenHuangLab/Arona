import { fireEvent, render, screen } from '@testing-library/react';
import { Message } from './Message';
import type { ChatMessage } from '@/types/chat';

function buildUserMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    id: 'm1',
    role: 'user',
    content: 'hi',
    timestamp: new Date('2026-01-22T01:50:00.000Z').toISOString(),
    ...overrides,
  };
}

describe('Message (user bubble sizing)', () => {
  it('does not apply w-full in view mode (prevents short bubbles from stretching)', () => {
    render(
      <Message
        message={buildUserMessage({ content: 'hi' })}
        canEdit
        onEdit={async () => {}}
      />
    );

    const text = screen.getByText('hi');
    const bubble = text.closest('div.rounded-2xl');
    expect(bubble).not.toBeNull();
    expect(bubble).not.toHaveClass('w-full');
  });

  it('applies w-full only in edit mode (textarea can use full width)', () => {
    render(
      <Message
        message={buildUserMessage({ content: 'hi' })}
        canEdit
        onEdit={async () => {}}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Edit user message' }));
    expect(screen.getByPlaceholderText('Edit your message...')).toBeInTheDocument();

    const textarea = screen.getByPlaceholderText('Edit your message...');
    const bubble = textarea.closest('div.rounded-2xl');
    expect(bubble).not.toBeNull();
    expect(bubble).toHaveClass('w-full');
  });
});

