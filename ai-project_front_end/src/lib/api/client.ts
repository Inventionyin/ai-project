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

const normalizeApiUrl = (path: string) => {
  const baseUrl = resolveApiBaseUrl()
  const normalizedPath = String(path || '').startsWith('/') ? String(path || '') : `/${String(path || '')}`
  const pathWithPrefix = normalizedPath.startsWith('/api') ? normalizedPath : `/api${normalizedPath}`

  if (!baseUrl) return pathWithPrefix
  if (baseUrl.endsWith('/api') && pathWithPrefix.startsWith('/api')) {
    return `${baseUrl}${pathWithPrefix.slice('/api'.length)}`
  }
  return `${baseUrl}${pathWithPrefix}`
}

const buildCurrentRedirect = () => {
  if (typeof window === 'undefined') return '/'
  return `${window.location.pathname}${window.location.search}${window.location.hash}`
}

export function clearAuthState() {
  localStorage.removeItem('accessToken')
  localStorage.removeItem('accessTokenExpiresAt')
  localStorage.removeItem('loginUsername')
}

export function redirectToLogin(redirect = buildCurrentRedirect()) {
  if (typeof window === 'undefined') return
  if (window.location.pathname === '/login') return
  const query = new URLSearchParams({ redirect: redirect || '/' })
  window.location.assign(`/login?${query.toString()}`)
}

export function isAuthExpiredResponse(res: Response, payload: ApiResponse<unknown>) {
  return res.status === 401 || payload.code === 40101
}

export function createApiError<T>(res: Response, payload: ApiResponse<T>, fallback = '请求失败') {
  const codeText = typeof payload.code === 'number' ? `（${payload.code}）` : ''
  const err = new Error(payload.message ? `${payload.message}${codeText}` : `${fallback}${codeText}`)
  ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).apiCode =
    typeof payload.code === 'number' ? payload.code : undefined
  ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).requestId =
    typeof payload.requestId === 'string' ? payload.requestId : undefined
  ;(err as { apiCode?: number; requestId?: string; httpStatus?: number }).httpStatus = res.status
  return err
}

export function handleAuthExpired() {
  clearAuthState()
  redirectToLogin()
  const err = new Error('登录已过期，请重新登录')
  ;(err as { apiCode?: number; httpStatus?: number }).apiCode = 40101
  ;(err as { apiCode?: number; httpStatus?: number }).httpStatus = 401
  return err
}

const resolveAuthHeader = () => {
  const accessToken = localStorage.getItem('accessToken')
  if (!accessToken) {
    throw new Error('登录状态已失效，请重新登录')
  }
  return `Bearer ${accessToken}`
}

export async function requestJson<T>(path: string, init: RequestInit) {
  const res = await fetch(normalizeApiUrl(path), init)
  let payload: ApiResponse<T> = {}
  try {
    payload = (await res.json()) as ApiResponse<T>
  } catch {
    payload = {}
  }
  if (!res.ok || payload.code !== 0) {
    if (isAuthExpiredResponse(res, payload)) {
      throw handleAuthExpired()
    }
    throw createApiError(res, payload)
  }
  return payload.data as T
}

export function authHeader() {
  return { Authorization: resolveAuthHeader() }
}
