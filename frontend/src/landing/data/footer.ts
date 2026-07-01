export type FooterCol = {
  heading: string
  links: { label: string; href: string }[]
}

export const footerColumns: FooterCol[] = [
  {
    heading: 'Product',
    links: [
      { label: 'Pricing', href: '/pricing' },
      { label: 'Features', href: '/features' },
      { label: 'Documentation', href: '/features' },
      { label: 'FAQs', href: '/about' },
    ],
  },
  {
    heading: 'Company',
    links: [
      { label: 'About us', href: '/about' },
      { label: 'Blog', href: '/blog' },
      { label: 'Contact us', href: '/contact' },
      { label: 'Privacy policy', href: '/privacy' },
      { label: 'Terms of use', href: '/terms' },
    ],
  },
]

export const footerDescription =
  'This site has been set up for demonstration purposes and more.'
