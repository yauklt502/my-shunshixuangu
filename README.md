# 10秒定龙头 · 盘中跟 / 盘后盯

先定板块，再戴三顶帽子，最后盯一只。盘中跟、盘后盯同一套顺序。

1. 今天主线是谁（涨停家数，并列看成交和高度）
2. 主线里谁先封、封得死 —— **火车头**（一字 / 爆量 / 烂板往后顺）
3. 板块指数红不红、跟风有没有、炸了散不散
4. 砸盘时谁最抗、谁先碎
5. 谁叫得出来 —— **情绪龙头**（人气是加分，不是硬门槛）
6. 最后看量：健康留下，一字或爆量见顶放弃

三路对照：火车头、情绪龙头、空间高标。

## 一键启动

Windows 双击 `一键启动.bat`  
Mac / Linux 运行 `./一键启动.sh` 或 `./run.sh`

会自动装依赖、打开服务、弹出浏览器：

http://127.0.0.1:8688

点个股名称会弹出通达信日K / 分时 / 五档（主站 `115.238.90.165:7709`，数据层 `eltdx`）。

页面右上角 **截屏** 一键存图。也可以直接打开：

http://127.0.0.1:8688/api/shot.png

```bash
python3 launch.py
python3 -m dragon 20260904 --review --shot
```

## 下载

源码 zip（GitHub 当前分支）：

https://github.com/yauklt502/my-shunshixuangu/archive/refs/heads/cursor/ten-sec-dragon-6202.zip

本地跑起来后也可以下：

http://127.0.0.1:8688/download.zip

## 测试

```bash
python3 -m unittest tests.test_score tests.test_backtest tests.test_shot -v
```

## 数据

东方财富：涨停池、炸板池、概念指数、人气榜、实时换手/成交额/量比、上证/深成/创业板指数。
