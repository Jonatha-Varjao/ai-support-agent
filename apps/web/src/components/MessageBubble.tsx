import Markdown from "react-markdown";
import { formatTime } from "../lib/formatTime";

interface Props {
  role: "user" | "assistant";
  content: string;
  timestamp?: string;
}

export default function MessageBubble({ role, content, timestamp }: Props) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className="max-w-[70%]">
        <div
          className={`rounded-2xl px-4 py-2 whitespace-pre-wrap ${
            isUser
              ? "bg-blue-600 text-white"
              : "bg-gray-200 text-gray-900 dark:bg-gray-700 dark:text-gray-100"
          }`}
        >
          <Markdown
            components={{
              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
              strong: ({ children }) => <strong className="font-bold">{children}</strong>,
              em: ({ children }) => <em className="italic">{children}</em>,
              code: ({ children }) => <code className="rounded bg-black/10 px-1 py-0.5 text-sm dark:bg-white/10">{children}</code>,
              ul: ({ children }) => <ul className="mb-2 list-inside list-disc">{children}</ul>,
              ol: ({ children }) => <ol className="mb-2 list-inside list-decimal">{children}</ol>,
              li: ({ children }) => <li>{children}</li>,
              a: ({ href, children }) => <a href={href} className="text-blue-300 underline" target="_blank" rel="noopener noreferrer">{children}</a>,
            }}
          >
            {content}
          </Markdown>
        </div>
        {timestamp && (
          <div className={`mt-1 text-xs text-gray-400 dark:text-gray-500 ${isUser ? "text-right" : "text-left"}`}>
            {formatTime(timestamp)}
          </div>
        )}
      </div>
    </div>
  );
}
