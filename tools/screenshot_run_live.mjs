// 触发一次真实运行，截取「任务执行中」看板（展示 Agent 编排时间线 + Self-Loop 曲线）
import { chromium } from 'playwright';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
await page.waitForTimeout(1200);

// 切到「任务运行」页
await page.locator('.el-menu-item', { hasText: '任务运行' }).click();
await page.waitForTimeout(1000);

// 点击「开始运行」（默认主题 + 自动选中第一个知识库）
await page.getByRole('button', { name: '开始运行' }).click();
console.log('已触发运行，等待执行过程…');

// 等待时间线出现事件（最多 90s）
let ok = false;
for (let i = 0; i < 90; i++) {
  await page.waitForTimeout(1000);
  const n = await page.locator('.el-timeline-item').count();
  if (n >= 3) { ok = true; break; }
}
await page.waitForTimeout(3000); // 再等几秒让更多事件进来
await page.screenshot({ path: 'C:/Users/Administrator/agent-orchestration-platform/docs/assets/03b-run-live.png' });
console.log('已截图 03b-run-live（时间线条数达标:', ok, '）');
await browser.close();
