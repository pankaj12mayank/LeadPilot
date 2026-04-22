import { Component, type ErrorInfo, type ReactNode } from 'react'

type Props = { children: ReactNode }

type State = { hasError: boolean; message: string }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, message: '' }

  static getDerivedStateFromError(err: Error): State {
    return { hasError: true, message: err.message || 'Something went wrong' }
  }

  componentDidCatch(err: Error, info: ErrorInfo) {
    console.error('LeadPilot UI error:', err, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-dvh flex-col items-center justify-center bg-surface px-4 py-12 text-ink">
          <div className="max-w-md rounded-2xl border border-surface-border bg-premium-card-light p-8 shadow-card dark:bg-premium-card-dark">
            <h1 className="font-display text-xl font-bold text-ink">This view could not be displayed</h1>
            <p className="mt-3 text-sm leading-relaxed text-ink-muted">
              A runtime error occurred. Reload the page to continue. If the problem persists, check the browser console
              for details.
            </p>
            {import.meta.env.DEV ? (
              <pre className="mt-4 max-h-40 overflow-auto rounded-lg border border-surface-border bg-field p-3 text-xs text-ink-muted">
                {this.state.message}
              </pre>
            ) : null}
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="mt-6 w-full rounded-xl border border-amber-500/35 bg-amber-500/12 px-4 py-3 text-sm font-semibold text-amber-900 transition hover:border-amber-500/50 dark:text-amber-100"
            >
              Reload page
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
