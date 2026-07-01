# Landing Page - Complete Build Plan

## Folder Structure
```
frontend/src/landing/
  ├── components/
  │   ├── Header.tsx          # Top bar + nav (logo, favicon, links)
  │   ├── Footer.tsx          # Footer columns + copyright (logo, favicon)
  │   ├── SeoHead.tsx         # Dynamic SEO meta tags per page
  │   ├── ThemeToggle.tsx     # Dark/light toggle (reuse)
  │   └── ScrollToTop.tsx     # Scroll restoration on page change
  │
  ├── sections/
  │   ├── HeroSection.tsx      # Hero with bg, heading, CTA, stats
  │   ├── FeaturesSection.tsx  # 3-column feature cards
  │   ├── AboutSection.tsx     # About preview / intro text
  │   ├── ProcessSection.tsx   # Numbered steps (01 02 03 04)
  │   ├── ServicesSection.tsx  # Services/What We Do
  │   ├── PricingSection.tsx   # Pricing plans (Basic, Normal, Pro)
  │   ├── PortfolioSection.tsx # Portfolio grid with filters
  │   ├── TestimonialsSection.tsx # Client testimonials carousel
  │   ├── BlogSection.tsx     # Latest blog posts
  │   ├── NewsletterSection.tsx # Email subscribe form
  │   └── ContactSection.tsx  # Contact form + info
  │
  ├── pages/
  │   ├── HomePage.tsx        # Main landing (all sections)
  │   ├── AboutPage.tsx       # About us page
  │   ├── ContactPage.tsx     # Contact page (map + form)
  │   ├── FeaturesPage.tsx    # Features detail page
  │   ├── PricingPage.tsx     # Pricing detail page
  │   ├── PortfolioPage.tsx   # Portfolio grid page
  │   ├── BlogPage.tsx        # Blog listing page
  │   ├── BlogPostPage.tsx    # Single blog post
  │   ├── LoginPage.tsx       # Login page
  │   ├── RegisterPage.tsx    # Registration page
  │   ├── TermsPage.tsx       # Terms & conditions
  │   ├── PrivacyPage.tsx     # Privacy policy
  │   └── NotFoundPage.tsx    # 404 page
  │
  ├── data/
  │   ├── navigation.ts      # Nav links (easy to edit)
  │   ├── features.ts        # Feature cards content
  │   ├── services.ts        # Services content
  │   ├── pricing.ts         # Pricing plans content
  │   ├── portfolio.ts       # Portfolio items
  │   ├── testimonials.ts    # Testimonials content
  │   ├── team.ts            # Team members
  │   ├── blog.ts            # Blog posts content
  │   ├── footer.ts          # Footer links & info
  │   └── contact.ts         # Contact info, social links
  │
  └── assets/
      └── images/            # Hero, about, etc images
```

## Design Reference (U-Corporate Theme)

| Section | Reference Feature |
|---------|------------------|
| **Top Bar** | Email, phone, hours, Sign in/Register link |
| **Nav** | Logo left, nav links center/right, CTA button |
| **Hero** | Big heading, subtext, CTA, background image/gradient, stats counter |
| **Features** | 3 cards side-by-side with icon, title, desc, "Read More" |
| **About/Services** | Left text, right image, "View More" CTA |
| **Process** | Numbered steps (01 02 03 04) in grid |
| **What We Do** | Image background, overlay text, CTA |
| **Pricing** | 3 plans (Basic $29, Normal $49, Pro $69) with feature lists |
| **Portfolio** | Image grid with hover overlay, category filter |
| **Testimonials** | Quote cards, avatar, name, role, carousel |
| **Blog** | 2-column popular + recent articles |
| **Newsletter** | Subscribe input + button, background section |
| **Footer** | 4-column: About, Customer links, Company links, Location map |
| **Bottom Bar** | Copyright left, social icons right |

## Key Requirements
1. **Every page** must show logo + favicon (from branding store)
2. **SEO**: Each page has unique title, description, keywords, OG tags
3. **Geo-friendly**: Content adapts (location in title/description)
4. **Dark/Light mode**: Existing theme system reused
5. **Human tone**: Content written naturally, no AI-generated feel
6. **Logo + Favicon**: From `useBrandingStore` - consistent across all pages
7. **Data files**: All content in `data/` folder - edit anytime without touching JSX

## Implementation Order
1. `data/` files (navigation, features, services, pricing, portfolio, testimonials, blog, footer, contact)
2. `components/` (Header, Footer, SeoHead)
3. `sections/` (all section components)
4. `pages/` (HomePage assembled from sections, then About, Contact, etc)
5. Routing in App.tsx
6. Replace old LandingPage.tsx

Want me to proceed with building this?
