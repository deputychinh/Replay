import { api, unwrap, type Schemas, type TicketPriority } from '@relay/api-client';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { keys } from './keys';

export function useStaff() {
  return useQuery({ queryKey: keys.staff, queryFn: async () => unwrap(await api.GET('/api/v1/users/staff')) });
}

export function useCannedReplies() {
  return useQuery({ queryKey: keys.canned, queryFn: async () => unwrap(await api.GET('/api/v1/canned-replies')) });
}

export function useNotifications() {
  return useQuery({ queryKey: keys.notifications, queryFn: async () => unwrap(await api.GET('/api/v1/notifications')) });
}

export function useMarkNotificationsRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () => unwrap(await api.POST('/api/v1/notifications/read')),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.notifications }),
  });
}

export function useDashboard() {
  return useQuery({ queryKey: keys.dashboard, queryFn: async () => unwrap(await api.GET('/api/v1/reports/dashboard')) });
}

export function useSlaPolicies() {
  return useQuery({ queryKey: keys.slaPolicies, queryFn: async () => unwrap(await api.GET('/api/v1/sla-policies')) });
}

export function useSetSlaPolicy() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ priority, body }: { priority: TicketPriority; body: Schemas['SlaPolicyIn'] }) =>
      unwrap(await api.PUT('/api/v1/sla-policies/{priority}', { params: { path: { priority } }, body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.slaPolicies }),
  });
}

export function useCalendar() {
  return useQuery({ queryKey: keys.calendar, queryFn: async () => unwrap(await api.GET('/api/v1/organization/calendar')) });
}

export function useSaveCalendar() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas['CalendarIn']) => unwrap(await api.PUT('/api/v1/organization/calendar', { body })),
    onSuccess: (data) => client.setQueryData(keys.calendar, data),
  });
}

export function useCreateCannedReply() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: Schemas['CannedReplyIn']) => unwrap(await api.POST('/api/v1/canned-replies', { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.canned }),
  });
}

export function useStartExport() {
  return useMutation({
    mutationFn: async (body: Schemas['ExportIn']) => unwrap(await api.POST('/api/v1/reports/exports', { body })),
  });
}

export function useExport(id: string | null) {
  return useQuery({
    queryKey: keys.export(id ?? ''),
    enabled: Boolean(id),
    refetchInterval: (query) => (query.state.data?.status === 'ready' || query.state.data?.status === 'failed' ? false : 2000),
    queryFn: async () => unwrap(await api.GET('/api/v1/reports/exports/{export_id}', { params: { path: { export_id: id! } } })),
  });
}

/** Ask the API for a presigned URL, then send the file straight to S3. Returns the attachment id. */
export async function uploadFile(file: File): Promise<string> {
  const upload = unwrap(
    await api.POST('/api/v1/attachments', { body: { filename: file.name, content_type: file.type, size_bytes: file.size } }),
  );
  const response = await fetch(upload.upload_url, { method: 'PUT', body: file, headers: upload.headers });
  if (!response.ok) throw new Error('Upload failed');
  return upload.id;
}

export async function downloadUrl(attachmentId: string): Promise<string> {
  return unwrap(await api.GET('/api/v1/attachments/{attachment_id}', { params: { path: { attachment_id: attachmentId } } })).url;
}
