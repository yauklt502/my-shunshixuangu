# 短线寻龙 · 同花顺金融数据终端

自己的短线监控站。别人的 [xl.mininas.cc](https://xl.mininas.cc/) 关掉也不影响你。打开网址就能用，不必每次本地开服务。

数据走同花顺开放接口（[fuyao.aicubes.cn](https://fuyao.aicubes.cn/)）。API Key 只存在你自己的浏览器里。

## 现在就能打开

浏览器打开（已核对页面能渲染、侧栏能点）：

**https://raw.githack.com/yauklt502/my-shunshixuangu/cursor/duanxian-xunlong-e-drive-bac5/web/index.html**

1. 收藏这个地址。
2. 到 [fuyao.aicubes.cn](https://fuyao.aicubes.cn/) 申请 API Key。
3. 填进右上角回车，点「连接测试」。

合并到 `main` 之后，也可以用：

https://raw.githack.com/yauklt502/my-shunshixuangu/main/web/index.html

## 做成自己的短域名（和 xl.mininas.cc 一样）

仓库已经接到 Cloudflare Worker `my-shunshixuangu`，每次推送都会自动发布。要得到 `https://xxx.workers.dev` 或 `https://xunlong.你的域名.com`：

1. 打开 [Cloudflare 控制台里的 my-shunshixuangu](https://dash.cloudflare.com/47cba3914c0ddb2d594f4793862c837d/workers/services/view/my-shunshixuangu)。
2. Settings 里打开 **workers.dev** 子域（当前未对外解析，所以 `*.workers.dev` 会 1042）。
3. 可选：Custom Domains 绑定你自己的域名。

GitHub Pages：仓库 Settings → Pages → Source 选 GitHub Actions，再合并本 PR。之后地址是：

https://yauklt502.github.io/my-shunshixuangu/

## 本地备用

双击 `启动.bat`，或 `一键部署到E盘.bat` 拷到 `E:\短线寻龙`。需要 Python 3 或 Node.js。不要直接双击 `web/index.html`。

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
