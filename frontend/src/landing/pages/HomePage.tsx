import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'

import { SeoHead } from '@/landing/components/SeoHead'
import { HeroSection } from '@/landing/sections/HeroSection'
import { FeaturesSection } from '@/landing/sections/FeaturesSection'
import { AboutSection } from '@/landing/sections/AboutSection'
import { ProcessSection } from '@/landing/sections/ProcessSection'
import { ServicesSection } from '@/landing/sections/ServicesSection'
import { PricingSection } from '@/landing/sections/PricingSection'
import { TestimonialsSection } from '@/landing/sections/TestimonialsSection'
import { BlogSection } from '@/landing/sections/BlogSection'
import { NewsletterSection } from '@/landing/sections/NewsletterSection'

export function HomePage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`${productName || APP_NAME} | AI Lead Growth System`}
        description={`${productName} is a lead management and sales CRM platform for prospecting, lead scoring, outreach tracking, and pipeline visibility. Trusted by 50,000+ sales professionals.`}
        keywords={['lead generation', 'sales CRM', 'lead scoring', 'outreach', 'pipeline management']}
        ogTitle={`${productName || APP_NAME} | AI-Powered Lead Intelligence`}
        ogDescription="Discover, score, and engage your ideal prospects with intelligent automation."
      />
      <HeroSection />
      <FeaturesSection />
      <AboutSection />
      <ProcessSection />
      <ServicesSection />
      <PricingSection />
      <TestimonialsSection />
      <BlogSection />
      <NewsletterSection />
    </>
  )
}
