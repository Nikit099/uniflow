import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { api, type User } from '../../shared/api'

export function DemoLogin({ onLogin }: { onLogin: (user: User) => void }) {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const login = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const user = await api<User>('/auth/demo/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      })
      onLogin(user)
    } catch {
      setError(t('loginFailed'))
      setBusy(false)
    }
  }

  return <main className="login-shell">
    <section className="login-card">
      <div className="login-heading"><div className="mark">U</div><h1>UniFlow</h1></div>
      <form className="login-form" onSubmit={(event) => void login(event)}>
        <label><span>{t('username')}</span><input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} /></label>
        <label><span>{t('password')}</span><input type="password" autoComplete="current-password" required value={password} onChange={(event) => setPassword(event.target.value)} /></label>
        {error && <p className="inline-error">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>{busy ? t('loading') : t('login')}</button>
      </form>
      <div className="account-list" aria-label={t('demoAccounts')}>
        <div><span>student</span><code>student123</code></div>
        <div><span>staff</span><code>staff123</code></div>
        <div><span>admin</span><code>admin123</code></div>
      </div>
    </section>
  </main>
}
