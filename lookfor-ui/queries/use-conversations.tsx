import { useQuery } from "@tanstack/react-query"

type ConversationResponse = {
  session_id: number
  customer_email: string
  first_name: string
  last_name: string
  shopify_customer_id: string
  escalated: boolean
  created_at: string
}

export type ConversationData = {
  conversation_id: string
  customer_email: string
  first_name: string
  last_name: string
  shopify_customer_id: string
  escalated: boolean
  created_at: string
}

export function useConversations() {
  return useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const res = await fetch(`http://localhost:8000/conversations`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      })
      if (!res.ok) {
        throw new Error("Failed to fetch conversation")
      }
      const data: ConversationResponse[] = await res.json()
      return data.map((conversation) => ({
        conversation_id: conversation.shopify_customer_id,
        customer_email: conversation.customer_email,
        first_name: conversation.first_name,
        last_name: conversation.last_name,
        shopify_customer_id: conversation.shopify_customer_id,
        escalated: conversation.escalated,
        created_at: conversation.created_at,
      })) as ConversationData[]
    },
  })
}
