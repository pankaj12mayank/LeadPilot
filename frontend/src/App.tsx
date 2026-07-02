import { lazy, Suspense } from 'react'
import { Navigate, Outlet, Route, Routes } from 'react-router-dom'

import { AppShell } from '@/layouts/AppShell'
import { useAuthStore } from '@/store/authStore'
import { LandingLayout } from '@/landing/components/LandingLayout'

const LoginPage = lazy(() => import('@/pages/LoginPage').then((m) => ({ default: m.LoginPage })))
const DashboardPage = lazy(() => import('@/pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const BuyerDashboardPage = lazy(() => import('@/pages/BuyerDashboardPage').then((m) => ({ default: m.BuyerDashboardPage })))
const SearchLeadsPage = lazy(() => import('@/pages/SearchLeadsPage').then((m) => ({ default: m.SearchLeadsPage })))
const LeadsPage = lazy(() => import('@/pages/LeadsPage').then((m) => ({ default: m.LeadsPage })))
const OutreachQueuePage = lazy(() => import('@/pages/OutreachQueuePage').then((m) => ({ default: m.OutreachQueuePage })))
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })))
const SettingsPage = lazy(() => import('@/pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const AdminLayout = lazy(() => import('@/pages/admin/AdminLayout').then((m) => ({ default: m.AdminLayout })))
const AdminOverviewPage = lazy(() => import('@/pages/admin/AdminOverviewPage').then((m) => ({ default: m.AdminOverviewPage })))
const AdminUsersPage = lazy(() => import('@/pages/admin/AdminUsersPage').then((m) => ({ default: m.AdminUsersPage })))
const AdminBrandingPage = lazy(() => import('@/pages/admin/AdminBrandingPage').then((m) => ({ default: m.AdminBrandingPage })))
const AdminLeadPacksPage = lazy(() => import('@/pages/admin/AdminLeadPacksPage').then((m) => ({ default: m.AdminLeadPacksPage })))
const AdminScoringPage = lazy(() => import('@/pages/admin/AdminScoringPage').then((m) => ({ default: m.AdminScoringPage })))
const AdminPlansPage = lazy(() => import('@/pages/admin/AdminPlansPage').then((m) => ({ default: m.AdminPlansPage })))
const AdminSourcesPage = lazy(() => import('@/pages/admin/AdminSourcesPage').then((m) => ({ default: m.AdminSourcesPage })))
const AdminJobLogsPage = lazy(() => import('@/pages/admin/AdminJobLogsPage').then((m) => ({ default: m.AdminJobLogsPage })))
const AdminProfilePage = lazy(() => import('@/pages/admin/AdminProfilePage').then((m) => ({ default: m.AdminProfilePage })))
const AdminNewsletterPage = lazy(() => import('@/pages/admin/AdminNewsletterPage').then((m) => ({ default: m.AdminNewsletterPage })))
const AdminInboxPage = lazy(() => import('@/pages/admin/AdminInboxPage').then((m) => ({ default: m.AdminInboxPage })))
const AdminPaymentGatewayPage = lazy(() => import('@/pages/admin/AdminPaymentGatewayPage').then((m) => ({ default: m.AdminPaymentGatewayPage })))
const AdminEmailConfigPage = lazy(() => import('@/pages/admin/AdminEmailConfigPage').then((m) => ({ default: m.AdminEmailConfigPage })))
const AdminTransactionsPage = lazy(() => import('@/pages/admin/AdminTransactionsPage').then((m) => ({ default: m.AdminTransactionsPage })))

/** Landing pages (public, wrapped in LandingLayout) */
const LandingHome = lazy(() => import('@/landing/pages/HomePage').then((m) => ({ default: m.HomePage })))
const LandingContact = lazy(() => import('@/landing/pages/ContactPage').then((m) => ({ default: m.ContactPage })))
const LandingFeatures = lazy(() => import('@/landing/pages/FeaturesPage').then((m) => ({ default: m.FeaturesPage })))
const LandingPricing = lazy(() => import('@/landing/pages/PricingPage').then((m) => ({ default: m.PricingPage })))
const LandingBlog = lazy(() => import('@/landing/pages/BlogPage').then((m) => ({ default: m.BlogPage })))
const LandingBlogPost = lazy(() => import('@/landing/pages/BlogPostPage').then((m) => ({ default: m.BlogPostPage })))
const LandingTerms = lazy(() => import('@/landing/pages/TermsPage').then((m) => ({ default: m.TermsPage })))
const LandingPrivacy = lazy(() => import('@/landing/pages/PrivacyPage').then((m) => ({ default: m.PrivacyPage })))
const LandingFeatureDetail = lazy(() => import('@/landing/pages/FeatureDetailPage').then((m) => ({ default: m.FeatureDetailPage })))
const LandingCheckout = lazy(() => import('@/landing/pages/CheckoutPage').then((m) => ({ default: m.CheckoutPage })))
const LandingPaymentSuccess = lazy(() => import('@/landing/pages/PaymentSuccessPage').then((m) => ({ default: m.PaymentSuccessPage })))
const LandingPaymentFailed = lazy(() => import('@/landing/pages/PaymentFailedPage').then((m) => ({ default: m.PaymentFailedPage })))
const LandingNotFound = lazy(() => import('@/landing/pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })))
const UserTransactionsPage = lazy(() => import('@/pages/user/UserTransactionsPage').then((m) => ({ default: m.UserTransactionsPage })))
const UserProfilePage = lazy(() => import('@/pages/user/UserProfilePage').then((m) => ({ default: m.UserProfilePage })))
const UserUpgradePage = lazy(() => import('@/pages/user/UserUpgradePage').then((m) => ({ default: m.UserUpgradePage })))
const UserCheckoutPage = lazy(() => import('@/pages/user/UserCheckoutPage').then((m) => ({ default: m.UserCheckoutPage })))

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
        {/* Public landing pages */}
        <Route element={<LandingLayout />}>
          <Route path="/" element={<LandingHome />} />
          <Route path="/contact" element={<LandingContact />} />
          <Route path="/features" element={<LandingFeatures />} />
          <Route path="/pricing" element={<LandingPricing />} />
          <Route path="/subscribe/:planId" element={<LandingCheckout />} />
          <Route path="/payment/success" element={<LandingPaymentSuccess />} />
          <Route path="/payment/failed" element={<LandingPaymentFailed />} />
          <Route path="/features/:slug" element={<LandingFeatureDetail />} />
          <Route path="/blog" element={<LandingBlog />} />
          <Route path="/blog/:slug" element={<LandingBlogPost />} />
          <Route path="/terms" element={<LandingTerms />} />
          <Route path="/privacy" element={<LandingPrivacy />} />
          <Route path="/404" element={<LandingNotFound />} />
        </Route>

        {/* Auth pages */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin/login" element={<Navigate to="/login?next=%2Fadmin" replace />} />
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<Navigate to="/admin/overview" replace />} />
          <Route path="overview" element={<AdminOverviewPage />} />
          <Route path="users" element={<AdminUsersPage />} />
          <Route path="branding" element={<AdminBrandingPage />} />
          <Route path="lead-packs" element={<AdminLeadPacksPage />} />
          <Route path="scoring" element={<AdminScoringPage />} />
          <Route path="plans" element={<AdminPlansPage />} />
          <Route path="sources" element={<AdminSourcesPage />} />
          <Route path="job-logs" element={<AdminJobLogsPage />} />
          <Route path="profile" element={<AdminProfilePage />} />
          <Route path="newsletter" element={<AdminNewsletterPage />} />
          <Route path="inbox" element={<AdminInboxPage />} />
          <Route path="payment-gateway" element={<AdminPaymentGatewayPage />} />
          <Route path="email-config" element={<AdminEmailConfigPage />} />
          <Route path="transactions" element={<AdminTransactionsPage />} />
        </Route>

        {/* Auth-protected routes */}
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
          <Route path="/user/transactions" element={<UserTransactionsPage />} />
          <Route path="/user/upgrade" element={<UserUpgradePage />} />
          <Route path="/user/checkout/:planId" element={<UserCheckoutPage />} />
          <Route path="/user/profile" element={<UserProfilePage />} />
        </Route>

        {/* Catch-all: 404 */}
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </Suspense>
  )
}
