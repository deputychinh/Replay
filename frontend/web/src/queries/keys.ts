// Every React Query key in one place, so invalidation is never a guess.
export const keys = {
  tickets: ['tickets'] as const,
  ticketList: (params: object) => ['tickets', 'list', params] as const,
  ticket: (id: string) => ['tickets', 'one', id] as const,
  messages: (id: string) => ['tickets', 'one', id, 'messages'] as const,
  events: (id: string) => ['tickets', 'one', id, 'events'] as const,
  staff: ['staff'] as const,
  canned: ['canned-replies'] as const,
  notifications: ['notifications'] as const,
  dashboard: ['dashboard'] as const,
  slaPolicies: ['sla-policies'] as const,
  calendar: ['calendar'] as const,
  organization: ['organization'] as const,
  export: (id: string) => ['export', id] as const,
};
