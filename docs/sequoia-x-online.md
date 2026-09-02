# Sequoia-X 在线网址（自己的，不用每次开本地服务）

`https://xl.mininas.cc/` 是别人的「短线寻龙 · 同花顺金融数据终端」，不是 Sequoia-X。哪天对方关了，那个网址就没了。

Sequoia-X 可以做成**你自己的网页**：浏览器打开就能扫，不必再双击 bat / 开 Python。顺势选股仍用本机 `8787`，互不影响。

这边没法替你按下 GitHub 的开关（仓库还没打开 Pages，Actions 也没有这个权限）。你点一次就能用。

## 免费 github.io 地址（推荐先做这个）

1. 打开 https://github.com/yauklt502/my-shunshixuangu/settings/pages
2. **Build and deployment → Source** 选 **GitHub Actions**
3. 保存后打开 Actions，点 **Deploy Sequoia-X Pages** → **Run workflow**
4. 变绿之后打开：

**https://yauklt502.github.io/my-shunshixuangu/**

静态页没有 `/api` 代理，页面会走腾讯 / 新浪 JSONP（右上角默认「腾讯」）。同花顺若扫不出，保持「腾讯」。

## 自己的短域名（类似 xl.mininas.cc）

想要 `xuangu.你的域名.com` 这种地址：

1. 买一个域名（Cloudflare / 阿里云 / Namesilo 都可以）
2. 注册免费 [Cloudflare](https://dash.cloudflare.com/sign-up)，把域名加进去
3. Cloudflare 左侧 **Workers & Pages** → Create → 连上这个 GitHub 仓库（或把下面两个 Secrets 填进仓库后等 Actions 部署）
   - 仓库 Settings → Secrets：`CLOUDFLARE_API_TOKEN`、`CLOUDFLARE_ACCOUNT_ID`
4. 部署后先得到 `https://sequoia-x.<子域>.workers.dev`
5. Worker 设置里 **Custom Domain** 绑你的域名

Worker 带 `/api` 代理，同花顺 + 腾讯和本机 9801 一样。

本地 `http://127.0.0.1:9801/` 仍然可用。
