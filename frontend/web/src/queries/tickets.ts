import { api, unwrap, type Schemas, type TicketSort, type TicketView } from '@relay/api-client';
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { keys } from './keys';

export type Ticket = Schemas['TicketOut'];
export type TicketDetail = Schemas['TicketDetail'];
export type Message = Schemas['MessageOut'];

export interface TicketFilters {
  view?: TicketView;
  status?: Schemas['TicketStatus'];
  priority?: Schemas['TicketPriority'];
  q?: string;
  sort?: TicketSort;
}

const PAGE = 40;

export function useTickets(filters: TicketFilters) {
  return useInfiniteQuery({
    queryKey: keys.ticketList(filters),
    initialPageParam: null as string | null,
    queryFn: async ({ pageParam }) =>
      unwrap(await api.GET('/api/v1/tickets', { params: { query: { ...filters, limit: PAGE, cursor: pageParam ?? undefined } } })),
    getNextPageParam: (last) => last.next_cursor,
  });
}

export function useTicket(id: string | undefined) {
  return useQuery({
    queryKey: keys.ticket(id ?? ''),
    enabled: Boolean(id),
    queryFn: async () => unwrap(await api.GET('/api/v1/tickets/{ticket_id}', { params: { path: { ticket_id: id! } } })),
  });
}

export function useMessages(id: string | undefined) {
  return useQuery({
    queryKey: keys.messages(id ?? ''),
    enabled: Boolean(id),
    queryFn: async () => unwrap(await api.GET('/api/v1/tickets/{ticket_id}/messages', { params: { path: { ticket_id: id! } } })),
  });
}

export function useEvents(id: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: keys.events(id ?? ''),
    enabled: Boolean(id) && enabled,
    queryFn: async () => unwrap(await api.GET('/api/v1/tickets/{ticket_id}/events', { params: { path: { ticket_id: id! } } })),
  });
}

export function useUpdateTicket(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas['TicketUpdate']) =>
      unwrap(await api.PATCH('/api/v1/tickets/{ticket_id}', { params: { path: { ticket_id: id } }, body })),
    onSuccess: (ticket) => {
      client.setQueryData(keys.ticket(id), ticket);
      void client.invalidateQueries({ queryKey: keys.tickets });
    },
  });
}

export function useBulkUpdate() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas['BulkUpdate']) => unwrap(await api.POST('/api/v1/tickets/bulk', { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.tickets }),
  });
}

export function useSendMessage(id: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas['MessageCreate']) =>
      unwrap(await api.POST('/api/v1/tickets/{ticket_id}/messages', { params: { path: { ticket_id: id } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.ticket(id) }),
  });
}

export function useCreateTicket() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas['TicketCreate']) => unwrap(await api.POST('/api/v1/tickets', { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.tickets }),
  });
}
