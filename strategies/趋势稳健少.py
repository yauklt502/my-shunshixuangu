# -*- coding: utf-8 -*-
"""
极速精简选股·趋势王【稳健少而精版】—— pytdx 直连版

为什么换掉 mootdx：
  原脚本走 mootdx，而 mootdx 的 ~/.mootdx/config.json 里配置的服务器 IP
  已经全部失效，client.bars() 只会返回空 DataFrame，看起来像"连不上"。
  本版改用 pytdx 直连通达信行情服务器（纯 socket，不受系统代理/v2rayN 影响），
  并在启动时【自动探测一批服务器、挑最快的活服务器】，以后某台再挂也能自动切换。

选股逻辑与原版完全一致：
  初筛：涨幅 2%~5.5%  且  成交额≥1亿  且  振幅≤10%
  核验：现价>MA20>MA60>MA120  且  MA60向上  且 (MA20-MA60)/MA60>1%
  评分：量比40% + 涨幅20% + 趋势强度40%，取综合评分前 5 名
额外增强：量比用真实 K 线计算（当日量 / 前5日均量），比原版固定 1.0 更有意义。
"""
from pytdx.hq import TdxHq_API
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import sys
import time
import os

# 解决终端中文乱码
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# === 数据源统一交给 tdx_source 管理：服务器 IP / 端口 / 测速只此一份 ===
# 桌面那 5 个脚本也共用同一个 tdx_source.py；以后 IP 失效，只改 tdx_source 里的
# CANDIDATE_SERVERS，本脚本与它们都不用再动。
sys.path.insert(0, r'C:\Users\Administrator\Desktop')
import tdx_source
from tdx_source import (
    TDX_PORT,           # 通达信行情端口（固定 7709）
    CANDIDATE_SERVERS,  # 候选服务器池（唯一来源）
    _SERVER,            # 选中的可用服务器（与 tdx_source 共享同一对象）
    _market_of,         # 沪 1 / 深 0
    pick_server,        # 启动测速，挑最快的活服务器
)

MAX_WORKERS = 10

# 线程本地连接
_local = threading.local()


def get_display_width(s):
    """中文计 2，其余计 1"""
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


# 服务器探测逻辑（_port_open / pick_server）已移至 tdx_source，本文件不再保留副本


def get_api():
    """每个线程一个独立连接（pytdx 连接非线程安全）"""
    if getattr(_local, 'api', None) is None:
        api = TdxHq_API(heartbeat=True)
        api.connect(_SERVER['ip'], TDX_PORT, time_out=3)
        _local.api = api
    return _local.api


# _market_of 已改用 tdx_source._market_of（见文件顶部 import）


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
                    continue  # 首页偶发解析失败，跳过继续翻页
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
    """批量取实时行情，pairs=[(market,code),...]，每次最多 80"""
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


def get_ma_data(code):
    """取日线算 MA20/60/120 + 上一日 MA60 + 真实量比"""
    try:
        api = get_api()
        market = _market_of(code)
        # 日线 frequency=9；取 130 根足够算 MA120
        bars = api.get_security_bars(9, market, code, 0, 130)
        if not bars or len(bars) < 120:
            return 0, 0, 0, 0, 1.0
        closes = [b['close'] for b in bars]
        vols = [b['vol'] for b in bars]

        def ma(seq, n, shift=0):
            seg = seq[-(n + shift):len(seq) - shift] if shift else seq[-n:]
            return sum(seg) / n

        ma20 = ma(closes, 20)
        ma60 = ma(closes, 60)
        ma120 = ma(closes, 120)
        ma60_last = ma(closes, 60, shift=1)
        # 真实量比 = 当日量 / 前 5 日均量
        vol_ratio = 1.0
        if len(vols) >= 6:
            prev5 = sum(vols[-6:-1]) / 5
            if prev5 > 0:
                vol_ratio = vols[-1] / prev5
        return ma20, ma60, ma120, ma60_last, vol_ratio
    except Exception:
        return 0, 0, 0, 0, 1.0


def main():
    print("=" * 60)
    print("[*] 极速精简选股·趋势王【稳健少而精版】(pytdx 直连)")
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
    # 多线程分片批量取报价
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
                    'code': code, 'name': board.get(code, code),
                    'price': price, 'pct_chg': pct_chg,
                    'amount': amount, 'amplitude': amplitude,
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

    print("\n[3/4] 多线程核验均线多头...")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(get_ma_data, code): code for code in code_list}
        done = 0
        for future in as_completed(futures):
            done += 1
            if done % 20 == 0:
                print(f"  进度 {done}/{len(code_list)}")
            code = futures[future]
            ma20, ma60, ma120, ma60_last, vol_ratio = future.result()
            if ma20 == 0:
                continue
            row = spot_map[code]
            price = row['price']
            # 均线条件（与原版一致）
            if price > ma20 > ma60 > ma120 and ma60 > ma60_last and (ma20 - ma60) / ma60 > 0.01:
                vol_sc = min(vol_ratio, 5) / 5 * 40
                pct_sc = row['pct_chg'] / 5.5 * 20
                trend_sc = (price / ma20 * 0.5 + ma20 / ma60 * 0.3 + ma60 / ma120 * 0.2)
                trend_sc = min(trend_sc, 1.2) / 1.2 * 40
                total = round(vol_sc + pct_sc + trend_sc, 2)
                res_list.append([
                    row['name'], code, price, round(row['pct_chg'], 2),
                    round(vol_ratio, 2), 0.0, round(ma20, 2), total
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
            row_cells = [
                format_cell(item[0], col_widths[0]),
                format_cell(item[1], col_widths[1]),
                format_cell(f"{item[2]:>.2f}", col_widths[2], 'right'),
                format_cell(f"{item[3]:>.2f}", col_widths[3], 'right'),
                format_cell(f"{item[4]:>.2f}", col_widths[4], 'right'),
                format_cell(f"{item[5]:>.2f}", col_widths[5], 'right'),
                format_cell(f"{item[6]:>.2f}", col_widths[6], 'right'),
                format_cell(f"{item[7]:.2f}", col_widths[7], 'right'),
            ]
            print("| " + " | ".join(row_cells) + " |")
        print(line)
        print("✅ 稳健精选标的已选出（少而精）")
    else:
        print("[i] 当前行情无符合强均线多头的稳健标的。")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
