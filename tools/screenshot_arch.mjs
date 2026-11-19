// 截图方案书中的架构 SVG 为 PNG（供 PPT 使用）
import { chromium } from 'playwright';

const htmlPath = 'C:/Users/Administrator/agent-orchestration-platform/docs/方案书.html';
const outDir = 'C:/Users/Administrator/agent-orchestration-platform/docs/assets/';

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
await page.goto('file:///' + htmlPath, { waitUntil: 'networkidle' });

const svg = page.locator('svg').first();
await svg.screenshot({ path: outDir + '00-architecture.png' });
console.log('已截图 00-architecture');
await browser.close();
