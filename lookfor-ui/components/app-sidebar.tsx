"use client"

import Link from "next/link"
import { useParams } from "next/navigation"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
} from "@/components/ui/sidebar"
import { useConversations } from "@/queries/use-conversations"

export function AppSidebar() {
  const { data: conversations, isLoading } = useConversations()
  const params = useParams()
  const chatId = params.params?.[0] as string

  return (
    <Sidebar>
      <SidebarHeader />
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Conversations</SidebarGroupLabel>
          <SidebarGroupContent>
            {!conversations || isLoading ? (
              <SidebarMenuSkeleton />
            ) : (
              conversations.map((item) => (
                <SidebarMenuItem key={item.conversation_id}>
                  <SidebarMenuButton asChild isActive={chatId === String(item.conversation_id)}>
                    <Link href={`/chats/${item.conversation_id}`}>{item.created_at}</Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))
            )}
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup />
      </SidebarContent>
      <SidebarFooter />
    </Sidebar>
  )
}
