import { auth } from '@/auth'
import { HERMES_API_URL } from '@/lib/hermes'

export async function POST(req: Request) {
  const session = await auth()
  if (!session?.user?.email) return Response.json({}, { status: 401 })

  const formData = await req.formData()
  const res = await fetch(`${HERMES_API_URL}/documents/upload`, {
    method: 'POST',
    headers: { 'x-user-id': session.user.email },
    body: formData,
  })
  const data = await res.json()
  return Response.json(data)
}
