import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { useModelStore } from '@/stores/modelStore'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [mode, setMode] = useState<'auth' | 'forgot' | 'reset'>('auth')
  const [resetToken, setResetToken] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const signin = useAuthStore((s) => s.signin)
  const signup = useAuthStore((s) => s.signup)
  const forgotPassword = useAuthStore((s) => s.forgotPassword)
  const resetPassword = useAuthStore((s) => s.resetPassword)
  const toast = useUIStore((s) => s.toast)
  const loadModels = useModelStore((s) => s.loadModels)
  const navigate = useNavigate()

  const handleAuth = async () => {
    if (!email || !password) { toast('Fill in all fields', 'error'); return }
    setLoading(true)
    try {
      if (tab === 'login') await signin(email, password)
      else await signup(email, password)
      await loadModels()
      navigate('/')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    } finally { setLoading(false) }
  }

  const handleForgot = async () => {
    setLoading(true); setMessage('')
    try {
      const msg = await forgotPassword(email)
      if (import.meta.env.DEV) {
        setMessage(msg + ' (check server logs for dev token)')
      } else {
        setMessage(msg)
      }
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    } finally { setLoading(false) }
  }

  const handleReset = async () => {
    if (password !== confirmPassword) { toast('Passwords do not match', 'error'); return }
    setLoading(true)
    try {
      const msg = await resetPassword(resetToken, password)
      toast(msg, 'success')
      setMode('auth')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    } finally { setLoading(false) }
  }

  if (mode === 'forgot') return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <button onClick={() => setMode('auth')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 mb-6">
          <ArrowLeft size={14} /> Back
        </button>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Reset Password</h2>
        <p className="text-sm text-slate-500 mb-6">Enter your email to receive a reset link</p>
        <Input label="Email" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        {message && <p className="text-xs text-emerald-400 mt-2">{message}</p>}
        <Button className="w-full mt-4" loading={loading} onClick={handleForgot}>Send Reset Link</Button>
      </motion.div>
    </div>
  )

  if (mode === 'reset') return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
        <button onClick={() => setMode('auth')} className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 mb-6">
          <ArrowLeft size={14} /> Back
        </button>
        <h2 className="text-xl font-bold text-slate-100 mb-2">New Password</h2>
        <div className="space-y-4">
          <Input label="Reset Token" placeholder="Paste token from email" value={resetToken} onChange={(e) => setResetToken(e.target.value)} />
          <Input label="New Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Input label="Confirm Password" type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          <Button className="w-full" loading={loading} onClick={handleReset}>Reset Password</Button>
        </div>
      </motion.div>
    </div>
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
          <div className="flex items-center justify-center gap-3 mb-2">
            <img src="/logo.png" alt="Komajdon" className="w-10 h-10 rounded-xl" />
          </div>
          <h1 className="text-2xl font-bold text-center text-slate-100">Komajdon</h1>
          <p className="text-sm text-center text-slate-500 mb-8">Visual Backends for MongoDB</p>

          <div className="flex bg-slate-800/50 rounded-lg p-1 mb-6">
            <button onClick={() => setTab('login')} className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${tab === 'login' ? 'bg-mongodb-green text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}>Sign In</button>
            <button onClick={() => setTab('register')} className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${tab === 'register' ? 'bg-mongodb-green text-white shadow-lg' : 'text-slate-400 hover:text-slate-200'}`}>Sign Up</button>
          </div>

          <div className="space-y-4">
            <Input label="Email" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAuth()} />
            <Input label="Password" type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && handleAuth()} />
            <Button className="w-full" size="lg" loading={loading} onClick={handleAuth}>
              {tab === 'login' ? 'Sign In' : 'Sign Up'}
            </Button>
          </div>

          <div className="mt-4 flex justify-between text-xs">
            <button onClick={() => { setMode('forgot'); setMessage('') }} className="text-slate-500 hover:text-slate-300">Forgot password?</button>
            <button onClick={() => setMode('reset')} className="text-slate-500 hover:text-slate-300">Have a reset token?</button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
