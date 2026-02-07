"use client"

import { useRouter } from "next/navigation"
import { ArrowUpIcon } from "lucide-react"
import { Textimation } from "textimation"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useCreateConversation } from "@/mutators/use-create-conversation"
import { useConversation } from "@/stores/conversation-store"

export default function Page() {
  const router = useRouter()
  const prompt = useConversation((s) => s.prompt)
  const setPrompt = useConversation((s) => s.setPrompt)

  const { mutate: createConversation, isPending } = useCreateConversation()

  const handleSend = () => {
    if (!prompt) return
    const uuid = crypto.randomUUID()
    createConversation({ prompt, id: uuid }, { onSuccess: () => router.push(`/chats/${uuid}`) })
  }

  return (
    <main className="grid h-svh w-full grid-cols-1 grid-rows-2 place-items-center items-end justify-center gap-4">
      <Textimation
        text={isPending ? "Thinking..." : "Hey, How can I help you today?"}
        type="random"
        className="font-mono text-xs"
        Comp="p"
      />

      <div className="relative w-full max-w-md">
        <Textarea
          disabled={isPending}
          placeholder="Type your message here..."
          className="h-20 w-full rounded-b-none"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
        />

        <Button
          disabled={isPending}
          className="absolute right-1 bottom-1"
          size="icon"
          onClick={handleSend}
        >
          {isPending ? <Spinner className="size-4" /> : <ArrowUpIcon className="size-4" />}
        </Button>
      </div>
    </main>
  )
}
