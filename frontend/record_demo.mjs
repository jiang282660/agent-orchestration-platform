import { chromium } from 'playwright'
import { mkdirSync } from 'fs'

const APP = 'http://127.0.0.1:5173'
mkdirSync('videos', { recursive: true })

const browser = await chromium.launch()
const context = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  recordVideo: { dir: 'videos', size: { width: 1440, height: 900 } },
})
const page = await context.newPage()
const wait = (ms) => page.waitForTimeout(ms)

// 1. 总览页
await page.goto(APP, { waitUntil: 'networkidle' })
await wait(3000)

// 2. 知识库页
await page.click('text=知识库')
await wait(3000)

// 3. 任务运行页
await page.click('text=任务运行')
await wait(1500)
// 选演示知识库
await page.locator('.el-select').first().click()
await wait(800)
await page.locator('.el-select-dropdown__item').filter({ hasText: '演示知识库' }).first().click()
await wait(800)
// 开始运行（实时看板 + SSE 流）
await page.click('button:has-text("开始运行")')
await page.waitForSelector('text=全部完成', { timeout: 300000 })
await wait(5000)

// 4. 基准评估页
await page.click('text=基准评估')
await wait(3000)

// 回到总览，收尾
await page.click('text=总览')
await wait(2000)

await context.close()
await browser.close()
console.log('✅ 录制完成，视频输出到 videos/ 目录')
