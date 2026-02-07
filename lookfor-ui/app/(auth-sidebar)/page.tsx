"use client"

import { Textimation } from "textimation"

export default function Page() {
  return (
    <main className="flex h-svh w-full items-center justify-center">
      <Textimation
        text="Select a thread to continue"
        type="random"
        className="font-mono text-xs"
        Comp="p"
      />
    </main>
  )
}
