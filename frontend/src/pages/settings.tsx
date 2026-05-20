import { useState } from 'react'
import { User, Shield, Bell, Mail, CheckCircle2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/stores/authStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'

export function SettingsPage() {
  const user = useAuthStore((s) => s.user)
  const checkAuth = useAuthStore((s) => s.checkAuth)
  const forgotPassword = useAuthStore((s) => s.forgotPassword)
  const resetPassword = useAuthStore((s) => s.resetPassword)
  const toast = useUIStore((s) => s.toast)

  const [vrSending, setVrSending] = useState(false)
  const [verifyToken, setVerifyToken] = useState('')
  const [verifying, setVerifying] = useState(false)

  const [resetEmail, setResetEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [resetStep, setResetStep] = useState<'email' | 'token'>('email')

  const handleResendVerification = async () => {
    setVrSending(true)
    try {
      const r = await api.post<{ message: string }>('/api/auth/resend-verification')
      toast(r.message, 'success')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    } finally { setVrSending(false) }
  }

  const handleVerifyEmail = async () => {
    if (!verifyToken) { toast('Enter verification token', 'error'); return }
    setVerifying(true)
    try {
      const r = await api.post<{ message: string }>('/api/auth/verify-email', { token: verifyToken })
      toast(r.message, 'success')
      setVerifyToken('')
      await checkAuth()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    } finally { setVerifying(false) }
  }

  const handleResetRequest = async () => {
    if (!resetEmail) { toast('Enter your email', 'error'); return }
    try {
      const m = await forgotPassword(resetEmail)
      toast(m, 'success')
      setResetStep('token')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleResetConfirm = async () => {
    if (!resetToken || !newPassword) { toast('Token and new password required', 'error'); return }
    try {
      const m = await resetPassword(resetToken, newPassword)
      toast(m, 'success')
      setResetToken(''); setNewPassword(''); setResetStep('email')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-xl font-bold text-slate-100 mb-6">Settings</h1>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <User size={18} className="text-emerald-400" />
          <h2 className="text-lg font-semibold text-slate-200">Profile</h2>
        </div>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-slate-500">Email</p>
            <p className="text-slate-200 font-medium">{user?.email || '—'}</p>
          </div>
          <div>
            <p className="text-slate-500">Role</p>
            <p className="text-slate-200 font-medium">
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${user?.role === 'admin' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
                {user?.role || '—'}
              </span>
            </p>
          </div>
        </div>
      </div>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <Mail size={18} className="text-emerald-400" />
          <h2 className="text-lg font-semibold text-slate-200">Email Verification</h2>
        </div>
        <div className="flex items-center gap-3 mb-4">
          <span className={`text-xs px-2 py-0.5 rounded-full ${user?.email_verified ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
            {user?.email_verified ? 'Verified' : 'Not verified'}
          </span>
          {!user?.email_verified && (
            <Button size="sm" variant="secondary" loading={vrSending} onClick={handleResendVerification}>
              Resend Code
            </Button>
          )}
        </div>
        {!user?.email_verified && (
          <div className="flex gap-2">
            <Input value={verifyToken} onChange={(e) => setVerifyToken(e.target.value)} placeholder="Enter verification token" className="flex-1" />
            <Button size="sm" loading={verifying} onClick={handleVerifyEmail}><CheckCircle2 size={14} className="mr-1" /> Verify</Button>
          </div>
        )}
      </div>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-4">
          <Shield size={18} className="text-emerald-400" />
          <h2 className="text-lg font-semibold text-slate-200">Security</h2>
        </div>
        {resetStep === 'email' ? (
          <>
            <p className="text-sm text-slate-500 mb-3">Request a password reset link (token is logged in dev server)</p>
            <div className="flex gap-2">
              <Input value={resetEmail} onChange={(e) => setResetEmail(e.target.value)} placeholder="Your email" className="flex-1" />
              <Button onClick={handleResetRequest}>Send Reset</Button>
            </div>
          </>
        ) : (
          <>
            <p className="text-sm text-slate-500 mb-3">Enter the reset token and your new password</p>
            <div className="space-y-3">
              <Input value={resetToken} onChange={(e) => setResetToken(e.target.value)} placeholder="Reset token from server log" />
              <Input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="New password" />
              <div className="flex gap-2">
                <Button variant="secondary" onClick={() => setResetStep('email')}>Back</Button>
                <Button onClick={handleResetConfirm}>Reset Password</Button>
              </div>
            </div>
          </>
        )}
      </div>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <Bell size={18} className="text-emerald-400" />
          <h2 className="text-lg font-semibold text-slate-200">About</h2>
        </div>
        <p className="text-sm text-slate-500">Komajdon v0.3.0 — Visual Backends for MongoDB</p>
      </div>
    </div>
  )
}
