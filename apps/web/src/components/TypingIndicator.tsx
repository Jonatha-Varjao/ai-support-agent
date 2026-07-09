export default function TypingIndicator() {
  return (
    <div className="flex justify-start mb-4">
      <div className="max-w-[70%] rounded-2xl px-4 py-3 bg-gray-200 dark:bg-gray-700">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
        </span>
      </div>
    </div>
  );
}
