import { auth } from '@/auth'
import { HERMES_API_URL } from '@/lib/hermes'
import { NextRequest } from 'next/server'

export async function POST(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const session = await auth()
  if (!session?.user) return Response.json({}, { status: 401 })
  const { id } = await params
  const formData = await req.formData()
  const res = await fetch(`${HERMES_API_URL}/agents/${id}/resources/upload`, {
    method: 'POST',
    body: formData,
  })
  const data = await res.json()
  return Response.json(data)
}
