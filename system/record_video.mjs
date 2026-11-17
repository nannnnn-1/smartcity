import { chromium } from 'playwright';
import fs from 'node:fs';

const OUT = 'D:/智慧城市课程/video';
fs.mkdirSync(OUT + '/raw', { recursive: true });
const browser = await chromium.launch({
  channel: 'msedge', headless: true,
  args: ['--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'],
});
const ctx = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  deviceScaleFactor: 1,
  recordVideo: { dir: OUT + '/raw', size: { width: 1280, height: 720 } },
});
const page = await ctx.newPage();
const recordStart = Date.now();
await page.goto('http://127.0.0.1:8088/', { waitUntil: 'domcontentloaded' });

// 等首屏加载完成
await page.waitForFunction(() => {
  const l = document.getElementById('loader');
  return l && l.style.display === 'none';
}, null, { timeout: 120000 });
const appReady = Date.now();
const trimStart = (appReady - recordStart) / 1000;

// 视频字幕 / 幻灯片覆盖层
await page.addStyleTag({ content: `
  #cine-cap{position:fixed;left:50%;bottom:34px;transform:translateX(-50%);z-index:99999;
    display:flex;align-items:center;gap:12px;padding:9px 18px;background:rgba(4,12,22,.82);
    border-left:3px solid #5fd7ff;color:#eaf8ff;font-family:"Microsoft YaHei UI",sans-serif;
    font-size:17px;letter-spacing:.5px;backdrop-filter:blur(8px);opacity:0;transition:opacity .45s;
    pointer-events:none;box-shadow:0 8px 30px rgba(0,0,0,.45);max-width:90vw}
  #cine-cap.on{opacity:1}
  #cine-cap b{color:#5fd7ff;font-family:Bahnschrift,sans-serif;font-size:13px;letter-spacing:2px}
  #cine-cap i{display:block;width:1px;height:16px;background:rgba(95,215,255,.35)}
  #cine-slide{position:fixed;inset:0;z-index:99998;background:#040a12;display:none;
    align-items:center;justify-content:center;flex-direction:column;pointer-events:none}
  #cine-slide.on{display:flex}
  #cine-slide img{width:86vw;max-height:74vh;object-fit:contain;border:1px solid rgba(95,215,255,.22);
    box-shadow:0 30px 90px rgba(0,0,0,.6)}
  #cine-slide .sc{position:absolute;left:7vw;bottom:7vh;color:#8fa9bf;font-family:"Microsoft YaHei UI";
    font-size:14px;letter-spacing:1px;border-left:3px solid #35d0a5;padding-left:12px}
`});
await page.evaluate(() => {
  const cap = document.createElement('div'); cap.id = 'cine-cap';
  cap.innerHTML = '<b>01</b><i></i><span>城市内涝 · 分钟级战场</span>';
  document.body.appendChild(cap);
  const sl = document.createElement('div'); sl.id = 'cine-slide';
  sl.innerHTML = '<img id="cine-img" src=""><div class="sc" id="cine-sc"></div>';
  document.body.appendChild(sl);
  requestAnimationFrame(() => cap.classList.add('on'));
});

const wait = (ms) => page.waitForTimeout(ms);
const cap = async (idx, text) => page.evaluate(([i, t]) => {
  const c = document.getElementById('cine-cap');
  c.querySelector('b').textContent = i;
  c.querySelector('span').textContent = t;
  c.classList.add('on');
}, [idx, text]);
const hideCap = () => page.evaluate(() => document.getElementById('cine-cap').classList.remove('on'));
const slide = async (src, caption) => page.evaluate(([s, c]) => {
  const el = document.getElementById('cine-slide');
  document.getElementById('cine-img').src = s;
  document.getElementById('cine-sc').textContent = c;
  el.classList.add('on');
}, [src, caption]);
const hideSlide = () => page.evaluate(() => document.getElementById('cine-slide').classList.remove('on'));

const ev = (fn, arg) => page.evaluate(fn, arg);

console.log('app ready after', trimStart.toFixed(2), 's');
await wait(700);

// 01 城市内涝
await cap('01', '城市内涝 · 分钟级战场');
await ev(async ([sid, f]) => { await window.__app.setScenario(sid, false); window.__app.togglePlay(false); window.__app.setFrame(f); }, ['replay-2309', 4]);
await wait(1500);
await ev(() => window.__app.flyPreset('overview'));
await wait(17300);

// 02 数据先行：管线 + 研究区
await cap('02', '数据先行 · 26.7 km² 数字底座');
await slide('/assets/slides/fig_pipeline.png', '数据管线：采集 → 清洗 → 融合 → 建模 → 校核 → 发布');
await wait(12000);
await slide('/assets/slides/fig_study_area.png', '研究区：莲花山—中心公园—福田 CBD—华强北');
await wait(11500);
await hideSlide();

// 03 三类情景
await cap('03', '三类情景 · 10 分钟一帧');
await ev(async () => { await window.__app.setScenario('design-50', false); });
await wait(1800);
await ev(() => { window.__app.togglePlay(false); window.__app.setFrame(10); window.__app.flyPreset('overview'); });
await wait(9000);
await ev(() => window.__app.setFrame(28));
await wait(11400);

// 04 结果
await cap('04', '50 年一遇 · 最大水深 2.33 m');
await ev(() => { window.__app.setFrame(48); window.__app.flyPreset('overview'); });
await wait(19800);

// 05 三维
await cap('05', '三维数字孪生 · 水面随地形起伏');
await ev(() => window.__app.flyPreset('cbd'));
await wait(6500);
await ev(() => window.__app.flySensor('SN-03'));
await wait(6500);
await ev(() => { window.__app.toggleLayer('water', false); });
await wait(3200);
await ev(() => { window.__app.toggleLayer('water', true); });
await wait(2700);

// 06 预警与处置
await cap('06', '五级预警 · 一点一策');
await ev(async () => { await window.__app.setScenario('replay-2309', false); window.__app.setFrame(40); window.__app.flyPreset('overview'); });
await wait(3500);
await ev(() => { const a = document.querySelector('.alert-item'); if (a) a.click(); });
await wait(9400);
await ev(() => document.getElementById('modal-close').click());
await wait(5500);

// 07 分工与总结
await cap('07', '数据 · 三维 · 平台 · 表达');
await ev(async () => { await window.__app.setScenario('design-5', false); window.__app.setFrame(32); window.__app.flyPreset('overview'); });
await wait(4500);
await slide('/assets/slides/fig_architecture.png', '四层解耦：感知 → 数据 → 模型/预警 → 应用');
await wait(8600);
await slide('/assets/slides/fig_gantt.png', '六周计划 · 四人并行 · 每周五联调');
await wait(7000);
await hideSlide();
await ev(() => window.__app.flyPreset('overview'));
await wait(5000);
await hideCap();
await wait(3000);

const video = page.video();
await ctx.close();
const path = await video.path();
fs.copyFileSync(path, OUT + '/raw/content.webm');
fs.writeFileSync(OUT + '/timings.json', JSON.stringify({ recordStart, appReady, trimStart, duration: (Date.now() - recordStart) / 1000 }, null, 2));
console.log('saved', path, 'trim', trimStart.toFixed(2));
await browser.close();
