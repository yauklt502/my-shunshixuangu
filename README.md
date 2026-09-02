# 开盘啦 · 市场雷达

独立网页，按《开盘啦 API 接口文档》对接龙虎 VIP 行情接口，覆盖市场概览、涨停分析、板块、龙虎榜、竞价、个股、风口、题材、直播和资讯。

涨跌配色沿用 A 股习惯：红涨绿跌。今日数据走实时域名，历史日期自动切到复盘域名。09:15 前默认上一交易日。

## 部署到本机 F 盘（Windows）

云端写不到你的 F:。在 Windows 上打开本仓库后双击 `install-to-F.bat`，会复制到 `F:\kaipanla` 并启动。

需要已安装 [Node.js 18+](https://nodejs.org/)，且资源管理器能看到 F 盘。细节见 `F盘部署说明.txt`。

| 文件 | 作用 |
|------|------|
| `install-to-F.bat` | 复制到 `F:\kaipanla` 并启动 |
| `F:\kaipanla\start.bat` | 以后日常启动（http://127.0.0.1:3000） |
| `F:\kaipanla\stop.bat` | 停止服务 |

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
