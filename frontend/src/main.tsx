import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'

import App from './App.tsx'
import 'sonner/dist/styles.css'
import './index.css'
import { AppToaster } from '@/components/layout/AppToaster'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { ThemeProvider } from '@/components/layout/ThemeProvider'
import { useAuthStore } from '@/store/authStore'
import { useBrandingStore } from '@/store/brandingStore'
import { initDocumentTheme } from '@/store/themeStore'

initDocumentTheme()
useAuthStore.getState().hydrate()
void useBrandingStore.getState().load()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <AppToaster />
      <BrowserRouter>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </BrowserRouter>
    </ThemeProvider>
  </StrictMode>,
)
