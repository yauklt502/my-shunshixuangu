import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdx_source import Quotes
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import threading
from tabulate import tabulate
from datetime import datetime

print("=" * 80)
print("  趋势王·创业板精选（深度思考放宽版）")
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

# ===== 2. 获取创业板列表 =====
print("\n[2/4] 获取创业板列表...")
sh = client.stocks(market=1)
sz = client.stocks(market=0)
all_df = pd.concat([sh, sz], ignore_index=True)
all_df['code'] = all_df['code'].astype(str).str.zfill(6)

cyb_df = all_df[
    all_df['code'].str.startswith('300') &
    (~all_df['name'].str.contains('ST|退', na=False))
].copy()
name_map = dict(zip(cyb_df['code'], cyb_df['name']))
codes = cyb_df['code'].tolist()
print(f"✅ 创业板标的: {len(codes)} 只")

# ===== 3. 多线程筛选（放宽参数） =====
print(f"\n[3/4] 多线程核验 {min(500, len(codes))} 只标的（15线程）...")

_local = threading.local()
stats_lock = threading.Lock()

cond_stats = {
    'total': 0, 'data_ok': 0,
    'chg': 0, 'vol_ratio': 0,
    'align': 0, 'ma60_up': 0,
    'amp10': 0, 'bias': 0,
}

def _connect():
    if not hasattr(_local, 'cli'):
        _local.cli = Quotes.factory(market='std')
    return _local.cli

def _screen(code):
    flags = {
        'data_ok': False,
        'chg': False,
        'vol_ratio': False,
        'align': False,
        'ma60_up': False,
        'amp10': False,
        'bias': False,
    }
    try:
        c = _connect()
        kl = c.bars(symbol=code, frequency=9, offset=130, fwd=True)  # 前复权：避免除权跳空污染涨幅/均线
        if kl is None or len(kl) < 60:
            return None, flags

        price = float(kl['close'].iloc[-1])
        yclose = float(kl['close'].iloc[-2])
        if yclose <= 0:
            return None, flags

        flags['data_ok'] = True

        # ---- 参数放宽：涨幅3%-12% ----
        chg = (price - yclose) / yclose * 100
        flags['chg'] = (3 <= chg <= 12)

        # 量比 ≥ 1.3（原2.0）
        vol_today = float(kl['vol'].iloc[-1])
        vol_avg5 = float(kl['vol'].iloc[-6:-1].mean())
        if vol_avg5 <= 0:
            return None, flags
        vr = vol_today / vol_avg5
        flags['vol_ratio'] = (vr >= 1.5)

        # 均线系统
        close_arr = kl['close'].astype(float)
        ma20 = close_arr.rolling(20).mean().iloc[-1]
        ma60 = close_arr.rolling(60).mean().iloc[-1]
        ma120 = close_arr.rolling(120).mean().iloc[-1] if len(close_arr) >= 120 else ma60
        ma60_last = close_arr.rolling(60).mean().iloc[-2]
        flags['align'] = (price > ma20 > ma60 > ma120)
        flags['ma60_up'] = (ma60 > ma60_last)

        # 10日平均振幅
        high_arr = kl['high'].astype(float)
        low_arr = kl['low'].astype(float)
        amp10 = ((high_arr - low_arr) / low_arr * 100).tail(10).mean()
        flags['amp10'] = (amp10 < 12)

        # 乖离率
        bias = (price - ma20) / ma20 * 100
        flags['bias'] = (bias < 18)

        if not all(flags[k] for k in ['chg','vol_ratio','align','ma60_up','amp10','bias']):
            return None, flags

        # 综合评分
        vol_sc = min(vr, 8) / 8 * 35
        trend_sc = (ma20 / ma60) * 35
        amp_sc = (12 - amp10) / 12 * 30
        score = round(vol_sc + trend_sc + amp_sc, 2)

        result = {
            '名称': name_map.get(code, ''),
            '代码': code,
            '现价': round(price, 2),
            '涨幅%': round(chg, 2),
            '量比': round(vr, 2),
            '10D振幅': round(amp10, 1),
            'MA20': round(ma20, 2),
            '综合评分': score
        }
        return result, flags
    except Exception:
        return None, flags

results = []
sample_codes = codes[:500]

with ThreadPoolExecutor(max_workers=15) as pool:
    futs = {pool.submit(_screen, c): c for c in sample_codes}
    done = 0
    for f in as_completed(futs):
        done += 1
        if done % 50 == 0:
            print(f"  进度 {done}/{len(sample_codes)}")
        res, flags = f.result()
        with stats_lock:
            cond_stats['total'] += 1
            if flags['data_ok']:
                cond_stats['data_ok'] += 1
                if flags['chg']: cond_stats['chg'] += 1
                if flags['vol_ratio']: cond_stats['vol_ratio'] += 1
                if flags['align']: cond_stats['align'] += 1
                if flags['ma60_up']: cond_stats['ma60_up'] += 1
                if flags['amp10']: cond_stats['amp10'] += 1
                if flags['bias']: cond_stats['bias'] += 1
        if res is not None:
            results.append(res)

# ===== 4. 输出结果 =====
print(f"\n[4/4] 汇总结果...")
df = pd.DataFrame(results).sort_values('综合评分', ascending=False) if results else pd.DataFrame()

print("\n" + "=" * 80)
print("✅ 趋势王·创业板精选（放宽版）")
print(f"📅 选股日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    print("今日无符合条件的创业板标的（可进一步降低涨幅下限至2%或量比至1.3）")

print("\n📋 各条件通过数（总处理{}只，K线有效{}只）：".format(cond_stats['total'], cond_stats['data_ok']))
print(f"  涨幅3-12%     : {cond_stats['chg']}")
print(f"  量比≥1.5      : {cond_stats['vol_ratio']}")
print(f"  多头排列      : {cond_stats['align']}")
print(f"  MA60上行      : {cond_stats['ma60_up']}")
print(f"  10日振幅<12%  : {cond_stats['amp10']}")
print(f"  乖离率<18%    : {cond_stats['bias']}")

print("\n选股逻辑执行完毕，按回车退出...")
input()