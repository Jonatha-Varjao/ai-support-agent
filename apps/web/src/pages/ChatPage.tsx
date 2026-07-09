import { useEffect, useRef, useCallback } from "react";
import { useParams, Navigate } from "react-router-dom";
import { useChatStore } from "../features/chat/store";
import { useMessages } from "../hooks/useChatThreads";
import { useStreamChat } from "../hooks/useStreamChat";
import { ApiError } from "../api/client";
import MessageBubble from "../components/MessageBubble";
import TypingIndicator from "../components/TypingIndicator";
import ChatInput from "../components/ChatInput";
import Spinner from "../components/Spinner";

export default function ChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const { data: serverMessages, isLoading, error, refetch } = useMessages(threadId);
  const { inFlight, clearInFlight } = useChatStore();
  const { send, streaming } = useStreamChat({
    threadId,
    onDone: useCallback(async (tid: string) => {
      await refetch();
      clearInFlight();
    }, [refetch, clearInFlight]),
  });

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [serverMessages, inFlight?.text]);

  useEffect(() => {
    return () => {
      clearInFlight();
    };
  }, [clearInFlight, threadId]);

  useEffect(() => {
    if (serverMessages && serverMessages.length > 0 && inFlight && !streaming) {
      clearInFlight();
    }
  }, [serverMessages, inFlight, streaming, clearInFlight]);

  const handleSend = useCallback(async (text: string) => {
    if (!threadId) return;
    send(text);
  }, [threadId, send]);

  if (error instanceof ApiError && error.status === 404) {
    return <Navigate to="/" replace />;
  }

  const messages = serverMessages ?? [];

  return (
    <div className="flex flex-1 flex-col min-h-0">
      <div className="flex-1 overflow-y-auto px-4 py-6 min-h-0">
        <div className="mx-auto max-w-3xl">
          {isLoading && (
            <div className="mt-8 flex justify-center">
              <Spinner size="sm" />
            </div>
          )}
          {!isLoading && messages.length === 0 && (
            <div className="mt-16 text-center text-gray-400 dark:text-gray-500">
              Inicie a conversa enviando uma mensagem
            </div>
          )}
          {messages.filter(msg => msg.role !== "tool").map((msg) => (
            <MessageBubble key={msg.id} role={msg.role as "user" | "assistant"} content={msg.content} timestamp={msg.created_at} />
          ))}
          {inFlight && inFlight.threadId === threadId && inFlight.userContent && (
            <MessageBubble role="user" content={inFlight.userContent} timestamp={inFlight.createdAt} />
          )}
          {inFlight && inFlight.threadId === threadId && (
            inFlight.text ? (
              <MessageBubble role="assistant" content={inFlight.text} />
            ) : (
              <TypingIndicator />
            )
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <ChatInput onSend={handleSend} disabled={streaming} />
    </div>
  );
}
