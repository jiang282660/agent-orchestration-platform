import { chromium } from 'playwright';

const htmlPath = 'C:/Users/Administrator/agent-orchestration-platform/docs/方案书.html';
const pdfPath = 'C:/Users/Administrator/agent-orchestration-platform/docs/方案书.pdf';

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
