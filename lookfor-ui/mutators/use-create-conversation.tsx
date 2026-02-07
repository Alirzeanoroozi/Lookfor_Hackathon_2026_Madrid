import { useMutation, useQueryClient } from "@tanstack/react-query"

import type { ConversationData } from "@/queries/use-conversation"

type ConversationResponse = {
  session_id: string
  final_message: string
  escalated: boolean
}

type CreateConversationData = {
  conversation_id: string
  final_message: string
  escalated: boolean
}

export function useCreateConversation() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async ({ prompt, id }: { prompt: string; id: string }) => {
      const response = await fetch(`http://localhost:8000/conversations/${id}`, {
        method: "POST",
        body: JSON.stringify({
          message: prompt,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      })
      if (!response.ok) {
        throw new Error("Failed to create conversation")
      }

      const data: ConversationResponse = await response.json()

      return {
        conversation_id: id,
        final_message: data.final_message,
        escalated: data.escalated,
      } as CreateConversationData
    },
    onSuccess: (data, { prompt }) => {
      queryClient.setQueryData(
        ["conversations", data.conversation_id],
        (prev: ConversationData) => {
          if (!prev) {
            return {
              conversation_id: data.conversation_id,
              messages: [
                { role: "user", content: prompt },
                { role: "assistant", content: data.final_message },
              ],
              escalated: data.escalated,
              tool_calls: [],
            }
          }
          return {
            ...prev,
            messages: [...prev.messages, { role: "assistant", content: data.final_message }],
          }
        }
      )

      queryClient.invalidateQueries({ queryKey: ["conversations"] })
    },
  })
}
