"use client"

import { useRouter } from "next/navigation"
import { ArrowRightIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { useCreateSession } from "@/mutators/use-create-session"

export default function AuthPage() {
  return (
    <main className="flex h-svh items-center justify-center">
      <FormExample />
    </main>
  )
}

function FormExample() {
  const router = useRouter()
  const { mutate, isPending } = useCreateSession()

  const handleSubmit = (e: React.SyntheticEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.target as HTMLFormElement)
    const fName = formData.get("f-name") as string
    const lName = formData.get("l-name") as string
    const email = formData.get("email") as string
    mutate(
      { fName, lName, email },
      {
        onError: (error) => {
          toast.error(error.message)
        },
        onSuccess: () => {
          router.push("/")
        },
      }
    )
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader>
        <CardTitle>User Information</CardTitle>
        <CardDescription>Please fill in your details below</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit}>
          <FieldGroup>
            <div className="grid grid-cols-2 gap-4">
              <Field>
                <FieldLabel htmlFor="f-name">First Name</FieldLabel>
                <Input id="f-name" name="f-name" placeholder="Dwayne" required />
              </Field>
              <Field>
                <FieldLabel htmlFor="l-name">Last Name</FieldLabel>
                <Input id="l-name" name="l-name" placeholder="Johnson" required />
              </Field>
            </div>

            <Field>
              <FieldLabel htmlFor="email">Email</FieldLabel>
              <Input id="email" name="email" placeholder="dwayne.johnson@example.com" required />
            </Field>
            <Field orientation="horizontal">
              <Button type="submit" className="ml-auto" disabled={isPending}>
                {isPending ? <Spinner /> : <ArrowRightIcon />}
                Sign Up
              </Button>
            </Field>
          </FieldGroup>
        </form>
      </CardContent>
    </Card>
  )
}
