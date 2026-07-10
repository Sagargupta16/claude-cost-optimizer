// GitHub Pages SPA fallback: serve index.html for deep links like /calculator.
import { copyFileSync } from 'node:fs'
copyFileSync('dist/index.html', 'dist/404.html')
console.log('dist/404.html created (SPA fallback)')
