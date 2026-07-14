const BASE = ''

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    let detail = text
    try {
      const parsed = JSON.parse(text)
      if (parsed?.detail) detail = parsed.detail
    } catch {
      // not JSON, keep raw text
    }
    throw new Error(detail || `Request failed with status ${res.status}`)
  }
  return res.json()
}

export const api = {
  get: (path) => request(path),
  post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
}
