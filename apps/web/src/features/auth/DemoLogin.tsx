import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowRight, Building2, GraduationCap, UserRoundCog } from 'lucide-react'
import { api, type User } from '../../shared/api'

export function DemoLogin({ onLogin }: { onLogin: (user: User) => void }) {
  const { t } = useTranslation()
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const roles = [
    { id: 'student', title: t('student'), icon: GraduationCap, description: 'student@demo.local' },
    { id: 'staff', title: t('staff'), icon: Building2, description: 'staff@demo.local' },
    { id: 'org_admin', title: t('admin'), icon: UserRoundCog, description: 'admin@demo.local' },
  ]
  const login = async (role: string) => { setBusy(role); setError(''); try { onLogin(await api<User>('/auth/demo/login', { method: 'POST', body: JSON.stringify({ role }) })) } catch (err) { setError(err instanceof Error ? err.message : t('error')); setBusy('') } }
  return <main className="login-shell"><section className="login-intro"><div className="mark">U</div><p className="eyebrow">UNIFLOW · DEMO UNIVERSITY</p><h1>{t('title')}</h1><p>{t('subtitle')}</p><div className="trust-note"><ShieldText/><span>Статусы университета и государственных органов всегда разделены.</span></div></section><section className="login-card"><div><h2>{t('login')}</h2><p>Выберите роль для локального синтетического сценария.</p></div><div className="role-list">{roles.map(({id,title,icon:Icon,description}) => <button className="role-button" key={id} disabled={Boolean(busy)} onClick={() => void login(id)}><span className="role-icon"><Icon size={22}/></span><span><strong>{title}</strong><small>{description}</small></span><ArrowRight className="role-arrow" size={19}/>{busy === id && <span className="mini-spinner"/>}</button>)}</div>{error && <p className="inline-error">{error}</p>}<small className="credentials">Локальные синтетические учётные записи. Пароль не используется на этой странице.</small></section></main>
}

function ShieldText(){ return <div className="checkmark">✓</div> }

