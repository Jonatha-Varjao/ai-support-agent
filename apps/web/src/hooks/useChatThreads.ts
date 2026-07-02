import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listThreads,
  getMessages,
  renameThread,
  deleteThread,
  type ThreadListItem,
  type MessageItem,
  type RenameRequest,
} from "../api/chat";

export function useThreads(enabled = true) {
  return useQuery<ThreadListItem[]>({
    queryKey: ["threads"],
    queryFn: listThreads,
    enabled,
    staleTime: 30_000,
  });
}

export function useMessages(threadId: string | undefined, enabled = true) {
  return useQuery<MessageItem[]>({
    queryKey: ["messages", threadId],
    queryFn: () => getMessages(threadId!),
    enabled: enabled && !!threadId,
    staleTime: 10_000,
  });
}

export function useRenameThread() {
  const qc = useQueryClient();
  return useMutation<{ id: string; title: string; updated_at: string }, Error, { id: string; title: string }>({
    mutationFn: ({ id, title }) => renameThread(id, { title } as RenameRequest),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["threads"] });
    },
  });
}

export function useDeleteThread() {
  const qc = useQueryClient();
  return useMutation<void, Error, string>({
    mutationFn: (id: string) => deleteThread(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["threads"] });
    },
  });
}
