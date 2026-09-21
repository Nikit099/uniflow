import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Languages, LogOut, ShieldCheck } from 'lucide-react'
import { api, setCsrf, type User } from '../shared/api'
import { DemoLogin } from '../features/auth/DemoLogin'
import { StudentDashboard } from '../features/student-dashboard/StudentDashboard'
import { CasePage } from '../features/cases/CasePage'
import { StaffQueue } from '../features/staff-queue/StaffQueue'
import { StaffReview } from '../features/staff-review/StaffReview'
import { AdminDashboard } from '../features/admin/AdminDashboard'

export function App() {
  const { t, i18n } = useTranslation()
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null | undefined>(undefined)
  useEffect(() => { api<User>('/auth/me').then((value) => { setCsrf(value.csrf_token); setUser(value) }).catch(() => setUser(null)) }, [])
  const loggedIn = (value: User) => { setCsrf(value.csrf_token); setUser(value); navigate(value.role === 'STUDENT' ? '/' : value.role === 'STAFF' ? '/staff' : '/admin') }
  const logout = async () => { await api('/auth/logout', { method: 'POST' }); setUser(null); navigate('/demo-login') }
  const changeLanguage = () => { const language = i18n.language === 'ru' ? 'en' : 'ru'; void i18n.changeLanguage(language); localStorage.setItem('language', language) }
  if (user === undefined) return <div className="center"><div className="spinner"/><span>{t('loading')}</span></div>
  return <>
    <div className="demo-banner"><ShieldCheck size={15}/>{t('demo')}</div>
    {user && <header className="topbar"><a className="brand" href="/"><span>U</span> UniFlow</a><div className="top-actions"><button className="ghost" onClick={changeLanguage}><Languages size={17}/>{t('language')}</button><span className="user-pill">{user.display_name}</span><button className="icon-button" aria-label={t('logout')} onClick={() => void logout()}><LogOut size={18}/></button></div></header>}
    <Routes>
      <Route path="/demo-login" element={user ? <Navigate to="/"/> : <DemoLogin onLogin={loggedIn}/>} />
      <Route path="/" element={!user ? <Navigate to="/demo-login"/> : user.role === 'STUDENT' ? <StudentDashboard/> : <Navigate to={user.role === 'STAFF' ? '/staff' : '/admin'}/>} />
      <Route path="/cases/:caseId" element={user ? <CasePage user={user}/> : <Navigate to="/demo-login"/>} />
      <Route path="/staff" element={user && user.role !== 'STUDENT' ? <StaffQueue/> : <Navigate to="/demo-login"/>} />
      <Route path="/staff/cases/:caseId" element={user && user.role !== 'STUDENT' ? <StaffReview/> : <Navigate to="/demo-login"/>} />
      <Route path="/admin" element={user?.role === 'ORG_ADMIN' ? <AdminDashboard/> : <Navigate to="/demo-login"/>} />
      <Route path="*" element={<Navigate to="/"/>}/>
    </Routes>
  </>
}

