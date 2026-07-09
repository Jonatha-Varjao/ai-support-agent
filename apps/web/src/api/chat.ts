import { apiFetch, ApiError } from "./client";

export interface ThreadListItem {
  id: string;
  title: string;
  updated_at: string;
}

export interface MessageItem {
  id: string;
  thread_id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  created_at: string;
}

export type ChatEvent =
  | { type: "token"; content: string }
  | { type: "done"; message_id: string; thread_id: string; cached?: boolean; blocked?: boolean };

export async function* streamChat(opts: {
  thread_id?: string;
  content: string;
  signal?: AbortSignal;
}): AsyncGenerator<ChatEvent> {
  const res = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id: opts.thread_id,
      content: opts.content,
    }),
    credentials: "include",
    signal: opts.signal,
  });

  if (!res.ok) {
    if (res.status === 401) {
      window.dispatchEvent(new CustomEvent("auth:expired"));
    }
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }

  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (value) buffer += decoder.decode(value, { stream: true });
      if (done && buffer === "") break;

      const parts = buffer.split("\n\n");
      buffer = done ? "" : (parts.pop() ?? "");

      for (const part of parts) {
        const line = part.trim();
        if (!line.startsWith("data: ")) continue;
        const json = line.slice(6);
        try {
          const raw = JSON.parse(json);
          if (raw.type === "token" || raw.type === "done") {
            yield raw as ChatEvent;
          }
          if (raw.type === "done") return;
        } catch {
          // skip malformed JSON frames
        }
      }

      if (done) break;
    }
  } finally {
    reader.releaseLock();
  }
}

export async function listThreads(): Promise<ThreadListItem[]> {
  return apiFetch<ThreadListItem[]>("/threads");
}

export async function getMessages(
  threadId: string,
  opts?: { before?: string; limit?: number },
): Promise<MessageItem[]> {
  const params = new URLSearchParams();
  if (opts?.before) params.set("before", opts.before);
  if (opts?.limit) params.set("limit", String(opts.limit));
  const qs = params.toString();
  const url = `/threads/${encodeURIComponent(threadId)}/messages${qs ? `?${qs}` : ""}`;
  return apiFetch<MessageItem[]>(url);
}

export async function renameThread(
  id: string,
  body: { title: string },
): Promise<{ id: string; title: string; updated_at: string }> {
  return apiFetch(`/threads/${encodeURIComponent(id)}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export async function deleteThread(id: string): Promise<void> {
  return apiFetch<void>(`/threads/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
}
