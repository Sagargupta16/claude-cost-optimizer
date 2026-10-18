// GitHub Pages SPA handling for deep links like /calculator.
//
// 404.html alone is not enough. Pages serves it for an unknown path and the
// router then renders the right view, so a human sees the correct page -- but
// the HTTP status is still 404. That means search engines skip the three tool
// pages the README promotes, and every link checker reports them as broken.
//
// Writing a real index.html at each route makes those URLs return 200. 404.html
// stays as the catch-all for anything not listed here.
//
// ROUTES must match the <Route path> list in src/App.tsx. Add a page there and
// add it here in the same commit, or its URL will soft-404.
//
// Each route copy also gets its own canonical and og:url. A straight copy kept
// the home page's canonical, which tells search engines every tool page is a
// duplicate of the home page and undoes the point of the 200.
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'

const ROUTES = ['calculator', 'badge', 'analyzer']
const SITE_URL = 'https://sagargupta.online/claude-cost-optimizer/'

const source = join('dist', 'index.html')
const html = readFileSync(source, 'utf8')

if (!html.includes(`"${SITE_URL}"`)) {
  console.error(`index.html has no canonical or og:url equal to ${SITE_URL}`)
  process.exit(1)
}

copyFileSync(source, join('dist', '404.html'))
console.log('dist/404.html created (SPA catch-all)')

for (const route of ROUTES) {
  const dir = join('dist', route)
  mkdirSync(dir, { recursive: true })
  const routeHtml = html.replaceAll(`"${SITE_URL}"`, `"${SITE_URL}${route}/"`)
  writeFileSync(join(dir, 'index.html'), routeHtml)
  console.log(`dist/${route}/index.html created (returns 200, canonical ${SITE_URL}${route}/)`)
}
