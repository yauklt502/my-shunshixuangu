import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdx_source import Quotes
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import threading
from tabulate import tabulate

print("=" * 80)
print("  趋势王·创业板精选（参数调整版）")
print("=" * 80)

# ===== 1. 连接服务器 =====
print("\n[1/4] 连接通达信行情服务器...")
client = Quotes.factory(market='std')
test_kl = client.bars(symbol='300750', frequency=9, offset=1)
if test_kl is None or len(test_kl) == 0:
    print("❌ 服务器连接失败，请检查通达信是否开启")
    input("按回车退出...")
    exit()
print("✅ 连接成功")

# ===== 2. 获取创业板股票列表 =====
print("\n[2/4] 获取创业板列表...")
sh = client.stocks(market=1)   # 上海
sz = client.stocks(market=0)   # 深圳
all_df = pd.concat([sh, sz], ignore_index=True)
all_df['code'] = all_df['code'].astype(str).str.zfill(6)

# 创业板：300开头
cyb_df = all_df[
    all_df['code'].str.startswith('300') &
    (~all_df['name'].str.contains('ST|退', na=False))
].copy()
name_map = dict(zip(cyb_df['code'], cyb_df['name']))
codes = cyb_df['code'].tolist()
print(f"✅ 创业板标的: {len(codes)} 只")

# ===== 3. 多线程获取 K 线 & 筛选 =====
print(f"\n[3/4] 多线程核验 {len(codes)} 只标的（15线程）...")

_local = threading.local()

def _connect():
    if not hasattr(_local, 'cli'):
        _local.cli = Quotes.factory(market='std')
    return _local.cli

def _screen(code):
    try:
        c = _connect()
        kl = c.bars(symbol=code, frequency=9, offset=130, fwd=True)  # 前复权：避免除权跳空污染涨幅/均线
        if kl is None or len(kl) < 60:
            return None
        
        price = float(kl['close'].iloc[-1])
        yclose = float(kl['close'].iloc[-2])
        if yclose <= 0:
            return None
        
        # ===== 涨幅 3% - 12% =====
        chg = (price - yclose) / yclose * 100
        if not (3 <= chg <= 12):
            return None
        
        # ===== 量比 >= 1.8 =====
        vol_today = float(kl['vol'].iloc[-1])
        vol_avg5 = float(kl['vol'].iloc[-6:-1].mean())
        if vol_avg5 <= 0:
            return None
        vr = vol_today / vol_avg5
        if vr < 1.8:
            return None
        
        # ===== 均线计算（新增 MA5, MA10）=====
        close_arr = kl['close'].astype(float)
        ma5 = close_arr.rolling(5).mean().iloc[-1]
        ma5_last = close_arr.rolling(5).mean().iloc[-2]
        ma10 = close_arr.rolling(10).mean().iloc[-1]
        ma20 = close_arr.rolling(20).mean().iloc[-1]
        ma60 = close_arr.rolling(60).mean().iloc[-1]
        ma120 = close_arr.rolling(120).mean().iloc[-1] if len(close_arr) >= 120 else ma60
        ma60_last = close_arr.rolling(60).mean().iloc[-2]
        
        # ===== 条件：5日线向上 且 5日线 > 10日线 =====
        if not (ma5 > ma5_last and ma5 > ma10):
            return None
        
        # ===== 10日振幅 < 15% =====
        high_arr = kl['high'].astype(float)
        low_arr = kl['low'].astype(float)
        amp10 = ((high_arr - low_arr) / low_arr * 100).tail(10).mean()
        if amp10 >= 15:
            return None
        
        # ===== 乖离率 < 18% =====
        bias = (price - ma20) / ma20 * 100
        if bias >= 18:
            return None
        
        # ===== 趋势判断：多头排列且MA60向上 =====
        if not (price > ma20 > ma60 > ma120 and ma60 > ma60_last):
            return None
        
        # ===== 综合评分 =====
        vol_sc = min(vr, 8) / 8 * 35
        trend_sc = (ma20 / ma60) * 35
        amp_sc = (12 - min(amp10, 12)) / 12 * 30   # 振幅评分仍参考原12上限
        score = round(vol_sc + trend_sc + amp_sc, 2)
        
        return {
            '名称': name_map.get(code, ''),
            '代码': code,
            '现价': round(price, 2),
            '涨幅%': round(chg, 2),
            '量比': round(vr, 2),
            '10D振幅': round(amp10, 1),
            'MA20': round(ma20, 2),
            '综合评分': score
        }
    except Exception:
        return None

results = []
with ThreadPoolExecutor(max_workers=15) as pool:
    futs = {pool.submit(_screen, c): c for c in codes[:500]}  # 限制数量
    done = 0
    for f in as_completed(futs):
        done += 1
        if done % 50 == 0:
            print(f"  进度 {done}/{len(codes[:500])}")
        r = f.result()
        if r:
            results.append(r)

# ===== 4. 输出结果 =====
print(f"\n[4/4] 汇总结果...")
df = pd.DataFrame(results).sort_values('综合评分', ascending=False) if results else pd.DataFrame()

print("\n" + "=" * 80)
print("✅ 趋势王·创业板精选（参数调整版）")
print(f"初筛剩余：{len(df)} 只")
print("=" * 80)

if len(df) > 0:
    table = tabulate(
        df.values,
        headers=df.columns,
        tablefmt='grid',
        numalign='center',
        stralign='center',
        floatfmt='.2f'
    )
    print(table)
else:
    print("今日无符合条件的创业板标的")

print("\n选股逻辑执行完毕，按回车退出...")
input()