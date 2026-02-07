import { create } from 'zustand'

export type Message = {
  role: 'user' | 'assistant'
  content: string
}

export  const useInput = create<{
  prompt: string
  setPrompt: (value: string) => void
}>((set) => ({
  prompt: "",
  setPrompt: (value: string) => set({ prompt: value }),
}))

