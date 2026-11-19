// 截图技术方案文档中的 SVG 架构图为 PNG（供 PPT 使用）
import { chromium } from 'playwright';

const htmlPath = 'C:/Users/Administrator/openharmony-ai-assistant/docs/技术方案.html';
const outDir = 'C:/Users/Administrator/openharmony-ai-assistant/ppt/assets/';
const names = ['arch-cloud-device', 'arch-native-layers', 'route', 'agent-flow'];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
await page.goto('file:///' + htmlPath, { waitUntil: 'networkidle' });

const svgs = page.locator('svg');
const count = await svgs.count();
for (let i = 0; i < Math.min(count, names.length); i++) {
  await svgs.nth(i).screenshot({ path: outDir + names[i] + '.png' });
  console.log('已截图:', names[i]);
}
await browser.close();
console.log('完成，共', count, '个 SVG');
