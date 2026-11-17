/**
 * Web 主路径演示录屏：每步顶部标题条 + 足够停留，便于答辩观看。
 * 依赖：frontend/mobile 的 playwright-core；Chrome；本机 Web:5173 API:8000
 */
import pw from "../frontend/mobile/node_modules/playwright-core/index.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const { chromium } = pw;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, "..");
const OUT_DIR = path.join(ROOT, "docs/交付/演示录屏");
const TMP = "/tmp/pa-demo-video";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const BASE = "http://127.0.0.1:5173";
const API = "http://127.0.0.1:8000/api/v1";

fs.mkdirSync(OUT_DIR, { recursive: true });
fs.rmSync(TMP, { recursive: true, force: true });
fs.mkdirSync(TMP, { recursive: true });

async function banner(page, title, subtitle = "") {
  await page.evaluate(
    ({ title, subtitle }) => {
      let el = document.getElementById("__demo_banner__");
      if (!el) {
        el = document.createElement("div");
        el.id = "__demo_banner__";
        Object.assign(el.style, {
          position: "fixed",
          left: "24px",
          right: "24px",
          top: "12px",
          zIndex: "2147483647",
          background: "rgba(15,61,46,0.94)",
          color: "#fff",
          padding: "14px 20px",
          borderRadius: "12px",
          fontFamily: "system-ui, -apple-system, sans-serif",
          boxShadow: "0 8px 24px rgba(0,0,0,.25)",
          pointerEvents: "none",
        });
        document.body.appendChild(el);
      }
      el.innerHTML = `<div style="font-size:20px;font-weight:700;line-height:1.3">${title}</div>` +
        (subtitle
          ? `<div style="margin-top:6px;font-size:14px;opacity:.92;line-height:1.45">${subtitle}</div>`
          : "");
    },
    { title, subtitle }
  );
}

async function clearBanner(page) {
  await page.evaluate(() => document.getElementById("__demo_banner__")?.remove());
}

async function hold(page, ms, title, subtitle) {
  if (title) await banner(page, title, subtitle || "");
  await page.waitForTimeout(ms);
}

async function apiLogin(request, username, password) {
  const r = await request.post(`${API}/auth/login`, {
    data: { username, password },
  });
  const j = await r.json();
  if (!r.ok()) throw new Error("login failed " + r.status());
  return j.data;
}

async function setAuth(page, token, user) {
  await page.addInitScript(
    ({ token, user }) => {
      localStorage.setItem(
        "paper-agent-auth",
        JSON.stringify({ state: { token, user }, version: 0 })
      );
    },
    { token, user }
  );
  await page.evaluate(
    ({ token, user }) => {
      localStorage.setItem(
        "paper-agent-auth",
        JSON.stringify({ state: { token, user }, version: 0 })
      );
    },
    { token, user }
  );
}

async function main() {
  const browser = await chromium.launch({
    executablePath: CHROME,
    headless: true,
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: TMP, size: { width: 1440, height: 900 } },
    locale: "zh-CN",
  });
  const page = await context.newPage();
  const req = context.request;

  const { token, user } = await apiLogin(req, "demo_tester", "Demo1234");
  console.log("logged in", user?.username);

  // —— 1 登录页（先看清界面，再注入登录）——
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await hold(
    page,
    4500,
    "① 登录页",
    "Web 端入口：注册 / 登录。演示账号 demo_tester。未登录只能看登录与用途说明。"
  );
  // 慢速填写，方便看清
  await clearBanner(page);
  await banner(page, "① 填写账号并登录", "用户名 demo_tester · 密码 Demo1234");
  const userInput = page.locator("input").nth(0);
  const passInput = page.locator('input[type="password"]').first();
  await userInput.click();
  await userInput.fill("");
  await userInput.type("demo_tester", { delay: 80 });
  await passInput.click();
  await passInput.fill("");
  await passInput.type("Demo1234", { delay: 80 });
  await page.waitForTimeout(1500);
  // 用 token 保证后续稳定（避免按钮文案差异）
  await setAuth(page, token, user);
  await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
  await page.waitForTimeout(800);

  // —— 2 项目列表 ——
  await hold(
    page,
    5000,
    "② 我的项目",
    "创建论文项目，选择类型（综述 / 实证研究 / 设计与实现），再进入成稿主路径。"
  );

  // —— 3 知识库 ——
  await page.goto(`${BASE}/library`, { waitUntil: "networkidle" });
  await hold(
    page,
    5500,
    "③ 公用知识库",
    "预置与用户上传的已索引论文均可检索。可按研究方向筛选；上传须勾选公用库授权。"
  );
  // 轻微滚动一点
  await page.mouse.wheel(0, 400);
  await page.waitForTimeout(2500);

  // 选一个已有项目（优先可导出 / 大纲已确认）
  const pj = await req.get(`${API}/projects`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const items = (await pj.json())?.data?.items || [];
  let project =
    items.find((p) => p.status === "exportable") ||
    items.find((p) => p.outline_confirmed) ||
    items[0];
  if (!project) {
    const c = await req.post(`${API}/projects`, {
      headers: { Authorization: `Bearer ${token}` },
      data: { title: "演示录屏临时项目", paper_type: "综述" },
    });
    project = (await c.json()).data;
  }
  const id = project.id;
  console.log("project", project.title, id);

  // —— 4 项目概览 ——
  await page.goto(`${BASE}/projects/${id}`, { waitUntil: "networkidle" });
  await hold(
    page,
    5000,
    "④ 项目概览与流程导航",
    `当前项目：「${project.title}」。左侧步骤：检索 → 大纲 → 正文 → 润色 → 核查 → 导出。`
  );

  // —— 5 检索 ——
  await page.goto(`${BASE}/projects/${id}/search`, { waitUntil: "networkidle" });
  await hold(
    page,
    4000,
    "⑤ 文献检索（S2）",
    "混合检索（关键词 + 向量）+ Reranker。结果带来源题名、作者、年份与证据片段页码。"
  );
  await clearBanner(page);
  await banner(page, "⑤ 正在检索…", "查询：国产青春电影的怀旧叙事");
  const q = page.locator("textarea").first();
  await q.click();
  await q.fill("");
  await q.type("国产青春电影的怀旧叙事", { delay: 40 });
  await page.waitForTimeout(800);
  await page.getByRole("button", { name: /检索|搜索|提交/ }).first().click().catch(async () => {
    await page.locator('button[type="submit"]').first().click();
  });
  await page.waitForTimeout(8000);
  await hold(
    page,
    6000,
    "⑤ 检索结果与证据",
    "每条命中均可回链公用库论文。可加入「备选篮」供对比 / 研究空白使用。"
  );
  await page.mouse.wheel(0, 350);
  await page.waitForTimeout(2500);

  // —— 6 大纲 ——
  await page.goto(`${BASE}/projects/${id}/outline`, { waitUntil: "networkidle" });
  await hold(
    page,
    6500,
    "⑥ 大纲生成与确认（S7）",
    "可编辑章节与写作意图。必须「确认大纲」后才能批量写作；未确认不能定稿。"
  );
  await page.mouse.wheel(0, 420);
  await page.waitForTimeout(3000);

  // —— 7 写作 ——
  await page.goto(`${BASE}/projects/${id}/editor`, { waitUntil: "networkidle" });
  await hold(
    page,
    6500,
    "⑦ 章节写作（S8）",
    "按节生成正文。正式引用必须回链已索引论文与证据；无证据句标为草稿。"
  );
  await page.mouse.wheel(0, 500);
  await page.waitForTimeout(3500);

  // —— 8 润色 ——
  await page.goto(`${BASE}/projects/${id}/polish`, { waitUntil: "networkidle" });
  await hold(
    page,
    5500,
    "⑧ 润色对照（polish）",
    "轻度 / 学术 / 深度。确认前不替换正文；不改数字、专名、引用与结论。降重请求会被拒绝。"
  );

  // —— 9 核查 ——
  await page.goto(`${BASE}/projects/${id}/citations`, { waitUntil: "networkidle" });
  await hold(
    page,
    4500,
    "⑨ 引用与逻辑核查（S9）",
    "L1 元数据一致 · L2 证据页码绑定。未通过项会列出问题句；定稿前须全部通过。"
  );
  const runBtn = page.getByRole("button", { name: /核查|运行|检查/ }).first();
  if (await runBtn.count()) {
    await clearBanner(page);
    await banner(page, "⑨ 运行核查…", "生成引用 / 逻辑问题报告");
    await runBtn.click().catch(() => {});
    await page.waitForTimeout(10000);
  }
  await hold(
    page,
    5500,
    "⑨ 核查结果",
    "通过后方可定稿导出；否则可继续改稿或仅导出「草稿」。"
  );

  // —— 10 导出 ——
  await page.goto(`${BASE}/projects/${id}/export`, { waitUntil: "networkidle" });
  await hold(
    page,
    6000,
    "⑩ 文档导出（S10）",
    "草稿导出带辅助生成标识；定稿受引用闸门约束。可打开 DOCX / PDF。"
  );

  // —— 11 研究工具 ——
  await page.goto(`${BASE}/tools/analysis`, { waitUntil: "networkidle" });
  await hold(
    page,
    6000,
    "⑪ 独立研究工具",
    "多篇对比（S4）与研究空白（S6）不在成稿主链内，使用备选篮；不替代大纲确认与引用闸门。"
  );

  await hold(
    page,
    4000,
    "演示结束",
    "主路径：登录 → 项目 → 知识库/检索 → 大纲确认 → 写作 → 润色 → 核查 → 导出。感谢观看。"
  );

  await context.close();
  await browser.close();

  // 找到 webm
  const files = fs.readdirSync(TMP).filter((f) => f.endsWith(".webm"));
  if (!files.length) throw new Error("未生成视频");
  const src = path.join(TMP, files[0]);
  const destWebm = path.join(OUT_DIR, "论文智能体_Web主路径演示.webm");
  fs.copyFileSync(src, destWebm);
  const st = fs.statSync(destWebm);
  console.log("saved", destWebm, (st.size / 1024 / 1024).toFixed(2) + "MB");

  // 尝试 ffmpeg（若存在）转 mp4
  const { spawnSync } = await import("child_process");
  const ff = spawnSync("ffmpeg", ["-y", "-i", destWebm, "-c:v", "libx264", "-pix_fmt", "yuv420p", path.join(OUT_DIR, "论文智能体_Web主路径演示.mp4")], {
    encoding: "utf8",
  });
  if (ff.status === 0) console.log("also mp4 ok");
  else console.log("ffmpeg skip:", (ff.stderr || ff.error || "").toString().slice(0, 120));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
