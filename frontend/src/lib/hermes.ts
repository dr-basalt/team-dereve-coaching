const HERMES_API_URL = process.env.HERMES_API_URL || 'http://hermes:8080'

export async function hermesGet(path: string, userId: string) {
  const res = await fetch(`${HERMES_API_URL}${path}`, {
    headers: { 'x-user-id': userId },
  })
  return res.json()
}

export async function hermesPost(path: string, userId: string, body?: unknown) {
  const res = await fetch(`${HERMES_API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-user-id': userId },
    body: body ? JSON.stringify(body) : undefined,
  })
  return res.json()
}

export async function hermesPut(path: string, userId: string, body: unknown) {
  const res = await fetch(`${HERMES_API_URL}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', 'x-user-id': userId },
    body: JSON.stringify(body),
  })
  return res.json()
}

export async function hermesDelete(path: string, userId: string) {
  const res = await fetch(`${HERMES_API_URL}${path}`, {
    method: 'DELETE',
    headers: { 'x-user-id': userId },
  })
  return res.json()
}

export { HERMES_API_URL }
