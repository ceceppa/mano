import { defineConfig } from 'vitepress'

const siteUrl = 'https://mano.ceceppa.me'

export default defineConfig({
  title: 'Mano',
  description: 'A fast planning loop for AI-assisted development. Plan in small phases and validate each assumption before it becomes code.',
  cleanUrls: true,
  lastUpdated: true,
  sitemap: { hostname: siteUrl },
  transformHead({ pageData }) {
    // VitePress creates the fallback page without running transformPageData.
    if (pageData.relativePath === '404.md') {
      return [['meta', { name: 'robots', content: 'noindex' }]]
    }
  },

  transformPageData(pageData) {
    const head = pageData.frontmatter.head ??= []
    if (pageData.relativePath === '404.md') {
      return
    }

    // Match the clean URLs emitted by VitePress and its sitemap.
    const path = pageData.relativePath
      .replace(/(^|\/)index\.md$/, '$1')
      .replace(/\.md$/, '')
    const url = new URL(path, `${siteUrl}/`).href
    const title = pageData.frontmatter.titleTemplate === false
      ? pageData.title
      : `${pageData.title} | Mano`

    head.push(
      ['link', { rel: 'canonical', href: url }],
      ['meta', { property: 'og:url', content: url }],
      ['meta', { property: 'og:title', content: title }],
      ['meta', { property: 'og:description', content: pageData.description }],
      ['meta', { name: 'twitter:title', content: title }],
      ['meta', { name: 'twitter:description', content: pageData.description }]
    )

    if (pageData.relativePath === 'index.md') {
      head.push(['script', { type: 'application/ld+json' }, JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        name: 'Mano',
        url: `${siteUrl}/`,
        description: pageData.description
      })])
    }
  },

  head: [
    ['link', { rel: 'icon', href: '/mano.svg', type: 'image/svg+xml' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'Mano' }],
    ['meta', { property: 'og:image', content: 'https://mano.ceceppa.me/mano.jpg' }],
    ['meta', { property: 'og:image:alt', content: 'Mano — a fast planning loop for AI-assisted development' }],
    ['meta', { name: 'twitter:image', content: 'https://mano.ceceppa.me/mano.jpg' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }]
  ],

  themeConfig: {
    logo: '/mano.svg',

    nav: [
      { text: 'Get started', link: '/getting-started' },
      {
        text: 'Features',
        items: [
          { text: 'All features', link: '/features/' },
          { text: 'Build mode', link: '/features/build' },
          { text: 'Auto mode', link: '/features/auto-mode' },
          { text: 'Import', link: '/features/import' },
          { text: 'Team owners', link: '/features/owners' },
          { text: 'Tracks & filters', link: '/features/tracks' },
          { text: 'Hooks', link: '/features/hooks' }
        ]
      },
      { text: 'Examples', link: '/examples' },
      { text: 'Commands', link: '/commands' },
      { text: 'Why Mano', link: '/why' }
    ],

    sidebar: [
      {
        text: 'Start here',
        items: [
          { text: 'Get started', link: '/getting-started' },
          { text: 'A real phase walkthrough', link: '/first-phase' },
          { text: 'Commands', link: '/commands' }
        ]
      },
      {
        text: 'Features',
        items: [
          { text: 'Overview', link: '/features/' },
          { text: 'Build mode', link: '/features/build' },
          { text: 'Auto mode', link: '/features/auto-mode' },
          { text: 'Import a document', link: '/features/import' },
          { text: 'Team owners', link: '/features/owners' },
          { text: 'Tracks & filters', link: '/features/tracks' },
          { text: 'Hooks', link: '/features/hooks' }
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
