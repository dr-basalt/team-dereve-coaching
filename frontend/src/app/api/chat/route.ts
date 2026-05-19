import { createOpenAI } from '@ai-sdk/openai'
import { streamText } from 'ai'

const hermes = createOpenAI({
  baseURL: (process.env.HERMES_API_URL || 'http://hermes:8080') + '/v1',
  apiKey: 'unused',
})

export async function POST(req: Request) {
  const { messages } = await req.json()

  const result = streamText({
    model: hermes('hermes-coaching'),
    messages,
  })

  return result.toDataStreamResponse()
}
