export default async function ThreadPage({ params }: { params: Promise<{ thread: string }> }) {
  const { thread } = await params
  return <div>Thread: {thread}</div>
}
