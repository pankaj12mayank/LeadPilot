import { useEffect } from 'react'

export function SeoHead({
  title,
  description,
  keywords,
  ogTitle,
  ogDescription,
  ogImage,
}: {
  title: string
  description?: string
  keywords?: string[]
  ogTitle?: string
  ogDescription?: string
  ogImage?: string
}) {
  useEffect(() => {
    document.title = title
    const setMeta = (name: string, content: string, prop = false) => {
      const selector = prop ? `meta[property="${name}"]` : `meta[name="${name}"]`
      let el = document.querySelector(selector) as HTMLMetaElement | null
      if (!el) {
        el = document.createElement('meta')
        if (prop) el.setAttribute('property', name)
        else el.setAttribute('name', name)
        document.head.appendChild(el)
      }
      el.setAttribute('content', content)
    }
    if (description) setMeta('description', description)
    if (keywords?.length) setMeta('keywords', keywords.join(', '))
    if (ogTitle) setMeta('og:title', ogTitle, true)
    if (ogDescription) setMeta('og:description', ogDescription, true)
    if (ogImage) setMeta('og:image', ogImage, true)
  }, [title, description, keywords, ogTitle, ogDescription, ogImage])

  return null
}
