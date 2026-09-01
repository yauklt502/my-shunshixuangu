# -*- coding: utf-8 -*-
"""
极速精简选股·趋势王【优化增强版】—— pytdx 直连版
（保留原版所有选股逻辑，仅将数据源从 mootdx 替换为 pytdx 批量并发）
"""
from pytdx.hq import TdxHq_API
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import sys
import time
import os
import pandas as pd
import akshare as ak

# 解决终端中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# === 使用与第一个文件相同的 tdx_source 管理服务器 ===
sys.path.insert(0, r'C:\Users\Administrator\Desktop')
import tdx_source
from tdx_source import (
    TDX_PORT,
    CANDIDATE_SERVERS,
    _SERVER,
    _market_of,
    pick_server,
)

MAX_WORKERS = 10
_local = threading.local()


def get_display_width(s):
    """中文计2，其余计1"""
    width = 0
    for char in str(s):
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width


def format_cell(text, width, align='left'):
    text = str(text)
    space_count = max(0, width - get_display_width(text))
    return (text + ' ' * space_count) if align == 'left' else (' ' * space_count + text)


def get_api():
    """每个线程一个独立连接（pytdx 连接非线程安全）"""
    if getattr(_local, 'api', None) is None:
        api = TdxHq_API(heartbeat=True)
        api.connect(_SERVER['ip'], TDX_PORT, time_out=3)
        _local.api = api
    return _local.api


def get_all_mainboard():
    """拉取沪深主板股票列表（代码+名称），过滤 ST/退"""
    api = TdxHq_API(heartbeat=True)
    api.connect(_SERVER['ip'], TDX_PORT, time_out=5)
    valid_prefix = ('600', '601', '603', '605', '000', '001', '002')
    result = {}
    try:
        for market in (1, 0):  # 1=上海 0=深圳
            cnt = api.get_security_count(market)
            start = 0
            while start < cnt:
                lst = api.get_security_list(market, start)
                start += 1000
                if not lst:
                    continue
                for item in lst:
                    code = str(item['code']).zfill(6)
                    name = item['name']
                    if not code.startswith(valid_prefix):
                        continue
                    if 'ST' in name or '退' in name:
                        continue
                    result[code] = name
    finally:
        api.disconnect()
    return result


def batch_quotes(pairs):
    """批量取实时行情，pairs=[(market,code),...]，每次最多80"""
    api = get_api()
    out = []
    for i in range(0, len(pairs), 80):
        chunk = pairs[i:i + 80]
        try:
            q = api.get_security_quotes(chunk)
            if q:
                out.extend(q)
        except Exception:
            pass
    return out


def get_ma_data_enhanced(code):
    """
    增强版均线数据（保留原第二版全部逻辑）
    使用 pytdx 获取日线，计算 MA5/10/20/60/120、量比、回撤、换手率等
    """
    try:
        api = get_api()
        market = _market_of(code)
        # 取 150 根日线（足够计算 MA120 和 30日高点）
        bars = api.get_security_bars(9, market, code, 0, 150)
        if not bars or len(bars) < 120:
            return None

        # 转换为 pandas Series 便于计算
        close = pd.Series([b['close'] for b in bars], dtype=float)
        high = pd.Series([b['high'] for b in bars], dtype=float)
        vol = pd.Series([b['vol'] for b in bars], dtype=float)

        price = close.iloc[-1]
        pct_chg = (price - close.iloc[-2]) / close.iloc[-2] * 100

        # ---- 涨停风险过滤（涨幅≥9%则放弃） ----
        if pct_chg >= 9.0:
            return None

        # ---- 均线计算 ----
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        ma120 = close.rolling(120).mean().iloc[-1]
        ma60_last = close.rolling(60).mean().iloc[-2]

        # ---- 更严格多头排列：价格 > MA5 > MA10 > MA20 > MA60 > MA120 ----
        if not (price > ma5 > ma10 > ma20 > ma60 > ma120):
            return None

        # ---- MA60向上 ----
        if ma60 <= ma60_last:
            return None

        # ---- 乖离率控制（<15%） ----
        bias_20 = (price - ma20) / ma20 * 100
        if bias_20 > 15:
            return None

        # ---- 真实量比 ----
        vol_today = vol.iloc[-1]
        vol_avg5 = vol.iloc[-6:-1].mean()
        real_vol_ratio = vol_today / vol_avg5 if vol_avg5 > 0 else 1.0

        # ---- 30日高点及回撤 ----
        high30 = high.iloc[-30:].max()
        pullback = (high30 - price) / high30 * 100

        # ---- 换手率（优先akshare，失败则估算，仅在通过所有条件后调用） ----
        turnover = 0.0
        try:
            df_hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if len(df_hist) >= 1:
                turnover = float(df_hist['换手率'].iloc[-1])
        except Exception:
            turnover = round(real_vol_ratio * 1.2, 1)

        # ---- 优化评分体系（满分100） ----
        # 1. 量比分（0-30）：量比≥3得满分
        vol_score = min(real_vol_ratio, 3) / 3 * 30

        # 2. 涨幅分（0-20）：3%-4%最优
        if 3 <= pct_chg <= 4:
            pct_score = 20
        elif 2 <= pct_chg < 3:
            pct_score = 15
        elif 4 < pct_chg <= 5:
            pct_score = 10
        else:
            pct_score = 5

        # 3. 趋势分（0-30）：基于MA5与MA60的偏离度
        spread = (ma5 - ma60) / ma60 * 100
        trend_score = min(spread, 15) / 15 * 30

        # 4. 回撤分（0-20）：回撤越小越好
        pullback_score = max(0, (5 - pullback) / 5 * 20)

        total_score = round(vol_score + pct_score + trend_score + pullback_score, 2)

        return {
            'ma20': ma20,
            'ma60': ma60,
            'ma120': ma120,
            'ma60_last': ma60_last,
            'vol_ratio': real_vol_ratio,
            'turnover': turnover,
            'price': price,
            'pct_chg': pct_chg,
            'pullback': pullback,
            'score': total_score
        }
    except Exception:
        return None


def main():
    print("=" * 60)
    print("🚀 极速精简选股·趋势王【优化增强版】(pytdx 直连)")
    print("=" * 60)

    print("\n[1/4] 探测可用通达信行情服务器...")
    ip = pick_server()
    if not ip:
        print("[X] 未找到可用服务器。请检查网络，或往 CANDIDATE_SERVERS 补充新 IP。")
        input("按回车键退出...")
        return
    _SERVER['ip'] = ip
    print(f"[OK] 已连接最优服务器: {ip}")

    print("\n[2/4] 获取主板股票列表并批量取实时行情初筛...")
    board = get_all_mainboard()
    codes = list(board.keys())
    print(f"  共 {len(codes)} 只主板股票，正在批量获取实时行情...")

    pairs = [(_market_of(c), c) for c in codes]
    snapshot = {}
    chunks = [pairs[i:i + 400] for i in range(0, len(pairs), 400)]
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = [ex.submit(batch_quotes, ck) for ck in chunks]
        for f in as_completed(futs):
            for q in f.result():
                code = str(q['code']).zfill(6)
                snapshot[code] = q

    spot = []
    for code, q in snapshot.items():
        try:
            price = float(q['price'])
            last_close = float(q['last_close'])
            if price <= 0 or last_close <= 0:
                continue
            pct_chg = (price - last_close) / last_close * 100
            amount = float(q['amount'])
            high = float(q['high'])
            low = float(q['low'])
            amplitude = (high - low) / low * 100 if low > 0 else 0
            # 初筛条件（与原版一致）
            if 2 < pct_chg < 5.5 and amount >= 100000000 and amplitude <= 10:
                spot.append({
                    'code': code,
                    'name': board.get(code, code),
                    'price': price,
                    'pct_chg': pct_chg,
                    'amount': amount,
                    'amplitude': amplitude,
                })
        except Exception:
            continue

    print(f"  行情获取完成，初筛 {len(spot)} 只")
    if not spot:
        print("[i] 当前行情未发现符合初筛条件的个股（非交易时段/休市时属正常）。")
        input("按回车键退出...")
        return

    print(f"\n[OK] 初筛剩余：{len(spot)} 只，开始深度趋势核验...")
    code_list = [s['code'] for s in spot]
    spot_map = {s['code']: s for s in spot}
    res_list = []

    print("\n[3/4] 多线程核验均线多头（含换手率、乖离率、回撤）...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_ma_data_enhanced, code): code for code in code_list}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 20 == 0:
                print(f"  进度 {done}/{len(code_list)}")
            code = futures[future]
            tech = future.result()
            if tech is None:
                continue

            row = spot_map[code]
            price = tech['price']
            pct = tech['pct_chg']
            vol_ratio = tech['vol_ratio']
            turnover = tech['turnover']
            ma20 = tech['ma20']
            score = tech['score']

            res_list.append([
                row["name"], code, round(price, 2), round(pct, 2),
                round(vol_ratio, 2), round(turnover, 2), round(ma20, 2), score
            ])

    print("\n[4/4] 汇总结果...")
    if res_list:
        res_list.sort(key=lambda x: x[-1], reverse=True)
        data = res_list[:5]

        col_widths = [12, 10, 8, 8, 8, 8, 8, 12]
        line = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
        headers = ["名称", "代码", "现价", "涨幅%", "量比", "换手率", "MA20", "综合评分"]

        print("\n" + line)
        header_str = "| " + " | ".join([format_cell(headers[i], col_widths[i]) for i in range(len(headers))]) + " |"
        print(header_str)
        print(line)

        for item in data:
            score_val = f"{item[7]:>10.2f}"
            colored_score = f"\033[91m{score_val}\033[0m"
            row_cells = [
                format_cell(item[0], col_widths[0]),
                format_cell(item[1], col_widths[1]),
                format_cell(f"{item[2]:>.2f}", col_widths[2], 'right'),
                format_cell(f"{item[3]:>.2f}", col_widths[3], 'right'),
                format_cell(f"{item[4]:>.2f}", col_widths[4], 'right'),
                format_cell(f"{item[5]:>.2f}", col_widths[5], 'right'),
                format_cell(f"{item[6]:>.2f}", col_widths[6], 'right'),
                " " * (col_widths[7] - 10) + colored_score
            ]
            print("| " + " | ".join(row_cells) + " |")
        print(line)
        print("✅ 优化版精选标的已选出（含换手率、乖离率、回撤控制）")
    else:
        print("💡 当前行情无符合优化条件的稳健标的。")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()