import { chromium } from 'playwright-core'
const b = await chromium.launch({ executablePath: '/usr/bin/google-chrome', headless: true })
const p = await b.newPage({ viewport: { width: 1280, height: 900 } })
await p.goto('http://localhost/productos/2', { waitUntil: 'networkidle' })
const t = await p.locator('main').innerText()
console.log(t.split('\n').filter((l) => /KG|UN\b/.test(l)).join(' | '))
await b.close()
