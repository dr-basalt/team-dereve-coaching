import { auth } from '@/auth'
import { hermesGet } from '@/lib/hermes'
import { NextRequest } from 'next/server'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth()
  if (!session?.user) return Response.json([], { status: 401 })
  const { id } = await params
  const data = await hermesGet(`/agents/${id}/resources`, '')
  return Response.json(data)
}
