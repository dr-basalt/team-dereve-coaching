import { createOpenAI } from '@ai-sdk/openai'
import { streamText } from 'ai'
import { auth } from '@/auth'

export async function POST(req: Request) {
  const session = await auth()
  const userId = session?.user?.email || 'anonymous'
  const { messages } = await req.json()

  const hermes = createOpenAI({
    baseURL: (process.env.HERMES_API_URL || 'http://hermes:8080') + '/v1',
    apiKey: process.env.HERMES_API_KEY || 'unused',
    headers: { 'x-user-id': userId },
  })

  const result = streamText({
    model: hermes('hermes-coaching'),
    messages,
  })

  return result.toDataStreamResponse()
}
