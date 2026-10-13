const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const TOKEN = import.meta.env.VITE_API_TOKEN

function authHeaders(extra = {}) {
  return {
    ...(TOKEN ? { Authorization: `Bearer ${TOKEN}` } : {}),
    ...extra,
  }
}

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = 'API Request Failed'
    try {
      const data = await response.json()
      errorDetail = data.detail || errorDetail
    } catch {
      errorDetail = response.statusText
    }
    throw new Error(errorDetail)
  }
  return response.json()
}

async function fetchWithAuth(path, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...authHeaders(),
    ...options.headers,
  }
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  return handleResponse(response)
}

async function uploadFile(path, formData) {
  // Do NOT set Content-Type — let the browser set multipart/form-data with boundary
  const response = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  return handleResponse(response)
}

async function downloadFile(path, filename) {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: authHeaders(),
  })
  if (!response.ok) {
    throw new Error('Download failed')
  }
  const blob = await response.blob()
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename || 'download'
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}

export const api = {
  get: (path) => fetchWithAuth(path),
  post: (path, body) => fetchWithAuth(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: (path, body) => fetchWithAuth(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: (path) => fetchWithAuth(path),
  upload: (path, formData) => uploadFile(path, formData),
  download: (path, filename) => downloadFile(path, filename),
}
