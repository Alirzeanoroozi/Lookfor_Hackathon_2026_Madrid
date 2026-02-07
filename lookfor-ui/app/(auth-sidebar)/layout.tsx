"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { useLocalStorage } from "usehooks-ts"

import { SidebarProvider } from "@/components/ui/sidebar"
import { Spinner } from "@/components/ui/spinner"
import { AppSidebar } from "@/components/app-sidebar"

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  const router = useRouter()
  const [sessionId] = useLocalStorage("sessionId", null)

  useEffect(() => {
    if (!sessionId) {
      router.push("/auth")
    }
  }, [sessionId, router])

  if (!sessionId) {
    return (
      <main className="flex h-screen items-center justify-center">
        <Spinner className="size-6" />
      </main>
    )
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      {children}
    </SidebarProvider>
  )
}
