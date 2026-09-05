# 三条纪律看板

把「低吸纪律、二三板节奏、回撤时别乱动」做成白底实时看板。

## 功能

1. **低吸纪律** — 日内高低点位置 + **回踩 MA5**
2. **二三板节奏** — 涨停梯队；**点击二/三板股票**可加入低吸观察
3. **回撤不乱动** — 上证/创业板近高点回撤；可调软/硬冻结阈值
4. 数据源切换：东方财富 / 同花顺 / 通达信兼容（腾讯）
5. 一键截图（白底 PNG）

## Windows 本地完整包（推荐）

下载：

https://github.com/yauklt502/my-shunshixuangu/raw/cursor/three-discipline-dashboard-a337/web/download/three-discipline-local.zip

解压后**双击 `启动.bat` 即可打开网页**（和以前一样）。

- 不需要 `npm install`
- 不需要创建 venv
- 不需要联网装依赖  
本机只需已安装 Node.js（勾选 Add to PATH）。

重新打包：

```bash
npm run pack:local
```

## 本地启动（开发）

```bash
npm start
# http://127.0.0.1:5177
```

（运行期零 npm 依赖；只有部署 Workers 时才需要 `npm i` 装 wrangler。）

## Cloudflare Workers 部署

本仓库按成功 PR 约定提供：

- `wrangler.toml`（`name = "my-shunshixuangu"`）
- `src/worker.js`（`/api/*` 行情逻辑）
- `web/` 静态前端

Workers Builds 会自动构建部署；也可：

```bash
npm run deploy
```

> 仅供纪律可视化，不构成投资建议。
