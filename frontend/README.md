# Frontend — LeadPilot

React 19 + TypeScript 6 + Vite 8 SPA.

## Tech Stack

| Area | Technology |
|------|-----------|
| UI Library | React 19, JSX |
| Build | Vite 8, TypeScript 6 |
| Styling | Tailwind CSS 3.4, dark mode (`class` strategy) |
| Routing | React Router DOM (declarative in `App.tsx`) |
| State | Zustand 5 stores (auth, admin, branding, theme, sidebar, user config) |
| API | Axios with interceptors (auth token injection, 401 handling) |
| Icons | Lucide React |
| Charts | Recharts 3 |
| Tables | @tanstack/react-table |
| Notifications | Sonner (toast) |

## Project Structure

```
src/
  ├── App.tsx              # All routes (landing + admin + app)
  ├── main.tsx             # React entry point
  ├── index.css            # Global styles + Tailwind directives + fonts
  │
  ├── layouts/
  │   ├── AppShell.tsx     # Authenticated app layout (sidebar + header + outlet)
  │
  ├── pages/
  │   ├── DashboardPage.tsx, LoginPage.tsx, etc.
  │   ├── admin/           # 16 admin panels
  │   └── user/            # Transactions, Profile, Upgrade, Checkout
  │
  ├── landing/             # Public marketing site (separate layout)
  │   ├── components/      # Header, Footer, LandingLayout, SeoHead, etc.
  │   ├── sections/        # Hero, Features, Pricing, Blog, Contact, etc.
  │   ├── pages/           # 17 landing pages
  │   └── data/            # Navigation, features, blog, testimonials, etc.
  │
  ├── components/
  │   ├── ui/              # Reusable: Modal, Badge, ConfirmDialog, ApiLoadError, etc.
  │   ├── layout/          # ThemeToggle, ThemeProvider, PlanSection, etc.
  │   ├── charts/          # Recharts-based chart components
  │   ├── scraper/         # Scraper status components
  │   └── ...              # UpgradeBanner, UsageBar, SubscriptionGate
  │
  ├── lib/
  │   ├── api/             # Axios-based API layer (30+ modules)
  │   ├── utils/           # Utility functions
  │   ├── config/          # App configuration
  │   └── copy/            # Text copy / meta descriptions
  │
  ├── store/               # Zustand stores
  └── types/               # TypeScript type definitions
```

## Key Conventions

- **API calls** go through `src/lib/api/` — each module exports typed async functions
- **Axios instance** in `client.ts` handles auth token injection + 401 redirect
- **State** managed via Zustand stores in `src/store/`
- **Admin panel** has its own auth (separate JWT from user auth)
- **Role gating** with `RequireRole` component in routes

## Development

```bash
npm run dev      # Start Vite dev server (port 5173)
npm run build    # TypeScript check + Vite build
npm run lint     # ESLint check
npm run test     # Vitest
npm run preview  # Preview production build
```
