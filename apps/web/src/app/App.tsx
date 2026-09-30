import { useEffect, useRef, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Languages, LogOut } from 'lucide-react'
import { ApiError, api, setCsrf, type User } from '../shared/api'
import { DemoLogin } from '../features/auth/DemoLogin'
import { StudentDashboard } from '../features/student-dashboard/StudentDashboard'
import { CasePage } from '../features/cases/CasePage'
import { StaffQueue } from '../features/staff-queue/StaffQueue'
import { StaffReview } from '../features/staff-review/StaffReview'
import { AdminDashboard } from '../features/admin/AdminDashboard'
import { maxBridge } from './max'

export function App() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const client = useQueryClient()
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [maxAuthFailed, setMaxAuthFailed] = useState(false)
  const [authUnavailable, setAuthUnavailable] = useState(false)
  const authStarted = useRef(false)
  useEffect(() => {
    if (authStarted.current) return
    authStarted.current = true
    const restoreSession = async () => {
      try {
        const value = await api<User>('/auth/me')
        setCsrf(value.csrf_token)
        setUser(value)
        const casePath = value.role === 'STUDENT' ? maxBridge.startCasePath() : ''
        if (casePath) navigate(casePath)
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) {
          setAuthUnavailable(true)
          setUser(null)
          return
        }
        if (!maxBridge.isAvailable()) {
          setUser(null)
          return
        }
        try {
          const value = await api<User>('/auth/max', {
            method: 'POST',
            body: JSON.stringify({ init_data: maxBridge.initData() }),
          })
          setCsrf(value.csrf_token)
          setUser(value)
          const casePath = value.role === 'STUDENT' ? maxBridge.startCasePath() : ''
          if (casePath) navigate(casePath)
        } catch (maxError) {
          if (maxError instanceof ApiError && maxError.status < 500) setMaxAuthFailed(true)
          else setAuthUnavailable(true)
          setUser(null)
        }
      }
    }
    void restoreSession()
  }, [navigate])
  const loggedIn = (value: User) => { client.clear(); setCsrf(value.csrf_token); setUser(value); navigate(homePath(value.role)) }
  const logout = async () => { await api('/auth/logout', { method: 'POST' }); client.clear(); setUser(null); navigate('/demo-login') }
  const changeLanguage = () => { const language = i18n.language === 'ru' ? 'en' : 'ru'; void i18n.changeLanguage(language); localStorage.setItem('language', language) }
  if (user === undefined) return <div className="center"><div className="spinner"/><span>{t('loading')}</span></div>
  if (authUnavailable) return <main className="auth-state"><section><p role="alert">{t('serviceUnavailable')}</p><button className="secondary" onClick={() => window.location.reload()}>{t('retry')}</button></section></main>
  if (maxAuthFailed) return <main className="auth-state"><section><p role="alert">{t('maxLoginFailed')}</p><button className="secondary" onClick={() => window.location.reload()}>{t('retry')}</button></section></main>
  return <>
    {user && <header className="topbar"><a className="brand" href="/"><span>U</span> UniFlow</a><div className="top-actions"><button className="ghost" onClick={changeLanguage}><Languages size={17}/>{t('language')}</button><span className="user-pill">{user.display_name}</span><button className="icon-button" aria-label={t('logout')} onClick={() => void logout()}><LogOut size={18}/></button></div></header>}
    <Routes>
      <Route path="/demo-login" element={user ? <Navigate to="/"/> : <DemoLogin onLogin={loggedIn}/>} />
      <Route path="/" element={!user ? <Navigate to="/demo-login"/> : user.role === 'STUDENT' ? <StudentDashboard/> : <Navigate to={homePath(user.role)} replace/>} />
      <Route path="/cases/:caseId" element={user ? <CasePage user={user}/> : <Navigate to="/demo-login"/>} />
      <Route path="/staff" element={user && user.role !== 'STUDENT' ? <StaffQueue/> : <Navigate to="/demo-login"/>} />
      <Route path="/staff/cases/:caseId" element={user && user.role !== 'STUDENT' ? <StaffReview/> : <Navigate to="/demo-login"/>} />
      <Route path="/admin" element={user?.role === 'ORG_ADMIN' ? <AdminDashboard/> : <Navigate to="/demo-login"/>} />
      <Route path="*" element={<Navigate to="/"/>}/>
    </Routes>
  </>
}

function homePath(role: User['role']) {
  return role === 'STUDENT' ? '/' : role === 'STAFF' ? '/staff' : '/admin'
}
