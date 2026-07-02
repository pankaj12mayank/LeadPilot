# Landing Page — Current State

> **Status:** Built ✅
> The landing page is fully implemented with all sections, pages, components, and data files.

## Folder Structure (Actual)

```
frontend/src/landing/
  ├── components/
  │   ├── Header.tsx              # Top bar + nav with logo/favicon from branding store
  │   ├── Footer.tsx              # Footer columns + copyright with branding
  │   ├── LandingLayout.tsx       # Shared layout: Header + Outlet + Footer
  │   ├── SeoHead.tsx             # Dynamic SEO meta tags per page
  │   ├── ScrollToTop.tsx         # Scroll restoration on page change
  │   └── ThemeToggle.tsx         # Dark/light toggle
  │
  ├── sections/
  │   ├── HeroSection.tsx         # Hero with heading, subtext, CTA buttons, stats
  │   ├── FeaturesSection.tsx     # 3-column feature cards with icons
  │   ├── AboutSection.tsx        # About preview / stats section
  │   ├── ProcessSection.tsx      # Numbered steps (01 02 03 04) in grid
  │   ├── ServicesSection.tsx     # Services/What We Do cards
  │   ├── PricingSection.tsx      # Dynamic pricing cards (fetched from API) with "Subscribe" CTA
  │   ├── TestimonialsSection.tsx # Client testimonials grid
  │   ├── BlogSection.tsx         # Latest blog posts cards
  │   ├── NewsletterSection.tsx   # Email subscribe form with API integration
  │   └── ContactSection.tsx      # Contact form with API integration
  │
  ├── pages/
  │   ├── HomePage.tsx            # Assembles all sections
  │   ├── FeaturesPage.tsx        # Features list + detail links
  │   ├── FeatureDetailPage.tsx   # Single feature detail
  │   ├── PricingPage.tsx         # PricingSection + comparison table + FAQ
  │   ├── CheckoutPage.tsx        # Plan summary + Stripe/Razorpay payment
  │   ├── PaymentSuccessPage.tsx  # Post-payment confirmation
  │   ├── PaymentFailedPage.tsx   # Payment error with retry
  │   ├── BlogPage.tsx            # Blog listing
  │   ├── BlogPostPage.tsx        # Single blog post with content
  │   ├── ContactPage.tsx         # Contact form page
  │   ├── AboutPage.tsx           # About us page
  │   ├── TermsPage.tsx           # Terms & conditions
  │   ├── PrivacyPage.tsx         # Privacy policy
  │   ├── NotFoundPage.tsx        # 404 page
  │   ├── LoginPage.tsx           # Login page
  │   └── RegisterPage.tsx        # Registration page
  │
  ├── data/
  │   ├── navigation.ts           # Nav links config
  │   ├── features.ts             # Feature cards content
  │   ├── services.ts             # Services content
  │   ├── portfolio.ts            # Portfolio items
  │   ├── testimonials.ts         # Testimonials content
  │   ├── blog.ts                 # Blog posts content
  │   └── contact.ts              # Contact info, social links
  │
  └── assets/
      └── images/                 # Static images
```

## Key Features
- **Dynamic pricing** — Plans fetched live from `/api/public/plans` endpoint, not hardcoded
- **Payment integration** — `/subscribe/:planId` checkout with Stripe + Razorpay
- **Branding-aware** — Logo, favicon, product name from `useBrandingStore`
- **SEO** — Every page has unique title, meta description, keywords via `SeoHead` component
- **Dark/Light mode** — Reuses project-wide theme system
- **Responsive** — Full mobile + desktop support

## Note
For logged-in users, upgrade flow goes through `/user/upgrade` → `/user/checkout/:planId` (inside app shell).
The landing `/pricing` and `/subscribe/:planId` are for unauthenticated visitors.
