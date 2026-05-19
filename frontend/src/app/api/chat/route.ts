import { NextRequest } from 'next/server'

const HERMES_API_URL = process.env.HERMES_API_URL || 'http://hermes:8080'

export async function POST(req: NextRequest) {
  const body = await req.json()

  const response = await fetch(`${HERMES_API_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      model: 'hermes-coaching',
      messages: body.messages,
      stream: true,
    }),
  })

  return new Response(response.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  })
}
