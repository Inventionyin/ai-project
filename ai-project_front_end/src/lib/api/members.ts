import { authHeader, requestJson } from '@/lib/api/client'

export type MemberListItem = {
  id: string
  userId: string
  userName: string
  userEmail: string
  role: string
  createdAt: number | null
}

export type MemberListData = {
  items: MemberListItem[]
  total: number
}

export type UserSuggestion = {
  id: string
  name: string
  email: string
}

export async function fetchMembers(projectId: string, page = 1, pageSize = 50) {
  const pid = String(projectId || '').trim()
  if (!pid) return { items: [], total: 0 }
  const query = new URLSearchParams({ projectId: pid, page: String(page), pageSize: String(pageSize) })
  return requestJson<MemberListData>(`/api/projects/${encodeURIComponent(pid)}/members?${query.toString()}`, {
    method: 'GET',
    headers: authHeader(),
  })
}

export async function addMember(projectId: string, userId: string, role: string) {
  const pid = String(projectId || '').trim()
  return requestJson<MemberListItem>(`/api/projects/${encodeURIComponent(pid)}/members`, {
    method: 'POST',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ userId, role }),
  })
}

export async function updateMemberRole(projectId: string, memberId: string, role: string) {
  const pid = String(projectId || '').trim()
  return requestJson<MemberListItem>(`/api/projects/${encodeURIComponent(pid)}/members/${encodeURIComponent(memberId)}`, {
    method: 'PUT',
    headers: { ...authHeader(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ role }),
  })
}

export async function removeMember(projectId: string, memberId: string) {
  const pid = String(projectId || '').trim()
  return requestJson<{ ok: boolean }>(`/api/projects/${encodeURIComponent(pid)}/members/${encodeURIComponent(memberId)}`, {
    method: 'DELETE',
    headers: authHeader(),
  })
}

export async function searchUsers(projectId: string, query: string) {
  const pid = String(projectId || '').trim()
  const q = new URLSearchParams({ projectId: pid, q: query })
  return requestJson<UserSuggestion[]>(`/api/projects/${encodeURIComponent(pid)}/members/users?${q.toString()}`, {
    method: 'GET',
    headers: authHeader(),
  })
}
