# ============================================================
#  妖龙 · 机构趋势推进系统（终极优化版）
#
#  核心：
#  1. 主板
#  2. 非ST
#  3. 情绪妖龙
#  4. 机构趋势妖龙
#  5. 大资金持续推进
#  6. 高成交额容量核心
#  7. 缩量新高
#
#  特点：
#  ✔ 过滤低级套利板
#  ✔ 过滤一字骗炮
#  ✔ 过滤脉冲冲顶
#  ✔ 专抓高质量趋势妖龙
#
#  适合：
#  龙头
#  趋势
#  波段
#  超短核心
# ============================================================

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdx_source import Quotes
from concurrent.futures import ThreadPoolExecutor, as_completed
from tabulate import tabulate
from tqdm import tqdm

import pandas as pd
import threading
import warnings
import time
from datetime import datetime

warnings.filterwarnings("ignore")

# ============================================================
# 参数
# ============================================================

MAX_WORKERS = 8
DELAY = 0.01

# ============================================================
# 启动
# ============================================================

print("=" * 140)
print("🔥 妖龙 · 机构趋势推进系统（终极优化版）")
print("=" * 140)

# ============================================================
# 连接服务器
# ============================================================

client = Quotes.factory(market='std')

try:

    test = client.bars(
        symbol='600000',
        frequency=9,
        offset=10
    )

    if test is None or len(test) == 0:
        raise Exception("连接失败")

    print("✅ 通达信连接成功")

except Exception as e:

    print(f"❌ 连接失败: {e}")

    input("\n按回车退出...")
    exit()

# ============================================================
# 获取股票池
# ============================================================

print("\n[1/5] 获取主板股票池...")

sh = client.stocks(market=1)
sz = client.stocks(market=0)

all_df = pd.concat([sh, sz], ignore_index=True)

all_df['code'] = all_df['code'].astype(str).str.zfill(6)

VALID_PREFIX = (
    '600',
    '601',
    '603',
    '605',
    '000',
    '001'
)

a_df = all_df[
    all_df['code'].str.startswith(VALID_PREFIX) &
    (
        ~all_df['name'].str.contains(
            'ST|\\*ST|退|退市|整理|风险',
            na=False
        )
    )
].copy()

codes = a_df['code'].tolist()

name_map = dict(zip(a_df['code'], a_df['name']))

print(f"✅ 股票池数量: {len(codes)}")

# ============================================================
# 多线程客户端
# ============================================================

_local = threading.local()

def get_client():

    if not hasattr(_local, 'cli'):
        _local.cli = Quotes.factory(market='std')

    return _local.cli

# ============================================================
# 核心逻辑
# ============================================================

# ============================================================
# 分关卡诊断（看清 0 只是真没票还是异常被吞）
# ============================================================
_stage_lock = threading.Lock()
stage_counts = {}

def _reject(stage):
    with _stage_lock:
        stage_counts[stage] = stage_counts.get(stage, 0) + 1
    return None


def screen(code):

    try:

        time.sleep(DELAY)

        c = get_client()

        kl = c.bars(
            symbol=code,
            frequency=9,
            offset=150,
            fwd=True          # 前复权：避免除权跳空污染涨幅/连板/阳线统计
        )

        if kl is None or len(kl) < 100:
            return _reject('数据不足')

        close = kl['close'].astype(float)
        high = kl['high'].astype(float)
        low = kl['low'].astype(float)
        vol = kl['vol'].astype(float)

        price = close.iloc[-1]

        # ====================================================
        # 均线
        # ====================================================

        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()

        ma5_now = ma5.iloc[-1]
        ma10_now = ma10.iloc[-1]
        ma20_now = ma20.iloc[-1]
        ma60_now = ma60.iloc[-1]

        # ====================================================
        # 超强多头排列
        # ====================================================

        if not (
            ma5_now >
            ma10_now >
            ma20_now >
            ma60_now
        ):
            return _reject('MA多头')

        # ====================================================
        # 均线持续攻击
        # ====================================================

        if ma5.iloc[-1] <= ma5.iloc[-3]:
            return _reject('MA5攻击')

        if ma10.iloc[-1] <= ma10.iloc[-3]:
            return _reject('MA10攻击')

        if ma20.iloc[-1] <= ma20.iloc[-5]:
            return _reject('MA20攻击')

        # ====================================================
        # 必须沿MA5推进
        # ====================================================

        if price < ma5_now:
            return _reject('沿MA5')

        # ====================================================
        # 5日涨幅
        # ====================================================

        rise5 = (
            (close.iloc[-1] - close.iloc[-6])
            / close.iloc[-6]
            * 100
        )

        if rise5 < 12:
            return _reject('5日涨幅')

        # ====================================================
        # 10日涨幅
        # ====================================================

        rise10 = (
            (close.iloc[-1] - close.iloc[-11])
            / close.iloc[-11]
            * 100
        )

        if rise10 < 20:
            return _reject('10日涨幅')

        # ====================================================
        # 今日涨幅
        # ====================================================

        pct_now = (
            (close.iloc[-1] - close.iloc[-2])
            / close.iloc[-2]
            * 100
        )

        if pct_now < 2:
            return _reject('今日涨幅')

        # ====================================================
        # 量比
        # ====================================================

        vol_today = vol.iloc[-1]
        vol_avg5 = vol.iloc[-6:-1].mean()

        if vol_avg5 <= 0:
            return _reject('量比为0')

        vr = vol_today / vol_avg5

        if vr < 1.0:
            return _reject('量比低')

        if vr > 8:          # 放宽量比上限（原4.5过严，与"温和放量"矛盾）
            return _reject('量比高')

        # ====================================================
        # 大资金容量过滤
        # ====================================================

        amount = price * vol_today * 100

        # 至少8亿成交额
        if amount < 800000000:
            return _reject('成交额')

        # ====================================================
        # 10日上涨天数
        # ====================================================

        up10 = 0

        for i in range(-10, 0):

            if close.iloc[i] > close.iloc[i-1]:
                up10 += 1

        if up10 < 7:
            return _reject('10日阳线')

        # ====================================================
        # 连板统计
        # ====================================================

        limit_up = 0

        for i in range(-6, 0):

            zf = (
                (close.iloc[i] - close.iloc[i-1])
                / close.iloc[i-1]
                * 100
            )

            if zf >= 9.5:
                limit_up += 1

        # ====================================================
        # 次要关卡：爆量 / 近新高 / 回撤 / 波动
        # 说明：核心趋势结构（MA排列+攻击+涨幅+量比+成交额+阳线）已通过的票，
        #       若只卡在以下"次要"关，归入「近失候选」供人工观察，不再直接淘汰为 0。
        # ====================================================

        secondary_fails = []

        # 缩量新高（防止爆量见顶）
        vol3_now = vol.iloc[-3:].mean()
        vol3_old = vol.iloc[-6:-3].mean()
        if vol_avg5 > 0 and vol3_now > vol3_old * 2.0:   # 放宽爆量阈值（原1.2过严）
            secondary_fails.append('爆量')

        # 新高附近
        high30 = high.iloc[-30:].max()

        if price < high30 * 0.97:
            secondary_fails.append('近新高')

        # ====================================================
        # 回撤
        # ====================================================

        pullback = (
            (high30 - price)
            / high30
            * 100
        )

        if pullback > 5:
            secondary_fails.append('回撤')

        # ====================================================
        # 波动
        # ====================================================

        amp10 = (
            (
                high.iloc[-10:] -
                low.iloc[-10:]
            )
            / close.iloc[-10:]
        ).mean() * 100

        if amp10 > 12:
            secondary_fails.append('波动')

        # ====================================================
        # 趋势发散
        # ====================================================

        spread = (
            (ma5_now - ma20_now)
            / ma20_now
            * 100
        )

        # ====================================================
        # 妖龙评分
        # ====================================================

        score = 0

        score += rise5 * 3
        score += rise10 * 2
        score += pct_now * 5
        score += vr * 20
        score += spread * 8
        score += limit_up * 25
        score += up10 * 10
        score += (5 - pullback) * 10

        if secondary_fails:
            with _stage_lock:
                stage_counts['近失候选'] = stage_counts.get('近失候选', 0) + 1
            return {
                '候选类型': '近失',
                '未过': ','.join(secondary_fails),
                '名称': name_map.get(code, ''),
                '代码': code,
                '现价': round(price, 2),
                '今日涨幅%': round(pct_now, 2),
                '5日涨幅%': round(rise5, 2),
                '10日涨幅%': round(rise10, 2),
                '量比': round(vr, 2),
                '10日阳线': up10,
                '连板数': limit_up,
                '成交额(亿)': round(amount / 100000000, 2),
                '回撤%': round(pullback, 2),
                '妖龙评分': round(score, 2)
            }

        with _stage_lock:
            stage_counts['通过'] = stage_counts.get('通过', 0) + 1

        return {

            '候选类型': '正式',
            '未过': '',
            '名称': name_map.get(code, ''),
            '代码': code,
            '现价': round(price, 2),
            '今日涨幅%': round(pct_now, 2),
            '5日涨幅%': round(rise5, 2),
            '10日涨幅%': round(rise10, 2),
            '量比': round(vr, 2),
            '10日阳线': up10,
            '连板数': limit_up,
            '成交额(亿)': round(amount / 100000000, 2),
            '回撤%': round(pullback, 2),
            '妖龙评分': round(score, 2)

        }

    except Exception:

        return _reject('异常')

# ============================================================
# 开始扫描
# ============================================================

print(f"\n[2/5] 开始扫描妖龙股（{MAX_WORKERS}线程）...")

results = []
near_miss = []

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:

    futures = [
        pool.submit(screen, code)
        for code in codes
    ]

    for f in tqdm(
        as_completed(futures),
        total=len(futures),
        ncols=100,
        desc="扫描进度"
    ):

        r = f.result()

        if r:
            if r.get('候选类型') == '近失':
                near_miss.append(r)
            else:
                results.append(r)

# ============================================================
# 输出结果
# ============================================================

# ============================================================
# 诊断：分关卡淘汰统计
# ============================================================
print("\n[诊断] 各关卡淘汰数量（看清 0 只是真没票还是脚本异常）：")
_diag_order = ['通过', '近失候选', '异常', '数据不足', 'MA多头', 'MA5攻击', 'MA10攻击',
               'MA20攻击', '沿MA5', '5日涨幅', '10日涨幅', '今日涨幅', '量比低',
               '量比高', '量比为0', '成交额', '10日阳线', '爆量', '近新高',
               '回撤', '波动']
for _k in _diag_order:
    if _k in stage_counts:
        print(f"  {_k:<8}: {stage_counts[_k]}")
if stage_counts.get('异常', 0) > 0:
    print("  ⚠️ '异常' > 0：有股票在取数/计算时抛错被吞，0 只可能是假象，需排查数据源。")

print("\n" + "=" * 140)
print("🔥 妖龙 · 机构趋势推进结果（终极优化版）")
print("=" * 140)

df = pd.DataFrame(results)
df = df.sort_values(by='妖龙评分', ascending=False) if not df.empty else df

# 去掉内部标记列，保持原表风格（schema 取自实际有数据的表，避免空表时丢列）
_display_base = ['名称', '代码', '现价', '今日涨幅%', '5日涨幅%', '10日涨幅%',
                '量比', '10日阳线', '连板数', '成交额(亿)', '回撤%', '妖龙评分']
_schema_src = df if not df.empty else (pd.DataFrame(near_miss) if near_miss else df)
_disp_cols = [c for c in _display_base if c in _schema_src.columns]

if len(results) == 0:

    print("❌ 今日无「全条件通过」妖龙")

else:

    _show = df[_disp_cols] if _disp_cols else df
    table = tabulate(
        _show.values,
        headers=_show.columns,
        tablefmt='grid',
        numalign='center',
        stralign='center',
        floatfmt='.2f'
    )

    print(table)

    print(f"\n✅ 共筛选出 {len(df)} 只高质量妖龙股")

# ============================================================
# 近失候选（准妖龙）观察池：核心结构已过，仅次要关未过
# ============================================================
if near_miss:

    _nd = pd.DataFrame(near_miss).sort_values(by='妖龙评分', ascending=False).head(10)
    _nd_cols = [c for c in _disp_cols + ['未过'] if c in _nd.columns]

    _ntable = tabulate(
        _nd[_nd_cols].values if _nd_cols else _nd.values,
        headers=_nd_cols if _nd_cols else _nd.columns,
        tablefmt='grid',
        numalign='center',
        stralign='center',
        floatfmt='.2f'
    )

    print("\n" + "-" * 140)
    print("📌 近失候选（准妖龙）：核心趋势结构已通过，仅次要条件未过，供人工观察")
    print("-" * 140)
    print(_ntable)
    print(f"\n🔎 共 {len(near_miss)} 只近失候选，已展示评分 Top 10")

# ============================================================
# 功能菜单
# ============================================================

while True:

    print("\n" + "=" * 60)
    print("📌 交易终端功能菜单")
    print("=" * 60)

    print("1 = 导出Excel")
    print("2 = 导出TXT")
    print("3 = 导出自选股")
    print("4 = 导出通达信板块")
    print("5 = 加入观察池")
    print("6 = 自动生成第二天计划")
    print("0 = 退出系统")

    choice = input("\n请输入功能编号：")

    # Excel
    if choice == "1":

        file_name = "高质量妖龙结果.xlsx"

        df.to_excel(
            file_name,
            index=False
        )

        print(f"\n📁 已导出：{file_name}")

    # TXT
    elif choice == "2":

        file_name = "高质量妖龙结果.txt"

        with open(
            file_name,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(table)

        print(f"\n📁 已导出：{file_name}")

    # 自选股
    elif choice == "3":

        file_name = "妖龙自选股.txt"

        with open(
            file_name,
            "w",
            encoding="utf-8"
        ) as f:

            for code in df['代码']:

                if code.startswith('6'):
                    f.write(f"1{code}\n")
                else:
                    f.write(f"0{code}\n")

        print(f"\n📁 已导出通达信自选股：{file_name}")

    # 板块
    elif choice == "4":

        file_name = "妖龙板块.blk"

        with open(
            file_name,
            "w",
            encoding="utf-8"
        ) as f:

            for code in df['代码']:
                f.write(f"{code}\n")

        print(f"\n📁 已导出通达信板块：{file_name}")

    # 观察池
    elif choice == "5":

        file_name = "妖龙观察池.txt"

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(
            file_name,
            "a",
            encoding="utf-8"
        ) as f:

            f.write(f"\n\n========== {now} ==========\n")

            for _, row in df.iterrows():

                f.write(
                    f"{row['代码']} "
                    f"{row['名称']} "
                    f"评分:{row['妖龙评分']}\n"
                )

        print(f"\n📁 已加入观察池：{file_name}")

    # 第二天计划
    elif choice == "6":

        file_name = "妖龙第二天计划.txt"

        with open(
            file_name,
            "w",
            encoding="utf-8"
        ) as f:

            f.write("=" * 60 + "\n")
            f.write("妖龙第二天交易计划\n")
            f.write("=" * 60 + "\n\n")

            for i, row in df.head(10).iterrows():

                f.write(
                    f"{i+1}. "
                    f"{row['名称']} "
                    f"{row['代码']}\n"
                )

                f.write(
                    f"   妖龙评分: {row['妖龙评分']}\n"
                )

                f.write(
                    f"   成交额: {row['成交额(亿)']}亿\n"
                )

                f.write(
                    f"   连板数: {row['连板数']}\n"
                )

                f.write(
                    f"   重点观察:\n"
                )

                f.write(
                    f"   ① 是否继续缩量新高\n"
                )

                f.write(
                    f"   ② 是否继续沿MA5推进\n"
                )

                f.write(
                    f"   ③ 是否继续资金流入\n\n"
                )

        print(f"\n📁 已生成：{file_name}")

    # 退出
    elif choice == "0":

        print("\n系统退出")

        break

    else:

        print("\n❌ 输入错误")