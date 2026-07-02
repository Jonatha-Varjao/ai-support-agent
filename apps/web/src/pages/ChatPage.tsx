import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Navigate } from "react-router-dom";
import { useChatStore } from "../features/chat/store";
import { useMessages } from "../hooks/useChatThreads";
import { streamChat } from "../api/chat";
import { ApiError } from "../api/client";
import MessageBubble from "../components/MessageBubble";
import ChatInput from "../components/ChatInput";

export default function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const { data: serverMessages, isLoading, error, refetch } = useMessages(threadId);
  const { inFlight, startStream, appendStream, endStream, failStream, clearInFlight } = useChatStore();

  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [serverMessages, inFlight?.text]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
      clearInFlight();
    };
  }, [clearInFlight, threadId]);

  const handleSend = useCallback(async (text: string) => {
    if (!threadId) return;

    const assistantId = crypto.randomUUID();
    startStream(threadId, assistantId);
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      for await (const ev of streamChat({ thread_id: threadId, content: text, signal: ctrl.signal })) {
        if (ev.type === "token") {
          appendStream(ev.content);
        }
        if (ev.type === "done") {
          endStream();
          refetch();
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        failStream("Erro ao gerar resposta");
      }
      clearInFlight();
    } finally {
      setStreaming(false);
    }
  }, [threadId, startStream, appendStream, endStream, failStream, clearInFlight, refetch]);

  if (error instanceof ApiError && error.status === 404) {
    return <Navigate to="/" replace />;
  }

  const messages = serverMessages ?? [];

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="mx-auto max-w-3xl">
          {isLoading && (
            <div className="mt-8 flex justify-center">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
            </div>
          )}
          {!isLoading && messages.length === 0 && (
            <div className="mt-16 text-center text-gray-400 dark:text-gray-500">
              Inicie a conversa enviando uma mensagem
            </div>
          )}
          {messages.map((msg) => (
            <MessageBubble key={msg.id} role={msg.role as "user" | "assistant"} content={msg.content} />
          ))}
          {inFlight && inFlight.threadId === threadId && (
            <MessageBubble role="assistant" content={inFlight.text} />
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <ChatInput onSend={handleSend} disabled={streaming} />
    </div>
  );
}
