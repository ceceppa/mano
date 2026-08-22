import { defineConfig } from 'vitepress'

export default defineConfig({
  title: 'Mano',
  description: 'A fast planning loop for AI-assisted development. Plan in small phases and validate each assumption before it becomes code.',
  cleanUrls: true,
  lastUpdated: true,

  head: [
    ['link', { rel: 'icon', href: '/mano.svg', type: 'image/svg+xml' }],
    ['meta', { property: 'og:title', content: 'Mano — a fast planning loop for AI-assisted development' }],
    ['meta', { property: 'og:description', content: 'Plan in small phases and validate each assumption before it becomes code. You stay in control of the direction.' }],
    ['meta', { property: 'og:image', content: 'https://mano.ceceppa.me/mano.jpg' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }]
  ],

  themeConfig: {
    logo: '/mano.svg',

    nav: [
      { text: 'First phase', link: '/first-phase' },
      { text: 'Examples', link: '/examples' },
      { text: 'Commands', link: '/commands' },
      { text: 'Why Mano', link: '/why' }
    ],

    sidebar: [
      {
        text: 'Start here',
        items: [
          { text: 'Your first phase', link: '/first-phase' },
          { text: 'Commands', link: '/commands' }
        ]
      },
      {
        text: 'In practice',
        items: [
          { text: 'Examples', link: '/examples' },
          { text: 'Why Mano', link: '/why' }
        ]
      }
    ],

    socialLinks: [
      { icon: 'github', link: 'https://github.com/ceceppa/mano' },
      { icon: 'npm', link: 'https://www.npmjs.com/package/mano-plan' }
    ],

    editLink: {
      pattern: 'https://github.com/ceceppa/mano/edit/main/site/:path',
      text: 'Edit this page on GitHub'
    },

    footer: {
      message: 'Released under the MIT License.',
      copyright: 'Copyright © 2026 Alessandro Senese'
    },

    search: { provider: 'local' }
  }
})
