# 开盘啦 · 市场雷达

独立网页，按《开盘啦 API 接口文档》对接龙虎 VIP 行情接口，覆盖市场概览、涨停分析、板块、龙虎榜、竞价、个股、风口、题材、直播和资讯。

涨跌配色沿用 A 股习惯：红涨绿跌。今日数据走实时域名，历史日期自动切到复盘域名。09:15 前默认上一交易日。

## 部署到本机 F 盘（Windows）

下载现成压缩包，解压到 F 盘，不要用仓库里的 `install-to-F.bat`。

1. 安装 [Node.js 18+](https://nodejs.org/)（勾选加入 PATH）
2. 下载 [`deploy/kaipanla-windows.zip`](https://github.com/yauklt502/my-shunshixuangu/raw/cursor/kaipanla-web-ui-71ed/deploy/kaipanla-windows.zip)
3. 解压到 `F:\kaipanla`（里面要有 `start.bat`、`dist`、`server`）
4. 双击 `F:\kaipanla\start.bat`，浏览器打开 http://127.0.0.1:3000

日常启动仍用 `start.bat`，停止用 `stop.bat`。详见 `F盘部署说明.txt`。

## 开发启动

```bash
npm install
npm run dev
```

浏览器打开 http://localhost:5173 。本地 Node 代理会转发 `/api/kpl`。

生产构建：

```bash
npm run build
set NODE_ENV=production
npm start
```

默认 http://127.0.0.1:3000 。

## 设置

右上角「设置」可填 Token / UserID。题材竞价、最强风口等接口在文档中标记为必填，未填写时这些页可能返回错误，其余复盘接口通常可直接看。
