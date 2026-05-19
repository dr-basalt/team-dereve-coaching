import { auth } from '@/auth'
import { hermesGet, hermesPost } from '@/lib/hermes'

export async function GET() {
  const session = await auth()
  if (!session?.user?.email) return Response.json([], { status: 401 })
  const data = await hermesGet('/conversations', session.user.email)
  return Response.json(data)
}

export async function POST() {
  const session = await auth()
  if (!session?.user?.email) return Response.json({}, { status: 401 })
  const data = await hermesPost('/conversations', session.user.email)
  return Response.json(data)
}
