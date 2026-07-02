import { ApiError } from "./client";

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

async function jsonRes<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export function listKB(params: { category?: string; page?: number; size?: number } = {}) {
  const qs = new URLSearchParams();
  if (params.category) qs.set("category", params.category);
  if (params.page) qs.set("page", String(params.page));
  if (params.size) qs.set("size", String(params.size));
  const url = `/admin/kb${qs.toString() ? `?${qs}` : ""}`;
  return fetch(url, { credentials: "include" }).then((r) => jsonRes<Page<KBListItem>>(r));
}

export function createKB(body: KBCreateRequest) {
  return fetch("/admin/kb", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  }).then((r) => jsonRes<KBListItem>(r));
}

export function updateKB(id: string, body: KBUpdateRequest) {
  return fetch(`/admin/kb/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  }).then((r) => jsonRes<KBListItem>(r));
}

export function deleteKB(id: string) {
  return fetch(`/admin/kb/${encodeURIComponent(id)}`, {
    method: "DELETE",
    credentials: "include",
  }).then((res) => {
    if (!res.ok) throw new ApiError(res.status, `Failed to delete: ${res.statusText}`);
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
  return fetch(url, { credentials: "include" }).then((r) => jsonRes<Page<UnansweredListItem>>(r));
}

export function updateUnanswered(id: string, body: { resolved?: boolean }) {
  return fetch(`/admin/unanswered/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  }).then((r) => jsonRes<UnansweredListItem>(r));
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
  return fetch(url, { credentials: "include" }).then((r) => jsonRes<Page<HandoffListItem>>(r));
}

export function updateHandoff(id: string, body: HandoffUpdateRequest) {
  return fetch(`/admin/handoffs/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  }).then((r) => jsonRes<HandoffListItem>(r));
}
