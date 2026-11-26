import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { getErrorMessage } from '../utils/format'
import { Button, ErrorAlert, Field } from '../components/ui'

function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="hidden flex-col justify-between bg-brand-900 p-12 text-brand-50 lg:flex">
        <div className="flex items-center gap-2 text-lg font-bold text-white">
          <img src="/favicon.svg" alt="" className="h-8 w-8" /> SettleUp
        </div>
        <div>
          <p className="text-3xl font-semibold leading-snug text-white">
            Share expenses with roommates and friends — and always know who owes whom.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-brand-100">
            <li>• Split bills equally or by custom amounts, to the paisa</li>
            <li>• See live balances for every group</li>
            <li>• Settle up with the fewest repayments we can find</li>
          </ul>
        </div>
        <p className="text-xs text-brand-100/70">A final-year BTech CSE project.</p>
      </div>
      <div className="flex items-center justify-center px-4 py-12 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2 text-lg font-bold lg:hidden">
            <img src="/favicon.svg" alt="" className="h-8 w-8" /> SettleUp
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-slate-500">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <p className="mt-6 text-center text-sm text-slate-500">{footer}</p>
        </div>
      </div>
    </div>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email.trim(), password)
      navigate(location.state?.from || '/dashboard', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Login failed.'))
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Log in to see your groups and balances."
      footer={<>New here? <Link to="/register" className="font-semibold text-brand-700">Create an account</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Email" htmlFor="email">
          <input id="email" type="email" autoComplete="email" className="input" value={email}
            onChange={(e) => setEmail(e.target.value)} required />
        </Field>
        <Field label="Password" htmlFor="password">
          <input id="password" type="password" autoComplete="current-password" className="input" value={password}
            onChange={(e) => setPassword(e.target.value)} required />
        </Field>
        <ErrorAlert message={error} />
        <Button type="submit" className="w-full" loading={loading}>Log in</Button>
      </form>
    </AuthShell>
  )
}

export function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  async function handleSubmit(event) {
    event.preventDefault()
    if (form.password.length < 8) return setError('Password must be at least 8 characters.')
    if (form.password !== form.confirm) return setError('Passwords do not match.')
    setError('')
    setLoading(true)
    try {
      await register(form.name.trim(), form.email.trim(), form.password)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(getErrorMessage(err, 'Registration failed.'))
      setLoading(false)
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="It takes less than a minute."
      footer={<>Already registered? <Link to="/login" className="font-semibold text-brand-700">Log in</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <Field label="Full name" htmlFor="name">
          <input id="name" className="input" autoComplete="name" value={form.name} onChange={set('name')} maxLength={100} required />
        </Field>
        <Field label="Email" htmlFor="email">
          <input id="email" type="email" className="input" autoComplete="email" value={form.email} onChange={set('email')} required />
        </Field>
        <Field label="Password" htmlFor="password" hint="At least 8 characters">
          <input id="password" type="password" className="input" autoComplete="new-password" value={form.password}
            onChange={set('password')} maxLength={72} required />
        </Field>
        <Field label="Confirm password" htmlFor="confirm">
          <input id="confirm" type="password" className="input" autoComplete="new-password" value={form.confirm}
            onChange={set('confirm')} maxLength={72} required />
        </Field>
        <ErrorAlert message={error} />
        <Button type="submit" className="w-full" loading={loading}>Create account</Button>
      </form>
    </AuthShell>
  )
}
