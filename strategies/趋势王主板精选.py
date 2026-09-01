import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdx_source import Quotes
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import threading
import sys
import time
import akshare as ak
import math
from datetime import datetime  # 新增

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ==================== 全局配置 ====================
MAX_WORKERS = 12
MAX_STOCKS = 800
INIT_FILTER = {
    'pct_low': 2.0,
    'pct_high': 5.5,
    'amount_min': 1e8,
    'amplitude_max': 10.0,
}
TREND_COND = {
    'ma20_ma60_ratio': 0.01,
    'ma60_up': True,
    'price_above_ma20': True,
}
SCORE_WEIGHTS = {
    'vol_ratio': 40,
    'pct': 20,
    'trend': 40,
}

_local = threading.local()

def get_client():
    if not hasattr(_local, 'client'):
        _local.client = Quotes.factory(market='std')
    return _local.client

def get_display_width(s):
    width = 0
    for char in str(s):
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def format_cell(text, width, align='left'):
    text = str(text)
    actual_w = get_display_width(text)
    space_count = max(0, width - actual_w)
    if align == 'left':
        return text + ' ' * space_count
    else:
        return ' ' * space_count + text

def get_ma_and_vol(code, days=130):
    try:
        client = get_client()
        kl = client.bars(symbol=code, frequency=9, offset=days, fwd=True)  # 前复权：避免除权跳空污染涨幅/均线
        if kl is None or len(kl) < 60:
            return None
        close = kl['close'].astype(float)
        vol = kl['vol'].astype(float)

        ma5 = close.rolling(5).mean()
        ma10 = close.rolling(10).mean()
        ma20 = close.rolling(20).mean()
        ma60 = close.rolling(60).mean()
        ma120 = close.rolling(120).mean() if len(close) >= 120 else ma60
        ma60_last = close.rolling(60).mean().iloc[-2] if len(close) >= 62 else ma60

        ma5_today = ma5.iloc[-1]
        ma5_yest = ma5.iloc[-2] if len(ma5) >= 2 else ma5_today
        ma10_today = ma10.iloc[-1]
        ma10_yest = ma10.iloc[-2] if len(ma10) >= 2 else ma10_today

        def calc_angle(today, yest):
            if yest > 0 and not math.isnan(today) and not math.isnan(yest):
                pct_change = (today / yest - 1) * 100
                rad = math.atan(pct_change)
                angle = rad * 180 / math.pi
                return angle
            return -999

        ma5_angle = calc_angle(ma5_today, ma5_yest)
        ma10_angle = calc_angle(ma10_today, ma10_yest)

        vol_today = vol.iloc[-1]
        vol_avg5 = vol.iloc[-6:-1].mean()
        vol_ratio = vol_today / vol_avg5 if vol_avg5 > 0 else 1.0

        turnover = 0.0
        try:
            df_hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if len(df_hist) >= 1:
                turnover = float(df_hist['换手率'].iloc[-1])
        except:
            turnover = round(vol_ratio * 1.2, 1)

        return {
            'ma20': ma20.iloc[-1],
            'ma60': ma60.iloc[-1],
            'ma120': ma120.iloc[-1],
            'ma60_last': ma60_last,
            'vol_ratio': vol_ratio,
            'turnover': turnover,
            'price': close.iloc[-1],
            'ma5_angle': ma5_angle,
            'ma10_angle': ma10_angle,
        }
    except Exception:
        return None

def get_fast_spot():
    client = Quotes.factory(market='std')
    sh = client.stocks(market=1)
    sz = client.stocks(market=0)
    all_df = pd.concat([sh, sz], ignore_index=True)
    all_df['code'] = all_df['code'].astype(str).str.zfill(6)
    valid_prefix = ('600', '601', '603', '605', '000', '001', '002')
    all_df = all_df[
        all_df['code'].str.startswith(valid_prefix) &
        (~all_df['name'].str.contains('ST|退', na=False))
    ].copy()
    codes = all_df['code'].tolist()
    print(f"📡 主板股票总数: {len(codes)}，将检查前{min(MAX_STOCKS, len(codes))}只")

    spot_data = []
    for idx, code in enumerate(codes[:MAX_STOCKS]):
        if idx % 100 == 0 and idx > 0:
            print(f"  实时行情进度: {idx}/{len(codes[:MAX_STOCKS])}")
        try:
            quote = client.quotes(symbol=code)
            if quote is None or quote.empty:
                continue
            q = quote.iloc[0]
            price = float(q['price'])
            if price <= 0:
                continue
            last_close = float(q['last_close'])
            if last_close <= 0:
                continue
            pct_chg = (price - last_close) / last_close * 100
            amount = float(q['amount'])
            high = float(q['high'])
            low = float(q['low'])
            amplitude = (high - low) / low * 100 if low > 0 else 0

            if (INIT_FILTER['pct_low'] < pct_chg < INIT_FILTER['pct_high'] and
                amount >= INIT_FILTER['amount_min'] and
                amplitude <= INIT_FILTER['amplitude_max']):
                spot_data.append({
                    'code': code,
                    'name': all_df[all_df['code'] == code]['name'].iloc[0],
                    'price': price,
                    'pct_chg': pct_chg,
                    'amount': amount,
                })
        except:
            continue
        time.sleep(0.01)
    print(f"✅ 初筛剩余: {len(spot_data)} 只")
    return pd.DataFrame(spot_data)

def main():
    print("=" * 70)
    print("  趋势王·主板精选 (优化版) | 均线多头 + 放量突破 + 均线角度>35°")
    print("=" * 70)

    try:
        client = Quotes.factory(market='std')
        test_kl = client.bars(symbol='600000', frequency=9, offset=1)
        if test_kl is None or len(test_kl) == 0:
            print("❌ 通达信连接失败，请检查软件是否开启")
            input("按回车退出...")
            return
        print("✅ 行情服务器连接成功")
    except Exception as e:
        print(f"❌ 连接异常: {e}")
        input("按回车退出...")
        return

    snapshot = get_fast_spot()
    if snapshot.empty:
        print("💡 无符合初筛条件的个股 (涨幅、成交额、振幅条件可能过严)")
        input("按回车退出...")
        return

    print(f"\n📊 初筛 {len(snapshot)} 只，正在进行均线多头及角度核验...")
    code_list = snapshot['code'].tolist()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_code = {executor.submit(get_ma_and_vol, code): code for code in code_list}
        done = 0
        for future in as_completed(future_to_code):
            done += 1
            if done % 10 == 0:
                print(f"  均线核验进度: {done}/{len(code_list)}")
            code = future_to_code[future]
            tech = future.result()
            if tech is None:
                continue

            row = snapshot[snapshot['code'] == code].iloc[0]
            price = row['price']

            cond1 = price > tech['ma20'] > tech['ma60'] > tech['ma120']
            cond2 = tech['ma60'] > tech['ma60_last']
            cond3 = (tech['ma20'] - tech['ma60']) / tech['ma60'] > TREND_COND['ma20_ma60_ratio']
            cond4 = tech['ma5_angle'] > 35 and tech['ma10_angle'] > 35

            if not (cond1 and cond2 and cond3 and cond4):
                continue

            vol_ratio = min(tech['vol_ratio'], 8)
            vol_score = (vol_ratio / 8) * SCORE_WEIGHTS['vol_ratio']
            pct_score = (row['pct_chg'] / INIT_FILTER['pct_high']) * SCORE_WEIGHTS['pct']
            trend_score = min(price / tech['ma20'], 1.2) / 1.2 * SCORE_WEIGHTS['trend']
            total_score = round(vol_score + pct_score + trend_score, 2)

            results.append([
                row['name'], code, round(price, 2), round(row['pct_chg'], 2),
                round(tech['vol_ratio'], 2), round(tech['turnover'], 2),
                round(tech['ma20'], 2), total_score
            ])

    if not results:
        print("💡 当前无符合条件（均线多头 + 5/10日线角度>35°）的标的")
        input("按回车退出...")
        return

    results.sort(key=lambda x: x[-1], reverse=True)
    top_data = results[:5]

    # 在表格上方显示日期
    print(f"\n📅 选股日期：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 打印表格
    col_widths = [12, 10, 8, 8, 8, 8, 8, 12]
    sep_line = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
    headers = ["名称", "代码", "现价", "涨幅%", "量比", "换手率", "MA20", "综合评分"]

    print("\n" + sep_line)
    print("| " + " | ".join([format_cell(headers[i], col_widths[i]) for i in range(8)]) + " |")
    print(sep_line)
    for item in top_data:
        name, code, price, pct, vol_ratio, turnover, ma20, score = item
        row_cells = [
            format_cell(name, col_widths[0]),
            format_cell(code, col_widths[1]),
            format_cell(f"{price:.2f}", col_widths[2], 'right'),
            format_cell(f"{pct:.2f}", col_widths[3], 'right'),
            format_cell(f"{vol_ratio:.2f}", col_widths[4], 'right'),
            format_cell(f"{turnover:.1f}", col_widths[5], 'right'),
            format_cell(f"{ma20:.2f}", col_widths[6], 'right'),
            " " * (col_widths[7] - 8) + f"\033[91m{score:>8.2f}\033[0m"
        ]
        print("| " + " | ".join(row_cells) + " |")
    print(sep_line)
    print("\n✅ 选股完成，以上为综合评分最高的5只标的\n")
    input("按回车键退出...")

if __name__ == "__main__":
    main()