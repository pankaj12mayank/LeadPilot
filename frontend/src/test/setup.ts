import '@testing-library/jest-dom/vitest'

Object.defineProperty(window, 'scrollTo', {
  value: () => {},
  writable: true,
})
import '@testing-library/jest-dom/vitest'
