import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/layouts/AppShell'
import { useAuthStore } from '@/store/authStore'

const LoginPage = lazy(() => import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const LandingPage = lazy(() => import('@/pages/LandingPage').then((m) => ({ default: m.LandingPage })))
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const BuyerDashboardPage = lazy(() => import('@/pages/BuyerDashboardPage').then((m) => ({ default: m.BuyerDashboardPage })))
const SearchLeadsPage = lazy(() => import('@/pages/SearchLeadsPage').then((m) => ({ default: m.SearchLeadsPage })))
const LeadsPage = lazy(() => import('@/pages/LeadsPage').then((m) => ({ default: m.LeadsPage })))
const OutreachQueuePage = lazy(() => import('@/pages/OutreachQueuePage').then((m) => ({ default: m.OutreachQueuePage })))
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })))
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const AboutPage = lazy(() => import('@/pages/AboutPage').then((m) => ({ default: m.AboutPage })))
const AdminLayout = lazy(() => import('@/pages/admin/AdminLayout').then((m) => ({ default: m.AdminLayout })))
const AdminOverviewPage = lazy(() => import('@/pages/admin/AdminOverviewPage').then((m) => ({ default: m.AdminOverviewPage })))
const AdminUsersPage = lazy(() => import('@/pages/admin/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })))
const AdminBrandingPage = lazy(() => import('@/pages/admin/AdminBrandingPage').then((m) => ({ default: m.AdminBrandingPage })))

function PageFallback() {
  return (
    <div className="mx-auto max-w-[1600px] space-y-6 p-4">
      <div className="skeleton-shimmer h-12 max-w-md rounded-2xl" />
      <div className="skeleton-shimmer h-96 w-full rounded-2xl" />
    </div>
  )
}

function RequireAuth() {
  const token = useAuthStore((s) => s.token)
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <AppShell />
}

function RequireRole({ allowed }: { allowed: Array<'admin' | 'user' | 'buyer'> }) {
  const user = useAuthStore((s) => s.user)
  const role = (user?.role || 'user') as 'admin' | 'user' | 'buyer'
  if (!allowed.includes(role)) {
    return <Navigate to="/dashboard" replace />
  }
  return <Outlet />
}

export default function App() {
  return (
    <Suspense fallback={<PageFallback />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin/login" element={<Navigate to="/login?next=%2Fadmin" replace />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/overview" replace />} />
          <Route path="overview" element={<AdminOverviewPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="branding" element={<AdminBrandingPage />} />
        </Route>
        <Route element={<RequireAuth />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route element={<RequireRole allowed={['admin', 'buyer']} />}>
            <Route path="/buyer-dashboard" element={<BuyerDashboardPage />} />
          </Route>
          <Route element={<RequireRole allowed={['admin', 'user']} />}>
            <Route path="/search-leads" element={<SearchLeadsPage />} />
            <Route path="/leads" element={<LeadsPage />} />
            <Route path="/outreach-queue" element={<OutreachQueuePage />} />
          </Route>
          <Route path="/platforms" element={<Navigate to="/search-leads" replace />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/about" element={<AboutPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  )
}
