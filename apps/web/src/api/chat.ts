import { ApiError } from "./client";

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

export interface RenameRequest {
  title: string;
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
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    console.log(res);
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
  const res = await fetch("/threads", { credentials: "include" });
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
  return res.json();
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
  const res = await fetch(url, { credentials: "include" });
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
  return res.json();
}

export async function renameThread(
  id: string,
  body: RenameRequest,
): Promise<{ id: string; title: string; updated_at: string }> {
  const res = await fetch(`/threads/${encodeURIComponent(id)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    credentials: "include",
  });
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
  return res.json();
}

export async function deleteThread(id: string): Promise<void> {
  const res = await fetch(`/threads/${encodeURIComponent(id)}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new ApiError(res.status, (await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
}
