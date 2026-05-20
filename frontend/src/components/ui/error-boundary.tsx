import React from 'react'

interface Props {
  children: React.ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends React.Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('App crashed:', error, info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-slate-950 flex items-center justify-center p-8">
          <div className="bg-slate-900 border border-red-500/30 rounded-xl p-8 max-w-2xl w-full">
            <h1 className="text-xl font-bold text-red-400 mb-4">App Error</h1>
            <pre className="text-sm text-slate-300 font-mono whitespace-pre-wrap break-all">
              {this.state.error.message}
            </pre>
            <pre className="text-xs text-slate-500 font-mono mt-4 whitespace-pre-wrap">
              {this.state.error.stack}
            </pre>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}