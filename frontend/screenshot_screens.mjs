// 截取 5 个界面原型图为 PNG（供 PPT 使用）
import { chromium } from 'playwright';

const htmlPath = 'C:/Users/Administrator/openharmony-ai-assistant/mockup/screens.html';
const outDir = 'C:/Users/Administrator/openharmony-ai-assistant/ppt/assets/';
const ids = ['screen-chat', 'screen-board', 'screen-devices', 'screen-kb', 'screen-privacy'];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 420, height: 900 } });
await page.goto('file:///' + htmlPath, { waitUntil: 'networkidle' });

for (const id of ids) {
  const el = page.locator('#' + id);
  await el.screenshot({ path: outDir + id + '.png' });
  console.log('已截图:', id);
}
await browser.close();
console.log('完成');
