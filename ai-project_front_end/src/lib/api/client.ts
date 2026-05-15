export type ApiResponse<T> = {
  code?: number
  message?: string
  data?: T
  requestId?: string
}

const resolveApiBaseUrl = () => {
  const envBase = String(import.meta.env.VITE_API_BASE_URL || '').trim()
  if (!envBase) return ''
  return envBase.endsWith('/') ? envBase.slice(0, -1) : envBase
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

export async function requestJson<T>(path: string, init: RequestInit) {
  const baseUrl = resolveApiBaseUrl()
  const res = await fetch(`${baseUrl}${path}`, init)
  let payload: ApiResponse<T> = {}
  try {
    payload = (await res.json()) as ApiResponse<T>
  } catch {
    payload = {}
  }
  if (!res.ok || payload.code !== 0) {
    const codeText = typeof payload.code === 'number' ? `（${payload.code}）` : ''
    const err = new Error(payload.message ? `${payload.message}${codeText}` : `请求失败${codeText}`)
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).apiCode =
      typeof payload.code === 'number' ? payload.code : undefined
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).requestId =
      typeof payload.requestId === 'string' ? payload.requestId : undefined
    ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).httpStatus = res.status
    throw err
  }
  return payload.data as T
}

export function authHeader() {
  return { Authorization: resolveAuthHeader() }
}
