# 三条纪律看板

把「低吸纪律、二三板节奏、回撤时别乱动」做成白底实时看板。

## 功能

1. **低吸纪律** — 日内高低点位置 + **回踩 MA5**
2. **二三板节奏** — 涨停梯队；**点击二/三板股票**可加入低吸观察
3. **回撤不乱动** — 上证/创业板近高点回撤；可调软/硬冻结阈值
4. 数据源切换：东方财富 / 同花顺 / 通达信兼容（腾讯）
5. 一键截图（白底 PNG）

## 本地启动

```bash
npm install
npm start
# http://127.0.0.1:5177
```

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
