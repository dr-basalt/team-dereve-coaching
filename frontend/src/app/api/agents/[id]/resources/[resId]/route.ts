import { auth } from '@/auth'
import { hermesDelete } from '@/lib/hermes'
import { NextRequest } from 'next/server'

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string; resId: string }> }) {
  const session = await auth()
  if (!session?.user) return Response.json({}, { status: 401 })
  const { id, resId } = await params
  const data = await hermesDelete(`/agents/${id}/resources/${resId}`, '')
  return Response.json(data)
}
