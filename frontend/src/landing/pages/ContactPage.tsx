import { useBrandingStore } from '@/store/brandingStore'
import { APP_NAME } from '@/lib/copy/appCopy'
import { SeoHead } from '@/landing/components/SeoHead'
import { ContactSection } from '@/landing/sections/ContactSection'

export function ContactPage() {
  const productName = useBrandingStore((s) => s.branding.product_name)

  return (
    <>
      <SeoHead
        title={`Contact ${productName || APP_NAME}`}
        description={`Get in touch with the ${productName} team. Sales inquiries, support requests, and partnership opportunities.`}
        keywords={['contact', 'support', 'sales inquiry', 'demo request']}
      />
      <ContactSection />
    </>
  )
}
