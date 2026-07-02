# Payment & Subscription System — Implementation Guide

> **Status:** Implementation Complete ✅
> This document describes the live system architecture. All backend routes, database models, frontend pages, and payment flows are fully built and operational.

---

## 1. Database Models (Backend — FastAPI + SQLModel)

### 1.1 Plan (extend existing `admin_config.plan_channel_access` → standalone table)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | str | e.g. "Starter", "Growth", "Pro", "Free" |
| description | str | |
| monthly_price | float | 0 for free plan |
| currency | str | default "usd" / "inr" |
| features | JSON | list of feature strings |
| highlighted | bool | show "Popular" badge |
| is_free | bool | if true → no payment needed |
| lead_limit | int | max leads per period |
| channel_access | JSON | which channels enabled |
| stripe_price_id | str\|null | Stripe recurring price ID |
| razorpay_plan_id | str\|null | Razorpay plan ID |
| sort_order | int | display ordering |
| is_active | bool | soft delete |
| created_at | datetime | |
| updated_at | datetime | |

### 1.2 Subscription

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| plan_id | UUID | FK → plans |
| status | enum | `active`, `cancelled`, `expired`, `pending_payment`, `past_due` |
| start_date | datetime | |
| end_date | datetime\|null | |
| trial_end | datetime\|null | |
| stripe_sub_id | str\|null | Stripe subscription ID |
| razorpay_sub_id | str\|null | Razorpay subscription ID |
| gateway | enum | `stripe`, `razorpay`, `free` |
| auto_renew | bool | default true |
| created_at | datetime | |
| updated_at | datetime | |

### 1.3 Transaction

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| subscription_id | UUID | FK → subscriptions |
| plan_id | UUID | FK → plans |
| amount | float | |
| currency | str | |
| gateway | enum | `stripe`, `razorpay` |
| gateway_txn_id | str | payment intent / order ID |
| gateway_sub_id | str\|null | subscription ID from gateway |
| status | enum | `success`, `failed`, `pending`, `refunded` |
| payment_method | str\|null | "card", "upi", "netbanking", etc |
| failure_reason | str\|null | |
| invoice_url | str\|null | |
| created_at | datetime | |

### 1.4 PaymentGatewayConfig (single-row per gateway)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| gateway | enum | `stripe`, `razorpay` |
| is_active | bool | |
| publishable_key | str | encrypted (Stripe: pk, Razorpay: key_id) |
| secret_key | str | encrypted |
| webhook_secret | str | encrypted (signing secret) |
| created_at | datetime | |
| updated_at | datetime | |

### 1.5 EmailConfig (single-row)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| smtp_host | str | |
| smtp_port | int | 587 / 465 |
| smtp_user | str | |
| smtp_pass | str | encrypted |
| from_email | str | |
| from_name | str | |
| is_active | bool | |
| created_at | datetime | |
| updated_at | datetime | |

### 1.6 EmailTemplate

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| name | str | unique key e.g. `payment_confirmation` |
| subject | str | template string with `{{var}}` |
| body_html | text | JSX-like HTML template |
| variables | JSON | list of expected variable names |
| created_at | datetime | |
| updated_at | datetime | |

### 1.7 UserUsage (tracks per-period consumption)

| Field | Type | Notes |
|-------|------|-------|
| id | UUID | PK |
| user_id | UUID | FK → users |
| subscription_id | UUID | FK → subscriptions |
| leads_consumed | int | |
| period_start | datetime | start of billing/renewal period |
| period_end | datetime | end of billing/renewal period |
| updated_at | datetime | |

---

## 2. Backend API Endpoints

### 2.1 Public (no auth)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/public/plans` | list active plans (already exists — add price + stripe/razorpay IDs) |
| POST | `/public/subscriptions/create` | create checkout session → returns payment URL |
| GET | `/public/subscriptions/callback` | handle redirect after payment (verify & activate) |
| GET | `/public/subscriptions/status?user_id=` | check subscription status for login gate |

### 2.2 User (auth required)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/user/subscription` | current active subscription + usage |
| GET | `/user/transactions` | user's transaction history (paginated, filterable) |
| GET | `/user/usage` | leads consumed vs limit, period info |

### 2.3 Admin (admin auth required)

| Method | Path | Purpose |
|--------|------|---------|
| CRUD | `/admin/plans` | full plan CRUD with pricing fields |
| GET/PUT | `/admin/payment-gateway` | get/set gateway config (keys masked on GET) |
| GET/PUT | `/admin/email-config` | get/set SMTP config (password masked on GET) |
| GET | `/admin/email-config/test` | send test email |
| CRUD | `/admin/email-templates` | manage templates (preview + save) |
| GET | `/admin/transactions` | all transactions with filters (user, gateway, status, date) |
| GET | `/admin/transactions/:id` | single txn detail |
| GET | `/admin/subscriptions` | all subscriptions (filterable) |

### 2.4 Webhooks (no auth, signature verification)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/webhooks/stripe` | Stripe events: checkout.session.completed, invoice.paid, customer.subscription.deleted |
| POST | `/webhooks/razorpay` | Razorpay events: payment.captured, subscription.charged, subscription.cancelled |

---

## 3. Payment Flow (Detailed)

### 3.1 Subscription Creation

```
User clicks "Subscribe" on plan
  → POST /public/subscriptions/create { plan_id, gateway: "stripe"|"razorpay" }
  → Backend:
      1. Creates subscription row with status=pending_payment
      2. If Stripe: creates Stripe Checkout Session → returns session.url
      3. If Razorpay: creates Razorpay Order + Subscription → returns order_id, subscription_id, amount
      4. Saves gateway IDs to subscription + transaction rows
  → Frontend redirects user to gateway URL / opens modal
```

### 3.2 Stripe Flow

```
User completes payment on Stripe Checkout
  → Stripe redirects to /public/subscriptions/callback?session_id=xxx
  → Backend:
      1. Verifies session via Stripe API
      2. Updates transaction status → success
      3. Activates subscription (status=active, start_date=now)
      4. Sets end_date = now + 1 month (or from Stripe subscription)
      5. Creates UserUsage row with period_start=now, period_end=now+30d
      6. Sends confirmation email via SMTP
  → Frontend shows success page → redirect to dashboard
```

### 3.3 Razorpay Flow

```
User completes payment in Razorpay modal
  → Razorpay fires callback with payment_id + order_id + signature
  → Frontend sends POST /public/subscriptions/verify { payment_id, order_id, signature, subscription_id }
  → Backend:
      1. Verifies signature
      2. Updates transaction status → success
      3. Activates subscription
      4. Creates UserUsage
      5. Sends confirmation email
  → Frontend shows success → redirect to dashboard
```

### 3.4 Payment Failure

```
Gateway returns failure
  → Frontend shows popup: "Payment failed. Please try again."
  → Transaction saved with status=failed, failure_reason saved
  → Subscription stays pending_payment
  → User can retry or select different gateway

  Login gate check:
    On login → check user's latest subscription status
    If pending_payment with failed transactions → block login + show "Complete your payment" message with link to retry
    If no active subscription and not free plan → block login
    Free plan → always allow login (but dashboard may show upgrade prompt for limit)
```

---

## 4. Free Plan Logic

```
Registration flow:
  1. User registers → auto-assigned "Free" plan subscription
  2. Subscription: status=active, start_date=now, gateway=free
  3. UserUsage: leads_consumed=0, period_start=now, period_end=now+30d
  4. User gets full login access

When user uses leads:
  → Increment leads_consumed in UserUsage
  → If leads_consumed >= plan.lead_limit → lock lead features

Dashboard behaviour when limit reached:
  → Leads page: show upgrade prompt banner + disable lead actions
  → Show: "You've used all {limit} leads in this period. Upgrade to continue."
  → Show remaining days in current period
  → "Upgrade Now" button → pricing page

30-day renewal:
  → On login / dashboard load → check if period_end < now
  → If expired → reset leads_consumed=0, set new period_start/period_end
  → Access restored automatically
  → Optionally: send email notification "Your free plan has been renewed"

Edge case:
  If user upgrades to paid mid-period → free sub cancelled, paid sub starts
  If paid sub expires → downgrade to free if available, else block
```

---

## 5. Login Gate Logic (Frontend + Backend)

```
Frontend: LoginPage calls /public/subscriptions/status?user_id= (or as part of login response)

Login response includes:
  {
    token, user,
    subscription: {
      plan_id, plan_name, status,
      is_free, leads_consumed, lead_limit,
      period_end, has_pending_payment
    }
  }

Post-login checks:
  1. If subscription.status === "pending_payment" AND has failed transactions:
     → Block: show "Payment failed" popup + "Retry Payment" button → redirect to checkout
  2. If no active subscription AND not on free plan:
     → Block: "No active plan. Please subscribe to continue." → redirect to pricing
  3. Free plan expired but within 30-day window:
     → Allow login, show renewal notice
  4. Everything OK → proceed to dashboard
```

---

## 6. Frontend Pages & Components

### 6.1 New Pages

| Route | Page | Purpose |
|-------|------|---------|
| `/pricing` | LandingPricing | show plans with prices (enhance existing) |
| `/subscribe/:planId` | CheckoutPage | plan summary + payment gateway buttons |
| `/payment/success` | PaymentSuccess | confirmation + email notice |
| `/payment/failed` | PaymentFailed | error + retry |
| `/user/transactions` | UserTransactions | user's transaction history |
| `/admin/payment-gateway` | AdminPaymentGateway | configure Stripe/Razorpay keys |
| `/admin/email-config` | AdminEmailConfig | SMTP configuration |
| `/admin/email-templates` | AdminEmailTemplates | manage email templates |
| `/admin/transactions` | AdminTransactions | all txn with filters |

### 6.2 Updated Pages

| Page | Changes |
|------|---------|
| `LoginPage` | post-login subscription check + popup handling |
| `DashboardPage` | show plan info, usage bar, upgrade prompt |
| `LeadsPage` | check usage limit, show lock/upgrade if exceeded |
| `SearchLeadsPage` | same usage limit check |
| `AdminPlansPage` | add pricing fields (price, currency, stripe_price_id, razorpay_plan_id) |
| `AdminLayout` | add nav links (Payment Gateway, Email, Transactions) |

### 6.3 Components

| Component | Purpose |
|-----------|---------|
| `PaymentGatewaySelector` | Stripe button + Razorpay button side by side |
| `UsageBar` | visual progress bar (leads_consumed / lead_limit) |
| `PlanCard` | enhanced with price, "Subscribe" CTA |
| `TransactionTable` | reusable txn list (admin + user) |
| `TransactionFilters` | date range, gateway, status, user search |
| `UpgradeBanner` | shown in dashboard when limit reached |

---

## 7. Email System

### 7.1 SMTP Setup (Admin Page: `/admin/email-config`)

```
Fields:
  - SMTP Host (e.g. smtp.gmail.com)
  - SMTP Port (587 for TLS, 465 for SSL)
  - SMTP Username
  - SMTP Password
  - From Email
  - From Name
  - [Test Connection] button → sends test email to admin's email

Config saved in EmailConfig table (password encrypted)
```

### 7.2 Email Templates (JSX Files)

Templates stored in `src/email-templates/` as JSX files and also editable in admin UI:

```
src/email-templates/
  ├── PaymentConfirmation.tsx
  ├── PaymentFailed.tsx
  ├── FreePlanRenewed.tsx
  ├── SubscriptionExpiring.tsx
  └── WelcomeEmail.tsx
```

**PaymentConfirmation.jsx example:**
```tsx
import { APP_NAME } from '@/lib/copy/appCopy'

type Props = {
  userName: string
  planName: string
  amount: string
  currency: string
  transactionId: string
  invoiceUrl?: string
  loginUrl: string
}

export function PaymentConfirmation({ userName, planName, amount, currency, transactionId, invoiceUrl, loginUrl }: Props) {
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: 600, margin: '0 auto', padding: 32 }}>
      <div style={{ textAlign: 'center', marginBottom: 32 }}>
        <h1 style={{ color: '#d97706', fontSize: 24, fontWeight: 700 }}>{APP_NAME}</h1>
      </div>
      <h2 style={{ fontSize: 20, fontWeight: 600, marginBottom: 16 }}>Payment Confirmed</h2>
      <p style={{ color: '#52525b', lineHeight: 1.6 }}>Hi {userName},</p>
      <p style={{ color: '#52525b', lineHeight: 1.6 }}>
        Your payment of <strong>{currency} {amount}</strong> for the <strong>{planName}</strong> plan has been received successfully.
      </p>
      <div style={{ background: '#fafafa', borderRadius: 12, padding: 24, margin: '24px 0', border: '1px solid #e4e4e7' }}>
        <p style={{ margin: '4px 0', color: '#71717a', fontSize: 14 }}>Transaction ID: {transactionId}</p>
        {invoiceUrl && <p style={{ margin: '4px 0' }}><a href={invoiceUrl} style={{ color: '#d97706' }}>View Invoice</a></p>}
      </div>
      <a href={loginUrl} style={{ display: 'inline-block', background: '#d97706', color: '#fff', padding: '12px 24px', borderRadius: 8, textDecoration: 'none', fontWeight: 600, marginTop: 24 }}>
        Go to Dashboard
      </a>
      <p style={{ color: '#a1a1aa', fontSize: 12, marginTop: 32, borderTop: '1px solid #e4e4e7', paddingTop: 16 }}>
        &copy; {new Date().getFullYear()} {APP_NAME}. All rights reserved.
      </p>
    </div>
  )
}
```

### 7.3 Email Send Flow

```
Backend trigger email:
  1. Load EmailConfig (SMTP settings)
  2. If not active → log warning, skip
  3. Load EmailTemplate by name (e.g. "payment_confirmation")
  4. Render template with user data (variables)
  5. Send via SMTP (using `smtplib` / `aiosmtplib` + `jinja2` for server-side render)
  6. Log send status

JSX Template Server-Side Rendering:
  → Backend reads the .tsx file
  → Uses a JSX-to-HTML converter (or simply store as HTML string in DB with {{var}} placeholders)
  → Simpler approach: store HTML templates in DB directly (not .tsx), use string replacement for vars
  → But admin UI can preview/edit the HTML
```

**Recommended approach for simplicity:**
- Store email body as HTML string in `EmailTemplate.body_html` with `{{variable_name}}` placeholders
- Admin can edit HTML + subject in the admin UI
- Backend does simple `string.replace("{{var}}", value)` before sending
- Template preview in admin: rendered HTML in an iframe

---

## 8. Stripe Integration Details

### 8.1 Setup
```python
import stripe
stripe.api_key = config.secret_key
```

### 8.2 Create Checkout Session (when user subscribes)
```python
session = stripe.checkout.Session.create(
    mode="subscription",
    line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
    success_url=f"{FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
    cancel_url=f"{FRONTEND_URL}/payment/failed",
    client_reference_id=str(user_id),
    metadata={"plan_id": str(plan.id), "subscription_id": str(sub.id)},
)
```

### 8.3 Webhook Events to Listen For
```python
# stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
events = [
    "checkout.session.completed",    # initial payment success
    "invoice.paid",                   # recurring payment success
    "invoice.payment_failed",         # recurring payment failed
    "customer.subscription.deleted",  # cancellation
]
```

### 8.4 Create Product & Price in Stripe (Admin action)
Admin creates price manually in Stripe Dashboard, then enters `stripe_price_id` in admin plans page.

---

## 9. Razorpay Integration Details

### 9.1 Setup
```python
import razorpay
client = razorpay.Client(auth=(config.key_id, config.key_secret))
```

### 9.2 Create Order + Subscription (when user subscribes)
```python
# First create a plan in Razorpay
plan = client.plan.create({
    "period": "monthly",
    "interval": 1,
    "item": {
        "name": plan.name,
        "amount": int(plan.monthly_price * 100),  # in paise (INR) or cents
        "currency": plan.currency.upper(),
    }
})

# Create subscription
sub = client.subscription.create({
    "plan_id": plan["id"],
    "total_count": 12,
    "customer_notify": 1,
    "notes": {"plan_id": str(plan.id), "user_id": str(user_id)}
})

# Returns: order_id, subscription_id, amount (to init frontend checkout)
```

### 9.3 Frontend Checkout
```javascript
// Load Razorpay checkout script
const options = {
  key: razorpayKeyId,  // from PaymentGatewayConfig.publishable_key
  subscription_id: subscriptionId,
  name: "LeadPilot",
  description: plan.name,
  prefill: { email: user.email, name: user.name },
  callback_url: `${API_URL}/public/subscriptions/verify?subscription_id=${localSubId}`,
  handler: function (response) {
    // on success: POST to backend verify endpoint
  },
  modal: {
    ondismiss: function () {
      // user closed modal without paying
    }
  }
}
const rzp = new Razorpay(options)
rzp.open()
```

### 9.4 Webhook Events
```python
# Razorpay webhook signature verification
expected_signature = hmac_sha256(payload, webhook_secret)
events = [
    "payment.captured",
    "subscription.charged",
    "subscription.cancelled",
    "subscription.activated",
]
```

---

## 10. Admin Transaction Filters

| Filter | Type | Values |
|--------|------|--------|
| User | search | search by name/email |
| Gateway | dropdown | all / stripe / razorpay |
| Status | dropdown | all / success / failed / pending / refunded |
| Plan | dropdown | all / plan names |
| Date Range | date picker | from → to |
| Amount Range | number | min → max |

**Transaction table columns:**
- Date/Time
- User (name + email)
- Plan
- Amount + Currency
- Gateway
- Status (colored badge)
- Payment Method
- Invoice (link if available)
- Actions (view detail)

---

## 11. User Transaction Page

**Route:** `/user/transactions`

**Columns:**
- Date
- Plan
- Amount
- Status
- Invoice

**Filters:** date range, status

**Usage section:**
- Current plan
- Leads used / limit
- Period start / end
- [Upgrade] button

---

## 12. Admin UI Changes

### 12.1 Plans Page Enhancement
Add to each plan:
- `Monthly Price` (number input)
- `Currency` (dropdown: USD / INR)
- `Stripe Price ID` (text input)
- `Razorpay Plan ID` (text input)
- `Is Free` (toggle)
- `Lead Limit` (number input)
- `Sort Order` (number input)

### 12.2 New Admin Sidebar Links
```
Payment Gateway    → /admin/payment-gateway
Email Config       → /admin/email-config
Email Templates    → /admin/email-templates
Transactions       → /admin/transactions
```

---

### 2.5 Subscriptions Router (actual file structure)

All subscription-related routes are in a single file:
```
backend/app/routes/subscriptions.py
```

Additions beyond original plan:
- `GET /admin/email-templates` — list all templates
- `PUT /admin/email-templates` — create/update template
- `DELETE /admin/email-templates/{id}` — delete template
- `POST /admin/email-config/test` — send test email
- `POST /public/subscriptions/create` returns `{ url, order_id, subscription_id, transaction_id, gateway, amount, currency, publishable_key, is_free, status }`
- `POST /public/subscriptions/verify-razorpay` — Razorpay signature verification
- `GET /public/subscriptions/callback` — Stripe return URL handler

Subscriptions service lives at:
```
backend/services/subscription_service.py
```

Models are consolidated in:
```
database/orm/models.py
```

---

## 13. Implementation Order (Original Plan — for reference)

```
Phase 1 — Foundation (Backend)
  ├── Plan model + CRUD API (with pricing fields)
  ├── PaymentGatewayConfig model + API
  ├── EmailConfig model + API
  ├── EmailTemplate model + API
  ├── Subscription model
  ├── Transaction model
  └── UserUsage model

Phase 2 — Payment Integration
  ├── Stripe checkout session creation
  ├── Stripe webhook handling
  ├── Razorpay order + subscription creation
  ├── Razorpay verification + webhook
  └── Payment callback endpoints

Phase 3 — Frontend Checkout
  ├── Pricing page with prices + subscribe button
  ├── CheckoutPage (gateway selection)
  ├── PaymentSuccess / PaymentFailed pages
  ├── Post-login subscription check
  └── Upgrade banner + usage bar

Phase 4 — Admin UI
  ├── Plans page → add pricing fields
  ├── PaymentGateway page (key config)
  ├── EmailConfig page (SMTP)
  ├── EmailTemplates page (list + edit + preview)
  └── Transactions page (filters + details)

Phase 5 — User Features
  ├── Free plan auto-assign on registration
  ├── 30-day cycle + usage tracking
  ├── Lead locking when limit exceeded
  ├── User transactions page
  └── Login gate (block if no active plan)

Phase 6 — Email System
  ├── SMTP integration in backend
  ├── Email template rendering
  ├── Send payment confirmation
  ├── Send payment failed
  ├── Send subscription expiring
  └── Test email from admin
```

---

## 14. File Structure — New & Modified Files

### Backend (FastAPI)
```
backend/
  app/
    models/
      plan.py              # NEW
      subscription.py      # NEW
      transaction.py       # NEW
      payment_gateway.py   # NEW
      email_config.py      # NEW
      email_template.py    # NEW
      user_usage.py        # NEW
    api/
      public/
        plans.py           # MODIFY - add price fields
        subscriptions.py   # NEW
      user/
        subscription.py    # NEW
        transactions.py    # NEW
        usage.py           # NEW
      admin/
        plans.py           # MODIFY - add pricing CRUD
        payment_gateway.py # NEW
        email_config.py    # NEW
        email_templates.py # NEW
        transactions.py    # NEW
      webhooks/
        stripe.py          # NEW
        razorpay.py        # NEW
    services/
      stripe_service.py    # NEW
      razorpay_service.py  # NEW
      email_service.py     # NEW
      subscription_service.py # NEW
```

### Frontend (React)
```
src/
  lib/
    api/
      subscriptions.ts    # NEW
      transactions.ts     # NEW
      emailConfig.ts      # NEW
      paymentGateway.ts   # NEW
  pages/
    user/
      UserTransactionsPage.tsx  # NEW
    admin/
      AdminPaymentGatewayPage.tsx  # NEW
      AdminEmailConfigPage.tsx     # NEW
      AdminEmailTemplatesPage.tsx  # NEW
      AdminTransactionsPage.tsx    # NEW
      AdminPlansPage.tsx           # MODIFY
      AdminLayout.tsx              # MODIFY - add nav links
  landing/
    pages/
      CheckoutPage.tsx         # NEW
      PaymentSuccessPage.tsx   # NEW
      PaymentFailedPage.tsx    # NEW
    sections/
      PricingSection.tsx       # MODIFY - show prices + subscribe CTA
  components/
    UsageBar.tsx               # NEW
    PaymentGatewaySelector.tsx # NEW
    UpgradeBanner.tsx          # NEW
    TransactionTable.tsx       # NEW
    TransactionFilters.tsx     # NEW
    PlanCard.tsx               # NEW
  email-templates/
    PaymentConfirmation.tsx    # NEW
    PaymentFailed.tsx          # NEW
    FreePlanRenewed.tsx        # NEW
    SubscriptionExpiring.tsx   # NEW
    WelcomeEmail.tsx           # NEW
```

---

## 15. Key Assumptions & Decisions

1. **Recurring billing** via Stripe Subscriptions / Razorpay Subscriptions (not one-time)
2. **Email templates stored as HTML string in DB** (not .tsx → simpler server-side rendering with string replacement)
3. **Admin must create Stripe Price ID / Razorpay Plan ID manually** in their gateway dashboard (or we create via API)
4. **Encryption** for API keys and SMTP password using `cryptography.fernet` with an app-level secret
5. **Free plan** is a plan record with `is_free=True`, `monthly_price=0`
6. **Login gate** is a backend check that returns subscription status alongside auth token
7. **Webhook secret** stored per gateway for signature verification
