# 顺势选股 · 龙头盯盘

## 怎么打开（小白）

刚才失败是因为中文路径被 Windows 读乱了。现在改成英文目录。

1. 重新下载最新压缩包：https://github.com/yauklt502/my-shunshixuangu/archive/refs/heads/cursor/sector-leader-watch-1ed7.zip
2. 解压后，双击 **`INSTALL-TO-E.bat`**
3. 文件会放到 **`E:\ShunshiWatch`**，浏览器会自动打开
4. 以后每次：双击 **`E:\ShunshiWatch\open.bat`**

黑窗口不要关。关掉 = 关掉盯盘。
没有 E 盘会放到桌面 `ShunshiWatch`。

## 切换数据源

右上角是一个下拉框，占地方更少：

- **东方财富**：公开行情，打开就能看。
- **同花顺**：扶摇 API（https://fuyao.aicubes.cn/admin/）。第一次选「同花顺」后，把密匙贴进输入框，点保存。密匙只存在你这台电脑的浏览器里，不会进 GitHub。也可以把密匙单独放在 `E:\ShunshiWatch\fuyao-key.txt`（一行一个 sk- 开头的密匙）。不要把这个文件发到网上。
- **通达信本地**：读本机 `E:\new_tdx\vipdoc` 日线（最后两根 K 线算涨幅），板块名单来自 `E:\new_tdx\T0002\hq_cache\block_gn.dat` 和 `block.dat`。这是收盘数据，不是盘中 tick。
- **通达信实时**：连通达信行情服务器（7709）。第一次大约半分钟（要下板块和股票名单），之后大约 10 秒刷新。没有涨停池先封时间，涨停/炸板按涨停价启发式判断。

同花顺、通达信都暂无主力净流入；选这个排序时会改按成交额。周末涨停/炸板池经常是空的，板块涨幅仍可看。

## Python 表格版（命令行）

网页版保留不变。若想在终端里看表格结果，可用 `python/leader_watch.py`：

```bash
pip install -r requirements.txt
python3 python/leader_watch.py
python3 python/leader_watch.py --date 20250828
python3 python/leader_watch.py --universe concept --sort limitUp
```

参数：

| 参数 | 说明 |
|------|------|
| `--date` | 交易日 `YYYYMMDD`，默认今日（复盘用） |
| `--universe` | `all` / `concept` / `industry` |
| `--sort` | `change` / `limitUp` / `amount` / `inflow` |

输出包含：大盘指数表、全市场总龙头/龙二/龙三、前三板块及龙一/龙二/龙三。数据源为东方财富（与网页默认一致）。
