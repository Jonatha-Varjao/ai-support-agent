import { useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useChatStore } from "../features/chat/store";
import { useStreamChat } from "../hooks/useStreamChat";
import MessageBubble from "../components/MessageBubble";
import TypingIndicator from "../components/TypingIndicator";
import ChatInput from "../components/ChatInput";

export default function NewChatPage() {
  const { inFlight } = useChatStore();
  const navigate = useNavigate();
  const onDone = useCallback((tid: string) => navigate(`/c/${tid}`, { replace: true }), [navigate]);
  const { send, streaming } = useStreamChat({ onDone });

  const handleSend = useCallback(async (text: string) => {
    send(text);
  }, [send]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-semibold text-gray-700 dark:text-gray-300">
          Comece uma conversa
        </h2>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
          Faça uma pergunta sobre a Mission
        </p>
      </div>
      {inFlight && (
        <div className="w-full max-w-3xl mb-4">
          <MessageBubble role="user" content={inFlight.userContent} timestamp={inFlight.createdAt} />
          {inFlight.text ? (
            <MessageBubble role="assistant" content={inFlight.text} />
          ) : (
            <TypingIndicator />
          )}
        </div>
      )}
      <div className="w-full max-w-3xl">
        <ChatInput onSend={handleSend} disabled={streaming} />
      </div>
    </div>
  );
}
