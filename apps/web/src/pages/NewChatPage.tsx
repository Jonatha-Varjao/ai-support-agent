import { useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useChatStore } from "../features/chat/store";
import { streamChat } from "../api/chat";
import ChatInput from "../components/ChatInput";

export default function NewChatPage() {
  const [streaming, setStreaming] = useState(false);
  const { startStream, appendStream, endStream, failStream, clearInFlight } = useChatStore();
  const abortRef = useRef<AbortController | null>(null);
  const navigate = useNavigate();

  const handleSend = useCallback(async (text: string) => {
    const tempId = crypto.randomUUID();
    startStream(tempId, "");
    setStreaming(true);

    const ctrl = new AbortController();
    abortRef.current = ctrl;

    try {
      for await (const ev of streamChat({ content: text, signal: ctrl.signal })) {
        if (ev.type === "token") {
          appendStream(ev.content);
        }
        if (ev.type === "done") {
          endStream();
          if (ev.thread_id) navigate(`/c/${ev.thread_id}`, { replace: true });
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
  }, [startStream, appendStream, endStream, failStream, clearInFlight, navigate]);

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
      <div className="w-full max-w-3xl">
        <ChatInput onSend={handleSend} disabled={streaming} />
      </div>
    </div>
  );
}
