import { create } from 'zustand'

export type Message = {
  role: 'user' | 'assistant'
  content: string
}

export  const useConversation = create<{
  prompt: string
  setPrompt: (value: string) => void
  conversationId: string | null
  messages: Message[]
  setData: (conversationId: string, messages: Message[]) => void
  addMessage: (message: Message) => void
}>((set) => ({
  prompt: "",
  setPrompt: (value: string) => set({ prompt: value }),
  conversationId: null,
  messages: [],
  setData: (conversationId: string, messages: Message[]) => set({ conversationId, messages,  }),
  addMessage: (message: Message) => set((state) => ({ messages: [...state.messages, message] })),
}))

