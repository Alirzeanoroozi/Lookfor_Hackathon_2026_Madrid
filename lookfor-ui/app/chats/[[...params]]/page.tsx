"use client"

import { useRef } from "react"
import { useParams, useRouter } from "next/navigation"
import { ArrowUpIcon, ToolboxIcon, WrenchIcon } from "lucide-react"
import { Textimation } from "textimation"

import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { useCreateConversation } from "@/mutators/use-create-conversation"
import { useConversation } from "@/queries/use-conversation"
import { useInput } from "@/stores/input-store"

export default function Page() {
  const router = useRouter()
  const prompt = useInput((s) => s.prompt)
  const setPrompt = useInput((s) => s.setPrompt)
  const params = useParams()
  const chatId = params.params?.[0]
  const containerRef = useRef<HTMLDivElement>(null)
  const { data: conversation } = useConversation(chatId)
  const { mutate: createConversation, isPending } = useCreateConversation()

  const handleSend = () => {
    if (!prompt) return
    if (chatId) {
      createConversation(
        { prompt, id: chatId },
        {
          onSuccess: () => {
            setPrompt("")
            setTimeout(() => {
              containerRef.current?.scrollTo({
                top: containerRef.current.scrollHeight,
                behavior: "smooth",
              })
            }, 250)
          },
        }
      )
    } else {
      const uuid = crypto.randomUUID()
      createConversation({ prompt, id: uuid }, { onSuccess: () => router.push(`/chats/${uuid}`) })
    }
  }

  if (conversation) {
    return (
      <main className="flex h-svh w-full flex-col place-items-center">
        <div
          ref={containerRef}
          className="container mx-auto flex h-full flex-col gap-4 overflow-y-auto py-4 text-xs"
        >
          <div className="mx-auto flex max-w-xl flex-col gap-4">
            {conversation.messages.map((message, idx) => {
              switch (message.role) {
                case "user": {
                  return (
                    <div key={idx} className="bg-card ml-auto rounded-lg p-2">
                      <p>{message.content}</p>
                    </div>
                  )
                }
                case "assistant": {
                  return (
                    <div key={idx} className="rounded-lg p-2">
                      <Textimation
                        text={message.content}
                        type="incremental"
                        className="font-mono text-xs"
                        Comp="p"
                      />
                    </div>
                  )
                }
              }
            })}

            {conversation.tool_calls?.length > 0 && (
              <div className="flex items-center gap-2">
                <WrenchIcon className="size-3" />
                {conversation.tool_calls.map((tool) => (
                  <div key={tool.tool_name}>{tool.tool_name}</div>
                ))}
              </div>
            )}

            {isPending && (
              <Textimation
                text="THINKING..."
                type="incremental"
                className="animate-pulse p-2 font-mono text-xs"
                Comp="p"
              />
            )}
          </div>
        </div>

        <div className="relative w-full max-w-xl">
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

  return (
    <main className="grid h-svh w-full grid-cols-1 grid-rows-2 place-items-center items-end justify-center gap-4">
      <Textimation
        text={isPending ? "Thinking..." : "Hey, How can I help you today?"}
        type="random"
        className="font-mono text-xs"
        Comp="p"
      />

      <div className="relative w-full max-w-xl">
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
