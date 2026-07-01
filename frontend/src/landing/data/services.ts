import type { LucideIcon } from 'lucide-react'
import { Palette, Code, AppWindow, Megaphone } from 'lucide-react'

export type ServiceItem = {
  icon: LucideIcon
  step: string
  title: string
  description: string
}

export const services: ServiceItem[] = [
  {
    icon: Palette,
    step: '01',
    title: 'UI/UX design',
    description: 'Clean interfaces your team will actually want to use every day.',
  },
  {
    icon: Code,
    step: '02',
    title: 'Web development',
    description: 'Fast, accessible sites built to convert visitors into customers.',
  },
  {
    icon: AppWindow,
    step: '03',
    title: 'App development',
    description: 'Mobile and web apps that solve real problems for real people.',
  },
  {
    icon: Megaphone,
    step: '04',
    title: 'Digital marketing',
    description: 'Campaigns that bring in leads, not just likes and page views.',
  },
]
