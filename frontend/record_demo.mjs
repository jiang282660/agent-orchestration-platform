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

// 1. 总览页：六角色团队 + DAG 可视化（停留 12s）
await page.goto(APP, { waitUntil: 'networkidle' })
await wait(12000)

// 2. 知识库页：文档入库与混合检索（停留 12s）
await page.click('text=知识库')
await wait(12000)

// 3. 任务运行页：提交任务，SSE 实时看板展示 Agent 编排 + 调度 + Self-Loop
await page.click('text=任务运行')
await wait(2000)
await page.locator('.el-select').first().click()
await wait(1000)
await page.locator('.el-select-dropdown__item').filter({ hasText: '演示知识库' }).first().click()
await wait(1000)
await page.click('button:has-text("开始运行")')
await page.waitForSelector('text=全部完成', { timeout: 300000 })
await wait(10000)

// 4. 缓慢滚动查看最终报告 + 引用溯源（约 20s）
for (let i = 0; i < 10; i++) {
  await page.mouse.wheel(0, 500)
  await wait(1000)
}
await wait(5000)

// 5. 基准评估页：golden set 覆盖度评估（停留 12s）
await page.click('text=基准评估')
await wait(12000)

// 6. 回到总览，收尾（停留 8s）
await page.click('text=总览')
await wait(8000)

// 关键：先取 video 对象 → 关 context（finalize 视频）→ saveAs → 再关 browser
const video = page.video()
await context.close()
if (video) {
  await video.saveAs('videos/demo.webm')
}
await browser.close()
console.log('✅ 录制完成，输出到 videos/demo.webm')
