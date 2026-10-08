// Live updates for the console: one WebSocket per tab, refreshed caches on every event.
import { EventName } from '@relay/api-client';
import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { keys } from '../queries/keys';

const RECONNECT_MS = 3000;
const TYPING_EVENT = 'relay:typing';
const LIVE_EVENT = 'relay:live';

export interface LiveEvent {
  event: string;
  data: Record<string, unknown>;
}

export function useRealtime(token: string | null, onEvent?: (event: LiveEvent) => void): boolean {
  const queryClient = useQueryClient();
  const [connected, setConnected] = useState(false);
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    if (!token) return;
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    const connect = () => {
      const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
      socket = new WebSocket(`${scheme}://${window.location.host}/api/v1/ws`);
      socket.onopen = () => socket?.send(JSON.stringify({ token }));
      socket.onmessage = (message) => {
        const live = JSON.parse(message.data as string) as LiveEvent;
        if (live.event === 'ready') return setConnected(true);
        if (live.event === 'ping') return;
        const ticketId = (live.data.id ?? live.data.ticket_id) as string | undefined;
        if (live.event === EventName.NOTIFICATION_CREATED) {
          void queryClient.invalidateQueries({ queryKey: keys.notifications });
        } else if (live.event !== EventName.AGENT_TYPING) {
          void queryClient.invalidateQueries({ queryKey: keys.tickets });
          if (ticketId) void queryClient.invalidateQueries({ queryKey: keys.ticket(ticketId) });
        }
        handler.current?.(live);
        window.dispatchEvent(new CustomEvent(LIVE_EVENT, { detail: live }));
      };
      socket.onclose = () => {
        setConnected(false);
        if (!stopped) retry = setTimeout(connect, RECONNECT_MS);
      };
    };

    const typing = (event: Event) => {
      const ticketId = (event as CustomEvent<string>).detail;
      if (socket?.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ event: EventName.AGENT_TYPING, ticket_id: ticketId }));
      }
    };

    connect();
    window.addEventListener(TYPING_EVENT, typing);
    return () => {
      stopped = true;
      clearTimeout(retry);
      window.removeEventListener(TYPING_EVENT, typing);
      socket?.close();
    };
  }, [token, queryClient]);

  return connected;
}

/** Tell other agents "I am typing on this ticket" through the open socket (best effort). */
export function sendTyping(ticketId: string): void {
  window.dispatchEvent(new CustomEvent(TYPING_EVENT, { detail: ticketId }));
}

/** Subscribe a page to the live events received by the console shell's socket. */
export function useLiveEvent(listener: (event: LiveEvent) => void): void {
  const current = useRef(listener);
  current.current = listener;
  useEffect(() => {
    const handle = (event: Event) => current.current((event as CustomEvent<LiveEvent>).detail);
    window.addEventListener(LIVE_EVENT, handle);
    return () => window.removeEventListener(LIVE_EVENT, handle);
  }, []);
}
