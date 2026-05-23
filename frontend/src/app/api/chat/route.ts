import { auth } from '@/auth'

const HERMES_API_URL = process.env.HERMES_API_URL || 'http://management:8080'
const HERMES_API_KEY = process.env.HERMES_API_KEY || 'unused'

export async function POST(req: Request) {
  const session = await auth()
  const userId = session?.user?.email || 'anonymous'
  const { messages } = await req.json()

  const response = await fetch(`${HERMES_API_URL}/v1/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${HERMES_API_KEY}`,
      'x-user-id': userId,
    },
    body: JSON.stringify({
      model: 'hermes-coaching',
      messages,
      stream: true,
    }),
  })

  // Parse OpenAI SSE and re-emit as plain text stream for useChat
  const reader = response.body?.getReader()
  if (!reader) {
    return new Response('No response body', { status: 502 })
  }

  const encoder = new TextEncoder()
  const decoder = new TextDecoder()

  const stream = new ReadableStream({
    async start(controller) {
      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6).trim()
            if (data === '[DONE]') continue
            try {
              const parsed = JSON.parse(data)
              const content = parsed.choices?.[0]?.delta?.content
              if (content) {
                controller.enqueue(encoder.encode(content))
              }
            } catch {
              // ignore parse errors
            }
          }
        }
      }
      controller.close()
    },
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  })
}
