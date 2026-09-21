export type User = { id: string; display_name: string; email: string | null; preferred_language: string; role: 'STUDENT' | 'STAFF' | 'ORG_ADMIN'; organization_id: string; csrf_token: string }
export type Document = { id: string; original_filename: string; mime_type: string; uploaded_at: string }
export type Requirement = { id: string; status: string; version: number; student_comment: string | null; staff_comment: string | null; requirement: { id: string; code: string; title_i18n: Record<string,string>; description_i18n: Record<string,string>; mandatory: boolean; source_ids: string[]; student_action_i18n: Record<string,string> }; documents: Document[] }
export type Case = { id: string; status: string; version: number; procedure_version_id: string; assigned_staff_user_id: string | null; submitted_at: string | null; verified_at: string | null; due_at: string | null; risk_level: string; progress: number; student_name: string | null; procedure_title: Record<string,string> | null; requirements: Requirement[] }

let csrf = ''
export function setCsrf(value: string) { csrf = value }
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (init.method && init.method !== 'GET') headers.set('X-CSRF-Token', csrf)
  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: 'include' })
  if (!response.ok) { const data = await response.json().catch(() => null) as { detail?: string; error?: {message?: string} } | null; throw new Error(data?.error?.message || data?.detail || `HTTP ${response.status}`) }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const localize = (value: Record<string,string> | null | undefined, language: string) => value?.[language] || value?.ru || ''
