import { auth } from '@/auth'
import { hermesDelete } from '@/lib/hermes'
import { NextRequest } from 'next/server'

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth()
  if (!session?.user?.email) return Response.json({}, { status: 401 })
  const { id } = await params
  const data = await hermesDelete(`/documents/${id}`, session.user.email)
  return Response.json(data)
}
