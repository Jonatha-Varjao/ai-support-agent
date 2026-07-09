import { apiFetch } from "./client";
import type { MessageItem } from "./chat";

// ── Shared ──────────────────────────────────────────────────────────────────

export type KBCategory = "product" | "service" | "flow" | "institutional" | "faq";

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

// ── KB ──────────────────────────────────────────────────────────────────────

export interface KBListItem {
  id: string;
  category: KBCategory;
  title: string;
  content: string;
  updated_at: string;
  has_embedding: boolean;
}

export interface KBCreateRequest {
  category?: KBCategory;
  title: string;
  content: string;
}

export interface KBUpdateRequest {
  category?: KBCategory;
  title?: string;
  content?: string;
}

export const KB_CATEGORIES: { value: KBCategory; label: string }[] = [
  { value: "product", label: "Produto" },
  { value: "service", label: "Serviço" },
  { value: "flow", label: "Fluxo interno" },
  { value: "institutional", label: "Informação institucional" },
  { value: "faq", label: "FAQ" },
];

export const KB_CATEGORY_LABELS: Record<KBCategory, string> = Object.fromEntries(
  KB_CATEGORIES.map((c) => [c.value, c.label]),
) as Record<KBCategory, string>;

export const ADMIN_PAGE_SIZE = 50;

export function listKB(params: { category?: string; page?: number; size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.page) qs.set("page", String(params.page));
  if (params.size) qs.set("size", String(params.size));
  const url = `/admin/kb${qs.toString() ? `?${qs}` : ""}`;
  return apiFetch<Page<KBListItem>>(url);
}

export function createKB(body: KBCreateRequest) {
  return apiFetch<KBListItem>("/admin/kb", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateKB(id: string, body: KBUpdateRequest) {
  return apiFetch<KBListItem>(`/admin/kb/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteKB(id: string) {
  return apiFetch<void>(`/admin/kb/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}

// ── Unanswered ──────────────────────────────────────────────────────────────

export type UnansweredReason = "no_context" | "injection";

export interface UnansweredListItem {
  id: string;
  thread_id: string;
  message_id: string;
  query: string;
  top_sim: number;
  reason: UnansweredReason;
  resolved: boolean;
  created_at: string;
  user_email: string | null;
  thread_title: string | null;
}

export function listUnanswered(
  params: { reason?: UnansweredReason; resolved?: boolean; page?: number; size?: number } = {},
) {
  const qs = new URLSearchParams();
  if (params.reason) qs.set("reason", params.reason);
  if (params.resolved !== undefined) qs.set("resolved", String(params.resolved));
  if (params.page) qs.set("page", String(params.page));
  if (params.size) qs.set("size", String(params.size));
  const url = `/admin/unanswered${qs.toString() ? `?${qs}` : ""}`;
  return apiFetch<Page<UnansweredListItem>>(url);
}

export function updateUnanswered(id: string, body: { resolved?: boolean }) {
  return apiFetch<UnansweredListItem>(`/admin/unanswered/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Handoffs ────────────────────────────────────────────────────────────────

export type HandoffStatus = "open" | "contacted" | "closed";

export interface HandoffListItem {
  id: string;
  user_email: string | null;
  thread_id: string;
  thread_title: string | null;
  status: HandoffStatus;
  created_at: string;
}

export interface HandoffUpdateRequest {
  status?: HandoffStatus;
}

export function listHandoffs(params: { status?: string; page?: number; size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.status && params.status !== "all") qs.set("status", params.status);
  if (params.page) qs.set("page", String(params.page));
  if (params.size) qs.set("size", String(params.size));
  const url = `/admin/handoffs${qs.toString() ? `?${qs}` : ""}`;
  return apiFetch<Page<HandoffListItem>>(url);
}

export function updateHandoff(id: string, body: HandoffUpdateRequest) {
  return apiFetch<HandoffListItem>(`/admin/handoffs/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ── Admin Threads ──────────────────────────────────────────────────────────

export interface AdminThreadItem {
  id: string;
  title: string;
  user_email: string;
  updated_at: string;
}

export function listAllThreads(params: { user_id?: string; page?: number; size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.user_id) qs.set("user_id", params.user_id);
  if (params.page) qs.set("page", String(params.page));
  if (params.size) qs.set("size", String(params.size));
  const url = `/admin/threads${qs.toString() ? `?${qs}` : ""}`;
  return apiFetch<Page<AdminThreadItem>>(url);
}

export function getAdminMessages(threadId: string, limit?: number) {
  const qs = new URLSearchParams();
  if (limit) qs.set("limit", String(limit));
  const url = `/admin/threads/${encodeURIComponent(threadId)}/messages${qs.toString() ? `?${qs}` : ""}`;
  return apiFetch<MessageItem[]>(url);
}
