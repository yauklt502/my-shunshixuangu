# 短线寻龙 · 同花顺金融数据终端

自己的短线监控站，打开网址就能用，不必再依赖 [xl.mininas.cc](https://xl.mininas.cc/)，也不必每次本地开服务。

数据走同花顺开放接口（[fuyao.aicubes.cn](https://fuyao.aicubes.cn/)）。API Key 只存在你自己的浏览器里。

## 在线打开（推荐）

推送到 GitHub 后，Cloudflare Workers 会自动发布静态站：

- **Cloudflare：** [https://my-shunshixuangu.yuanchanglin7341.workers.dev/](https://my-shunshixuangu.yuanchanglin7341.workers.dev/)
- **GitHub Pages（合并到 main 后）：** [https://yauklt502.github.io/my-shunshixuangu/](https://yauklt502.github.io/my-shunshixuangu/)

用法：

1. 浏览器打开上面的网址并收藏。
2. 到 [fuyao.aicubes.cn](https://fuyao.aicubes.cn/) 申请 API Key。
3. 把 Key 填进右上角后回车，点「连接测试」。

换电脑或清缓存后需要再输一次 Key。不要把 Key 发给别人。

### 绑定自己的域名（可选）

和 `xl.mininas.cc` 一样，可以在 Cloudflare 控制台给 Worker `my-shunshixuangu` 加自定义域，例如 `xunlong.你的域名.com`，加完后打开那个域名即可。

## 本地备用

没有网或要改代码时，仍可双击 `启动.bat`（或 `一键部署到E盘.bat` 拷到 `E:\短线寻龙`）。需要 Python 3 或 Node.js。不要直接双击 `web/index.html`。

```bash
python serve.py
# 或
node serve.js
```

## 模块

| 侧栏 | 说明 |
| --- | --- |
| 寻龙总览 | 连板 / 封单 / 热度 / 龙虎加权龙值 |
| 实时选真龙 | 约 8 秒刷新快照并重排 |
| 未涨停真龙 | 涨幅 2%–9.5% 的可买强势票 |
| 买卖点 / 盘口测谎 | 量价 + 封单 + 龙虎推断 |
| 涨停梯队 / 涨停池 / 炸板 / 火箭热股 / 龙虎榜 | 对应专项数据 |
| 自选监控 / 个股详情 | 快照与前复权 K 线 |

接口限频约 20 次/分钟。数据仅供研究参考，不构成投资建议。
