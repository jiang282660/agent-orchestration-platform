// 截取 8 张演示幻灯片为 PNG（供 ffmpeg 合成视频）
import { chromium } from 'playwright';
import fs from 'fs';

const htmlPath = 'C:/Users/Administrator/openharmony-ai-assistant/video/slides.html';
const outDir = 'C:/Users/Administrator/openharmony-ai-assistant/video/slides/';
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await page.goto('file:///' + htmlPath, { waitUntil: 'networkidle' });

for (let i = 0; i < 8; i++) {
  const el = page.locator('#s' + i);
  await el.screenshot({ path: outDir + `slide${i}.png` });
  console.log('已截图 slide' + i);
}
await browser.close();
console.log('完成');
