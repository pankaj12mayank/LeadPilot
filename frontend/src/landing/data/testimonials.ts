export type Testimonial = {
  name: string
  role: string
  quote: string
  avatar: string
}

export const testimonials: Testimonial[] = [
  {
    name: 'Justin Watson',
    role: 'Operations Manager',
    quote:
      'We tried three other tools before this one. LeadPilot is the only platform that actually fits how our team works. Setup was straightforward, and we had our first campaign running inside an hour.',
    avatar: '',
  },
  {
    name: 'Lori Cruz',
    role: 'Sales Director',
    quote:
      'The scoring model alone saves us hours every week. Instead of chasing cold leads, we focus on the people who are actually ready to talk. Our conversion rate went up 40% in two months.',
    avatar: '',
  },
  {
    name: 'David James',
    role: 'Logistics Consultant',
    quote:
      'I am not a tech person, but I had everything set up in an afternoon. Whenever I had a question, support answered within a couple of hours. That kind of service matters when you are running a business.',
    avatar: '',
  },
]
