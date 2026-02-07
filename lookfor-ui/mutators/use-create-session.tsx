import { useMutation } from "@tanstack/react-query"

type SessionResponse = {
  customer_email: string
  first_name: string
  last_name: string
  session_id: number
  shopify_customer_id: string
}

export function useCreateSession() {
  return useMutation({
    mutationFn: async (data: { fName: string; lName: string; email: string }) => {
      const response = await fetch("http://localhost:8000/sessions", {
        method: "POST",
        body: JSON.stringify({
          customer_email: data.email,
          first_name: data.fName,
          last_name: data.lName,
          shopify_customer_id: `gid://shopify/Customer/${Math.floor(Math.random() * 100000000)}`,
        }),
        headers: {
          "Content-Type": "application/json",
        },
      })

      if (!response.ok) {
        throw new Error("Failed to create session")
      }

      const json = (await response.json()) as SessionResponse

      localStorage.setItem("sessionId", json.session_id.toString())

      return json
    },
  })
}
