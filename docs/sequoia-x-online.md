# Sequoia-X 在线网址（自己的，不用每次开本地服务）

`https://xl.mininas.cc/` 是别人的「短线寻龙 · 同花顺金融数据终端」，不是 Sequoia-X。哪天对方关了，那个网址就没了。

Sequoia-X 可以做成**你自己仓库里的网页**：浏览器打开就能扫，不必再双击 bat / 开 Python。顺势选股仍用本机 `8787`，互不影响。

## 免费：GitHub Pages

推送本分支后，GitHub Actions 会把 `web/` 发布成静态站。

1. 打开仓库 **Settings → Pages**
2. Build and deployment → Source 选 **GitHub Actions**
3. 等 Actions 里 `Deploy Sequoia-X Pages` 变绿

你的地址是：

**https://yauklt502.github.io/my-shunshixuangu/**

静态页没有 `/api` 代理，页面会改走腾讯 / 新浪的 JSONP（右上角默认「腾讯」）。同花顺若扫不出，保持「腾讯」即可。

## 自己的短域名（类似 xl.mininas.cc）

GitHub Pages 也可以绑自定义域名（Settings → Pages → Custom domain），例如 `xuangu.yourdomain.com`。

若要和本机一样走同花顺代理（`/api/ths`），用 Cloudflare Worker（免费档够用）：

1. 注册 [Cloudflare](https://dash.cloudflare.com/sign-up)
2. 建 API Token：Workers 编辑权限；记下 Account ID
3. 仓库 Settings → Secrets and variables → Actions，添加：
   - `CLOUDFLARE_API_TOKEN`
   - `CLOUDFLARE_ACCOUNT_ID`
4. 再跑一次 Actions：`Deploy Sequoia-X Cloudflare`
5. 得到 `https://sequoia-x.<你的子域>.workers.dev`
6. 在 Worker 设置里绑自己的域名（域名可先托管到 Cloudflare）

本地 `http://127.0.0.1:9801/` 仍然可用，给离线或不想用公网的时候。
