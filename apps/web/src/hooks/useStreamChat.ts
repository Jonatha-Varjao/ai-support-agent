import { useState, useRef, useCallback, useEffect } from "react";
import { useChatStore } from "../features/chat/store";
import { streamChat } from "../api/chat";

interface Opts {
  threadId?: string;
  onDone: (threadId: string) => void;
}

export function useStreamChat({ threadId, onDone }: Opts) {
  const { startStream, appendStream, clearInFlight } = useChatStore();
  const abortRef = useRef<AbortController | null>(null);
  const [streaming, setStreaming] = useState(false);

  useEffect(() => {
    return () => { abortRef.current?.abort(); };
  }, []);

  const send = useCallback(async (text: string) => {
    const tempId = threadId ?? crypto.randomUUID();
    startStream(tempId, text);
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      for await (const ev of streamChat({ thread_id: threadId, content: text, signal: ctrl.signal })) {
        if (ev.type === "token") appendStream(ev.content);
        if (ev.type === "done") await onDone(ev.thread_id);
      }
    } catch {
      clearInFlight();
    } finally {
      setStreaming(false);
    }
  }, [threadId, startStream, appendStream, clearInFlight, onDone]);

  return { send, streaming };
}
