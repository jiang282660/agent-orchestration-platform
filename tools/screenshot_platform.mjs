// 截图 Agent 平台前端 4 个页面（供方案书/PPT 使用）
import { chromium } from 'playwright';
import fs from 'fs';

const outDir = 'C:/Users/Administrator/agent-orchestration-platform/docs/assets/';
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
await page.waitForTimeout(1500);

async function shot(name) {
  await page.waitForTimeout(800);
  await page.screenshot({ path: outDir + name + '.png' });
  console.log('已截图:', name);
}

// 1 总览（默认页）
await shot('01-overview');

// 2 知识库
await page.locator('.el-menu-item', { hasText: '知识库' }).click();
await shot('02-knowledge-base');

// 3 任务运行
await page.locator('.el-menu-item', { hasText: '任务运行' }).click();
await shot('03-run-board');

// 4 基准评估
await page.locator('.el-menu-item', { hasText: '基准评估' }).click();
await shot('04-benchmark');

await browser.close();
console.log('完成');
