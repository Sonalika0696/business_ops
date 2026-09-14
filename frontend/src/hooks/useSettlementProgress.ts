import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { API_BASE_URL } from "@/api/client";
import { authStorage } from "@/lib/authStorage";
import { queryKeys } from "@/api/queryClient";
import { isTerminalStatus } from "@/api/settlements";
import type { ProgressFrame, SettlementReportRead } from "@/api/types";

/**
 * `WS /ws/settlements/{id}?token=<jwt>` — the one WS route in the system
 * (DESIGN.md §4), token as a query param because browsers can't set WS
 * headers. Pushes a frame on every status transition; on disconnect this
 * reconnects with backoff rather than falling back to a second transport
 * (ARCHITECTURE.md §3) — `useSettlement`'s `livePoll` option is the
 * independent safety net for when Redis (the pub/sub broker) isn't running.
 */
export function useSettlementProgress(reportId: string | undefined, enabled: boolean) {
  const queryClient = useQueryClient();
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!reportId || !enabled) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;

    const connect = () => {
      const token = authStorage.get();
      if (!token || cancelled) return;

      const wsBase = API_BASE_URL.replace(/^http/, "ws");
      socket = new WebSocket(`${wsBase}/ws/settlements/${reportId}?token=${encodeURIComponent(token)}`);

      socket.onmessage = (event) => {
        attemptRef.current = 0;
        try {
          const frame = JSON.parse(event.data) as ProgressFrame;
          queryClient.setQueryData<SettlementReportRead>(queryKeys.settlement(reportId), (prev) =>
            prev ? { ...prev, ...frame } : prev,
          );
          if (isTerminalStatus(frame.status)) {
            queryClient.invalidateQueries({ queryKey: queryKeys.settlement(reportId) });
          }
        } catch {
          // Malformed frame — ignore, the poll fallback still converges.
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        const current = queryClient.getQueryData<SettlementReportRead>(queryKeys.settlement(reportId));
        if (current && isTerminalStatus(current.status)) return;
        attemptRef.current += 1;
        const delay = Math.min(1000 * 2 ** attemptRef.current, 15000);
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      cancelled = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [reportId, enabled, queryClient]);
}
