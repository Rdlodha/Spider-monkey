/**
 * Toast notification system for ReconForge.
 * Usage:
 *   import { useToast } from '../components/Toast'
 *   const { toast } = useToast()
 *   toast.success('Scan imported!')
 *   toast.error('Failed to connect')
 *   toast.info('Processing...')
 *   toast.warn('Token expires soon')
 */
import { createContext, useContext, useState, useCallback, useRef } from 'react'
import { CheckCircle, XCircle, AlertTriangle, Info, X } from 'lucide-react'

const ToastContext = createContext(null)

const ICONS = {
  success: <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0" />,
  error:   <XCircle    className="w-5 h-5 text-red-400    flex-shrink-0" />,
  warn:    <AlertTriangle className="w-5 h-5 text-yellow-400 flex-shrink-0" />,
  info:    <Info       className="w-5 h-5 text-blue-400   flex-shrink-0" />,
}

const COLORS = {
  success: 'border-emerald-500/40 bg-emerald-950/80',
  error:   'border-red-500/40    bg-red-950/80',
  warn:    'border-yellow-500/40 bg-yellow-950/80',
  info:    'border-blue-500/40   bg-blue-950/80',
}

let _idCounter = 0

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const timers = useRef({})

  const dismiss = useCallback((id) => {
    clearTimeout(timers.current[id])
    delete timers.current[id]
    setToasts(ts => ts.filter(t => t.id !== id))
  }, [])

  const show = useCallback((type, message, duration = 4000) => {
    const id = ++_idCounter
    setToasts(ts => [...ts, { id, type, message }])
    timers.current[id] = setTimeout(() => dismiss(id), duration)
    return id
  }, [dismiss])

  const toast = {
    success: (msg, dur) => show('success', msg, dur),
    error:   (msg, dur) => show('error',   msg, dur),
    warn:    (msg, dur) => show('warn',    msg, dur),
    info:    (msg, dur) => show('info',    msg, dur),
  }

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}

      {/* Toast container — fixed bottom-right */}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 w-80 max-w-full pointer-events-none"
      >
        {toasts.map(t => (
          <div
            key={t.id}
            role="alert"
            className={`
              flex items-start gap-3 px-4 py-3 rounded-lg border
              backdrop-blur-sm shadow-xl pointer-events-auto
              animate-in slide-in-from-bottom-2 fade-in duration-200
              ${COLORS[t.type]}
            `}
          >
            {ICONS[t.type]}
            <p className="text-sm text-slate-100 flex-1 leading-snug">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              aria-label="Dismiss notification"
              className="text-slate-400 hover:text-white transition-colors mt-0.5"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
