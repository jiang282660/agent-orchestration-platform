// 用 Playwright(Chromium) 将技术方案 HTML 渲染为 PDF（脚本置于 frontend 以便解析 playwright 依赖）
import { chromium } from 'playwright';

const htmlPath = 'C:/Users/Administrator/openharmony-ai-assistant/docs/技术方案.html';
const pdfPath = 'C:/Users/Administrator/openharmony-ai-assistant/docs/技术方案.pdf';

const browser = await chromium.launch();
const page = await browser.newPage();
await page.goto('file:///' + htmlPath, { waitUntil: 'networkidle' });
await page.pdf({
  path: pdfPath,
  format: 'A4',
  printBackground: true,
  preferCSSPageSize: true,
  margin: { top: '18mm', bottom: '18mm', left: '16mm', right: '16mm' },
});
await browser.close();
console.log('已生成 PDF:', pdfPath);
