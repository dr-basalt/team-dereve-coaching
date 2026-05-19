import { auth } from '@/auth'
import { hermesGet, hermesPut, hermesDelete } from '@/lib/hermes'
import { NextRequest } from 'next/server'

export async function GET(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth()
  if (!session?.user) return Response.json({}, { status: 401 })
  const { id } = await params
  const data = await hermesGet(`/agents/${id}`, '')
  return Response.json(data)
}

export async function PUT(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth()
  if (!session?.user) return Response.json({}, { status: 401 })
  const { id } = await params
  const body = await req.json()
  const data = await hermesPut(`/agents/${id}`, '', body)
  return Response.json(data)
}

export async function DELETE(_req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth()
  if (!session?.user) return Response.json({}, { status: 401 })
  const { id } = await params
  const data = await hermesDelete(`/agents/${id}`, '')
  return Response.json(data)
}
