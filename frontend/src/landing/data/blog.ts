export type BlogPost = {
  id: string
  title: string
  slug: string
  excerpt: string
  category: string
  date: string
  author: string
  image: string
  readTime: string
  body?: string
}

export const blogPosts: BlogPost[] = [
  {
    id: '1',
    title: 'Personal debt or company debt: we explore your options',
    slug: 'personal-vs-company-debt-options',
    excerpt:
      'Understanding the difference between personal and business debt can save you thousands. We break down the scenarios where each makes sense.',
    category: 'Finance',
    date: '20 August, 2025',
    author: 'John Doe',
    image: '',
    readTime: '4 min read',
    body: 'When you are running a business, the line between personal and company expenses can blur. But when it comes to debt, keeping them separate matters more than most people realise. Personal debt like credit cards or personal loans comes with higher interest rates and fewer tax benefits. Company debt, on the other hand, can be structured in ways that protect your personal assets and often comes with better terms. The right choice depends on what you are financing. Equipment, inventory, and expansion are usually better suited to business debt. Personal expenses or bridge funding might call for personal credit. We have put together a comparison table to help you decide which route fits your situation.',
  },
  {
    id: '2',
    title: 'When is the right time to sell your company?',
    slug: 'right-time-to-sell-company',
    excerpt:
      'Timing a business exit is as much about market conditions as it is about personal readiness. Here is what to consider before you list.',
    category: 'Business',
    date: '21 August, 2025',
    author: 'John Doe',
    image: '',
    readTime: '5 min read',
    body: 'Selling a business is rarely just about the money. The best exits happen when three things line up: the market is hungry for what you do, your financials tell a clean story, and you personally feel ready to move on. Many owners wait too long, hoping for a higher multiple that never comes. Others sell too early, leaving value on the table. In this post, we walk through the signals that indicate it might be time to start the conversation with buyers. Revenue consistency, recurring revenue percentage, and team independence are three big ones to watch.',
  },
  {
    id: '3',
    title: 'Change emails and long video calls for asynchronous video',
    slug: 'async-video-over-email',
    excerpt:
      'Long email threads and back-to-back meetings eat your week. Asynchronous video is changing how teams communicate without losing context.',
    category: 'Productivity',
    date: '16 December, 2025',
    author: 'John Doe',
    image: '',
    readTime: '3 min read',
    body: 'How many hours do you spend in meetings that could have been a short video? Asynchronous video tools let you record your screen, explain your point, and send it in a link. The recipient watches when they have time, replies the same way, and nobody has to coordinate calendars. Teams that adopt async video report fewer interruptions, shorter decision cycles, and better documentation (because the video stays accessible). It is not a replacement for every conversation, but for status updates, feature demos, and feedback, it beats a ten-email thread every time.',
  },
  {
    id: '4',
    title: 'Google Analytics checklist: is your website data accurate?',
    slug: 'google-analytics-accuracy-checklist',
    excerpt:
      'Most websites have tracking issues they do not know about. Run through this checklist to make sure your analytics data is reliable.',
    category: 'Analytics',
    date: '24 August, 2025',
    author: 'John Doe',
    image: '',
    readTime: '6 min read',
    body: 'If you are making decisions based on Google Analytics data, you need to be confident it is correct. Unfortunately, common issues like missing tags, bot traffic, and cross-domain tracking problems mean many people are looking at numbers that do not add up. We have put together a practical checklist you can run through in under an hour. It covers tag verification, spam filtering, goal configuration, and data retention settings. Even if you think your setup is clean, you will probably find at least one thing to fix.',
  },
  {
    id: '5',
    title: 'Why most small businesses fail in the first year',
    slug: 'why-small-businesses-fail-first-year',
    excerpt:
      'The stats are sobering, but the reasons are predictable. Here is what new business owners overlook and how to avoid the same pitfalls.',
    category: 'Business',
    date: '23 August, 2025',
    author: 'John Doe',
    image: '',
    readTime: '7 min read',
    body: 'About one in five new businesses does not make it past the first year. The reasons are usually the same: running out of cash, poor market fit, or trying to do everything alone. The good news is that all of these are avoidable with the right planning. In this article, we look at the real stories behind the failure statistics. Cash flow mismanagement is the biggest culprit, followed by pricing that does not cover actual costs. We also cover why a strong network of advisors and peers makes a bigger difference than most founders realise.',
  },
]
