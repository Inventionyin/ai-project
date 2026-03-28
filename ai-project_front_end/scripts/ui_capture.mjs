import { chromium } from '@playwright/test'
import fs from 'node:fs/promises'
import path from 'node:path'

function parseArgs(argv) {
  const args = { headed: false }
  for (let i = 0; i < argv.length; i += 1) {
    const key = argv[i]
    const next = argv[i + 1]
    if (key === '--url') args.url = String(next || '')
    if (key === '--page-id') args.pageId = String(next || '')
    if (key === '--out') args.out = String(next || '')
    if (key === '--headed') args.headed = true
    if (key === '--url' || key === '--page-id' || key === '--out') i += 1
  }
  return args
}

function buildSelector(el) {
  const id = String(el.id || '').trim()
  if (id) return `#${id}`
  const testId = String(el.dataTestId || '').trim()
  if (testId) return `[data-testid="${testId}"]`
  const tag = String(el.tag || '').trim().toLowerCase()
  const name = String(el.name || '').trim()
  if (tag && name) return `${tag}[name="${name}"]`
  return tag || '*'
}

async function main() {
  const args = parseArgs(process.argv.slice(2))
  if (!args.url || !args.pageId || !args.out) {
    throw new Error('missing_required_args')
  }
  const outDir = path.resolve(args.out)
  await fs.mkdir(outDir, { recursive: true })
  const browser = await chromium.launch({ headless: !args.headed })
  const context = await browser.newContext({ viewport: { width: 1440, height: 960 } })
  const page = await context.newPage()
  await page.goto(args.url, { waitUntil: 'networkidle', timeout: 60000 })
  const elements = await page.$$eval(
    'a,button,input,textarea,select,[role="button"],[data-testid]',
    nodes =>
      nodes.map((node, idx) => {
        const el = node
        const tag = (el.tagName || '').toLowerCase()
        const text = (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 80)
        const role = el.getAttribute('role') || ''
        const dataTestId = el.getAttribute('data-testid') || ''
        const id = el.getAttribute('id') || ''
        const name = el.getAttribute('name') || ''
        const placeholder = el.getAttribute('placeholder') || ''
        const ariaLabel = el.getAttribute('aria-label') || ''
        return {
          index: idx + 1,
          tag,
          text,
          role,
          dataTestId,
          id,
          name,
          placeholder,
          ariaLabel
        }
      })
  )
  const enriched = elements.map(item => ({
    ...item,
    selector: buildSelector(item)
  }))
  const screenshotPath = path.join(outDir, 'page.png')
  const elementsPath = path.join(outDir, 'elements.json')
  await page.screenshot({ path: screenshotPath, fullPage: true })
  await fs.writeFile(elementsPath, JSON.stringify(enriched, null, 2), 'utf-8')
  await browser.close()
  process.stdout.write(
    JSON.stringify(
      {
        ok: true,
        pageId: args.pageId,
        count: enriched.length,
        screenshotPath,
        elementsPath
      },
      null,
      2
    )
  )
}

main().catch(err => {
  process.stderr.write(String(err?.message || err))
  process.exit(1)
})
