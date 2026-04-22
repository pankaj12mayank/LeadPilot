import { Toaster } from 'sonner'

import { useThemeStore } from '@/store/themeStore'

export function AppToaster() {
  const resolved = useThemeStore((s) => s.resolved)
  return (
    <Toaster
      theme={resolved}
      position="top-right"
      closeButton
      richColors
      toastOptions={{
        classNames: {
          toast: 'font-sans',
        },
      }}
    />
  )
}
