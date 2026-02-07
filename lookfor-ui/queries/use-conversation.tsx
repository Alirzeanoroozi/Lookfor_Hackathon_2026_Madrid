import { useQuery } from "@tanstack/react-query"

import type { Message } from "@/stores/conversation-store"

type ConversationResponse = {
  session_id: string
  messages: Message[]
  escalated: boolean
}

export type ConversationData = {
  conversation_id: string
  messages: Message[]
  escalated: boolean
}

export function useConversation(conversationId: string) {
  return useQuery({
    queryKey: ["conversations", conversationId],
    queryFn: async () => {
      const res = await fetch(`http://localhost:8000/conversations/${conversationId}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      })
      if (!res.ok) {
        throw new Error("Failed to fetch conversation")
      }
      const data: ConversationResponse = await res.json()
      return {
        conversation_id: conversationId,
        messages: data.messages,
        escalated: data.escalated,
      } as ConversationData
    },
  })
}
