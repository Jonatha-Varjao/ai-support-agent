import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { STALE_10S } from "../lib/constants";
import {
  listKB,
  createKB,
  updateKB,
  deleteKB,
  listUnanswered,
  updateUnanswered,
  listHandoffs,
  updateHandoff,
  listAllThreads,
  getAdminMessages,
  type KBCreateRequest,
  type KBUpdateRequest,
  type HandoffUpdateRequest,
  type KBListItem,
  type UnansweredListItem,
  type HandoffListItem,
  type AdminThreadItem,
  type UnansweredReason,
  type Page,
} from "../api/admin";
import type { MessageItem } from "../api/chat";

// ── KB ──────────────────────────────────────────────────────────────────────

export function useKBList(filters: { category?: string; page?: number; size?: number } = {}) {
  return useQuery<Page<KBListItem>>({
    queryKey: ["kb", filters],
    queryFn: () => listKB(filters),
    staleTime: STALE_10S,
  });
}

export function useKBCreate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: KBCreateRequest) => createKB(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kb"] }),
  });
}

export function useKBUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: KBUpdateRequest }) => updateKB(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kb"] }),
  });
}

export function useKBDelete() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteKB(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["kb"] }),
  });
}

// ── Unanswered ──────────────────────────────────────────────────────────────

export function useUnansweredList(
  filters: { reason?: UnansweredReason; resolved?: boolean; page?: number; size?: number } = {},
) {
  return useQuery<Page<UnansweredListItem>>({
    queryKey: ["unanswered", filters],
    queryFn: () => listUnanswered(filters),
    staleTime: STALE_10S,
  });
}

export function useUpdateUnanswered() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { resolved?: boolean } }) =>
      updateUnanswered(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["unanswered"] }),
  });
}

// ── Handoffs ────────────────────────────────────────────────────────────────

export function useHandoffsList(filters: { status?: string; page?: number; size?: number } = {}) {
  return useQuery<Page<HandoffListItem>>({
    queryKey: ["handoffs", filters],
    queryFn: () => listHandoffs(filters),
    staleTime: STALE_10S,
  });
}

export function useUpdateHandoff() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: HandoffUpdateRequest }) => updateHandoff(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["handoffs"] }),
  });
}

// ── Admin Threads ──────────────────────────────────────────────────────────

export function useAdminThreads(filters: { user_id?: string; page?: number; size?: number } = {}) {
  return useQuery<Page<AdminThreadItem>>({
    queryKey: ["admin-threads", filters],
    queryFn: () => listAllThreads(filters),
    staleTime: STALE_10S,
  });
}

export function useAdminMessages(threadId: string | undefined) {
  return useQuery<MessageItem[]>({
    queryKey: ["admin-messages", threadId],
    queryFn: () => getAdminMessages(threadId!),
    enabled: !!threadId,
    staleTime: STALE_10S,
  });
}
