import { auth } from '@/auth'
import { hermesGet, hermesPost } from '@/lib/hermes'

export async function GET() {
  const session = await auth()
  if (!session?.user) return Response.json([], { status: 401 })
  const data = await hermesGet('/agents', '')
  return Response.json(data)
}

export async function POST(req: Request) {
  const session = await auth()
  if (!session?.user) return Response.json({}, { status: 401 })
  const body = await req.json()
  const data = await hermesPost('/agents', '', body)
  return Response.json(data)
}
