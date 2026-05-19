import { auth } from '@/auth'
import { hermesGet } from '@/lib/hermes'

export async function GET() {
  const session = await auth()
  if (!session?.user?.email) return Response.json([], { status: 401 })
  const data = await hermesGet('/documents', session.user.email)
  return Response.json(data)
}
