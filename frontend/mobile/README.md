# 论文智能体 · 移动端（Taro）

一套代码覆盖 **微信小程序** 与 **Android（H5 / WebView）**，只调用后端 `/api/v1`。管理后台仍仅 Web。

目录：`frontend/mobile/`

## 前置

1. 本机 API 已启动：`http://127.0.0.1:8000`
2. Node 18+

```bash
cd frontend/mobile
npm install
```

## 微信小程序调试（怎么打开）

### 1. 启动后端

在仓库根目录：

```bash
source /opt/anaconda3/etc/profile.d/conda.sh
conda activate paperAgent
export DATABASE_URL=postgresql+psycopg://paper_agent@localhost:5433/paper_agent
export JWT_SECRET=dev-change-me
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

### 2. 编译小程序（watch）

```bash
cd frontend/mobile
npm run dev:weapp
```

成功后会生成 / 更新 `frontend/mobile/dist/`。

### 3. 用微信开发者工具打开

1. 安装并打开 [微信开发者工具](https://developers.weixin.qq.com/miniprogram/dev/devtools/download.html)
2. **导入项目**（或「+」）
3. **目录**选：

   `/Users/sw/Desktop/26国培东软/论文智能体/frontend/mobile`

   （`project.config.json` 里已写 `miniprogramRoot: dist/`，工具会读编译产物）
4. AppID：没有正式号可选 **测试号 / 游客模式**（`touristappid`）
5. 进入后打开右上角 **详情 → 本地设置**：
   - 勾选 **不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书**
   - 勾选 **启用调试**（可选）
6. 模拟器应出现登录页；账号见仓库根 README（如 `demo_tester` / `Demo1234`）

### 4. 真机预览

开发者工具点 **预览** → 手机微信扫码。  
真机访问电脑 API 时，把 `src/utils/config.ts` 或环境变量改成电脑局域网地址，例如：

```bash
# .env.development
TARO_APP_API_BASE=http://192.168.x.x:8000/api/v1
```

改完需重启 `npm run dev:weapp`。

### 常见问题

| 现象 | 处理 |
| --- | --- |
| 白屏 / 找不到页面 | 确认 `dev:weapp` 在跑，且导入的是 `frontend/mobile` 不是单独 `dist` |
| request:fail | 勾选「不校验合法域名」；确认 API 在 8000 |
| 上传 PDF 失败 | 小程序体积受限，大文件改用 Web 上传 |

## Android（H5 WebView）

见上文历史说明：先 `npm run dev:h5`，再用 Android Studio 打开 `frontend/mobile/android`。

## 主路径

登录 → 项目 → 知识库 / 检索 → 大纲 → 写作 → 润色 → 核查 → 导出  

底部 Tab：**项目 | 知识库 | 分析**（备选篮、S4 对比、S6 研究空白）
