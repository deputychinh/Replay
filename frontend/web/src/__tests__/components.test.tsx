import { MessageKind, TicketPriority, TicketStatus } from '@relay/api-client';
import { render, screen } from '@testing-library/react';
import { PriorityBadge, StatusBadge } from '../components/badge/Badge';
import { Thread } from '../features/ticket/Thread';
import type { Message } from '../queries/tickets';

const message = (overrides: Partial<Message>): Message => ({
  id: crypto.randomUUID(),
  kind: MessageKind.PUBLIC_REPLY,
  body: 'Hello',
  author: { id: 'a', full_name: 'Dana Whitfield', company: 'Globex' },
  author_is_staff: false,
  attachments: [],
  created_at: '2026-10-08T12:00:00Z',
  ...overrides,
});

describe('badges', () => {
  it('shows readable labels with a colour modifier per status family', () => {
    render(<><StatusBadge status={TicketStatus.PENDING_CUSTOMER} /><PriorityBadge priority={TicketPriority.URGENT} /></>);
    expect(screen.getByText('Waiting on customer')).toHaveClass('badge', 'badge--waiting');
    expect(screen.getByText('Urgent')).toHaveClass('badge--urgent');
  });
});

describe('Thread', () => {
  it('marks internal notes and puts our side on the right', () => {
    render(
      <Thread
        perspective="staff"
        messages={[
          message({ body: 'Customer question' }),
          message({ body: 'Team only', kind: MessageKind.INTERNAL_NOTE, author_is_staff: true, author: { id: 'b', full_name: 'Priya Natarajan' } }),
        ]}
      />,
    );
    const note = screen.getByText('Team only').closest('li');
    expect(note).toHaveClass('thread__message--note', 'thread__message--ours');
    expect(screen.getByText('Internal')).toBeInTheDocument();
    expect(screen.getByText('Customer question').closest('li')).not.toHaveClass('thread__message--ours');
  });

  it('renders message text as text, never as HTML', () => {
    render(<Thread perspective="customer" messages={[message({ body: '<img src=x onerror=alert(1)>' })]} />);
    expect(document.querySelector('img')).toBeNull();
    expect(screen.getByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
  });
});
