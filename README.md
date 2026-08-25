# my-shunshixuangu

A-share stock-picking helpers powered by **同花顺 Fuyao** financial data
([docs](https://fuyao.aicubes.cn/docs), [llms-full.txt](https://fuyao.aicubes.cn/llms-full.txt)).

## Setup

```bash
cp .env.example .env
# edit .env → set FUYAO_API_KEY=sk-fuyao-...

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python scripts/smoke_test.py
```

Never commit `.env` or paste the real key into tracked files.

## Cursor MCP（一键配置）

```bash
cp .env.example .env          # 填入 FUYAO_API_KEY
bash scripts/setup-fuyao-mcp.sh
# 重启 Cursor → Settings → MCP，确认 fuyao-* Connected
```

脚本会写入（含真实 key，已 gitignore）：

- 项目：`.cursor/mcp.json`
- 用户：`~/.cursor/mcp.json`

| Server | Endpoint | Use |
|---|---|---|
| `fuyao-a-share` | `/mcp/a-share` | 行情 / 财务 / 涨跌停 / 龙虎榜 / 竞价 |
| `fuyao-a-share-index` | `/mcp/a-share-index` | 同花顺指数与成分股 |
| `fuyao-fund` | `/mcp/fund` | 公募基金 |
| `fuyao-meta` | `/mcp/meta` | 标的检索（建议常开） |

配好后直接对话即可，例如：「贵州茅台今天涨多少？再拉近 1 个月日 K」

## Python REST client

```python
from fuyao import FuyaoClient

c = FuyaoClient()  # reads FUYAO_API_KEY
print(c.search_tickers("贵州茅台", limit=3))
print(c.prices_snapshot("600519.SH"))
print(c.limit_up_pool())
print(c.dragon_tiger_list())
```

Auth header: `X-api-key`. Responses use the `ApiResponse` envelope (`code` / `message` / `request_id` / `data`); the client unwraps `data` and raises `FuyaoError` when `code != 0`.

## API notes

- Base URL: `https://fuyao.aicubes.cn`
- Paths look like `/api/<universe>/<datatype>/<action>`
- Full contract for agents: https://fuyao.aicubes.cn/llms-full.txt
