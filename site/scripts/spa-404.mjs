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
import { copyFileSync, mkdirSync } from 'node:fs'
import { join } from 'node:path'

const ROUTES = ['calculator', 'badge', 'analyzer']

const source = join('dist', 'index.html')

copyFileSync(source, join('dist', '404.html'))
console.log('dist/404.html created (SPA catch-all)')

for (const route of ROUTES) {
  const dir = join('dist', route)
  mkdirSync(dir, { recursive: true })
  copyFileSync(source, join(dir, 'index.html'))
  console.log(`dist/${route}/index.html created (returns 200)`)
}
