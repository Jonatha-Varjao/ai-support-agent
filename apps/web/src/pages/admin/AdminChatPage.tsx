import { useParams, useNavigate, Navigate } from "react-router-dom";
import { useAdminMessages } from "../../hooks/useAdmin";
import MessageBubble from "../../components/MessageBubble";
import Spinner from "../../components/Spinner";
import EmptyState from "../../components/EmptyState";

export default function AdminChatPage() {
  const { threadId } = useParams<{ threadId: string }>();
  const { data: messages, isLoading, error } = useAdminMessages(threadId);
  const navigate = useNavigate();

  if (error) return <Navigate to="/admin/threads" replace />;

  const items = (messages ?? []).filter((msg) => msg.role !== "tool");

  return (
    <div>
      <div className="mb-4">
        <button
          onClick={() => navigate(-1)}
          className="text-sm text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
        >
          ← Voltar
        </button>
      </div>
      {isLoading ? (
        <div className="flex justify-center mt-8">
          <Spinner />
        </div>
      ) : items.length === 0 ? (
        <EmptyState message="Nenhuma mensagem nesta conversa." />
      ) : (
        <div className="mx-auto max-w-3xl">
          {items.map((msg) => (
            <MessageBubble
              key={msg.id}
              role={msg.role as "user" | "assistant"}
              content={msg.content}
              timestamp={msg.created_at}
            />
          ))}
        </div>
      )}
    </div>
  );
}
