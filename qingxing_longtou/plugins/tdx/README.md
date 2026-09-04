# 通达信第三方插件 / 导出接入说明

将通达信公式、DLL 插件或自写导出脚本的结果放到本目录的 `export/` 下。

## 必需文件

### export/boards.csv

```csv
code,name,kind,change_percent,amount,main_net_inflow,up_count,down_count
BK1234,人工智能,concept,4.52,1200000000,350000000,42,8
```

### export/members.csv（推荐）或 export/members_{板块代码}.csv

```csv
board_code,board_name,code,name,price,change_percent,amount
BK1234,人工智能,300xxx,某某股份,25.6,10.01,890000000
```

### 可选 export/zt.csv / zb.csv

```csv
code,name,first_seal_time,consecutive_boards,seal_amount,open_count
300xxx,某某股份,093215,3,120000000,0
```

## 环境变量

- `TDX_HOME`：通达信安装目录（可读自定义板块 `.blk`，仅代码无行情）
- `TDX_PLUGIN_URL`：第三方插件本地 HTTP，例如 `http://127.0.0.1:18080/snapshot`

## Windows 插件示例流程

1. 通达信盘后/盘中公式选出板块成分 → 导出 CSV
2. 或使用现有 TdxEngine 类插件推送到 `TDX_PLUGIN_URL`
3. 在本软件数据源选择「通达信」后点「刷新选股」
