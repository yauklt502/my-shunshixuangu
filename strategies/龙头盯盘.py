# -*- coding: utf-8 -*-
"""
顺势选股 · 龙头盯盘（pytdx 直连版 · 情绪资金总龙头 + 板块龙头）
定义：总龙头 = 市场涨幅领先、成交巨大、连续走强的个股（不限于涨停）
数据源：复用桌面 tdx_source（与趋势王共用服务器）
"""
from __future__ import annotations

import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, r'C:\Users\Administrator\Desktop')
import tdx_source
from tdx_source import TDX_PORT, _SERVER, _market_of, pick_server

from pytdx.hq import TdxHq_API

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# ---------- 线程本地连接 ----------
_local = threading.local()

def get_api():
    if getattr(_local, 'api', None) is None:
        api = TdxHq_API(heartbeat=True)
        api.connect(_SERVER['ip'], TDX_PORT, time_out=3)
        _local.api = api
    return _local.api

# ---------- 数据获取 ----------
def get_all_stocks():
    api = TdxHq_API(heartbeat=True)
    api.connect(_SERVER['ip'], TDX_PORT, time_out=5)
    result = {}
    try:
        for market in (1, 0):
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
                    if 'ST' in name or '退' in name or 'N' in name:
                        continue
                    result[code] = name
    finally:
        api.disconnect()
    return result

def get_industry_map():
    """获取行业分类（股票代码 -> 行业名称），失败则按市场分组"""
    api = TdxHq_API(heartbeat=True)
    api.connect(_SERVER['ip'], TDX_PORT, time_out=5)
    mapping = {}
    try:
        # 尝试行业分类
        industries = api.get_industry_list()
        if industries and len(industries) > 0:
            for ind in industries:
                ind_code = ind.get('code', '')
                ind_name = ind.get('name', '')
                if not ind_code:
                    continue
                stocks = api.get_industry_stock(ind_code)
                for s in stocks:
                    code = str(s['code']).zfill(6)
                    mapping[code] = ind_name
            if mapping:
                print(f"  通过行业接口获取到 {len(mapping)} 条记录")
                return mapping

        # 尝试概念板块（如果存在）
        try:
            plates = api.get_plate_list()
            if plates:
                for pl in plates:
                    pl_code = pl.get('code', '')
                    pl_name = pl.get('name', '')
                    if not pl_code:
                        continue
                    stocks = api.get_plate_stock(pl_code)
                    for s in stocks:
                        code = str(s['code']).zfill(6)
                        mapping[code] = pl_name
                if mapping:
                    print(f"  通过概念板块接口获取到 {len(mapping)} 条记录")
                    return mapping
        except:
            pass

        # 若都失败，按市场分组（备选）
        print("  警告：行业/板块接口失效，将按市场分组（沪/深/创业/科创）")
        return {}
    except Exception as e:
        print(f"  获取行业分类异常: {e}")
        return {}
    finally:
        api.disconnect()

def get_market_group(code):
    if code.startswith(('600','601','603','605')):
        return '沪主板'
    elif code.startswith(('000','001','002')):
        return '深主板'
    elif code.startswith('300'):
        return '创业板'
    elif code.startswith('688'):
        return '科创板'
    else:
        return '其他'

def batch_quotes(pairs):
    api = get_api()
    out = []
    for i in range(0, len(pairs), 80):
        chunk = pairs[i:i+80]
        try:
            q = api.get_security_quotes(chunk)
            if q:
                out.extend(q)
        except:
            pass
    return out

def get_kline(code, count=20):
    try:
        api = get_api()
        market = _market_of(code)
        bars = api.get_security_bars(9, market, code, 0, count)
        return bars if bars else []
    except:
        return []

def calc_consecutive_boards(code):
    bars = get_kline(code, 20)
    if len(bars) < 2:
        return 0
    cnt = 0
    for i in range(len(bars)-2, -1, -1):
        if bars[i+1]['close'] / bars[i]['close'] >= 1.095:
            cnt += 1
        else:
            break
    return cnt

# ---------- 表格工具 ----------
def get_display_width(s):
    width = 0
    for ch in str(s):
        if '\u4e00' <= ch <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def format_cell(text, width, align='left'):
    text = str(text)
    space_count = max(0, width - get_display_width(text))
    if align == 'left':
        return text + ' ' * space_count
    else:
        return ' ' * space_count + text

def format_amount(v):
    if v is None:
        return '--'
    if v >= 1e8:
        return f"{v/1e8:.2f}亿"
    elif v >= 1e4:
        return f"{v/1e4:.0f}万"
    else:
        return f"{v:.0f}"

# ---------- 主程序 ----------
def main():
    print("=" * 70)
    print("[*] 顺势选股 · 龙头盯盘 (pytdx 直连版 · 情绪龙头)")
    print("=" * 70)

    # 服务器探测
    print("[*] 使用 tdx_source 探测服务器...")
    ip = pick_server()
    if not ip:
        print("[X] 无可用服务器。")
        input("按回车退出...")
        return
    _SERVER['ip'] = ip
    print(f"[OK] 已连接：{ip}:{TDX_PORT}")

    # 获取股票列表
    print("\n[1/4] 获取全市场股票列表...")
    stocks = get_all_stocks()
    codes = list(stocks.keys())
    print(f"  共 {len(codes)} 只股票")

    # 获取行业分类
    print("\n[2/4] 获取行业分类...")
    industry_map = get_industry_map()
    # 如果行业映射不完整，补全未分类的为市场分组
    for code in codes:
        if code not in industry_map:
            industry_map[code] = get_market_group(code)
    print(f"  最终分类完成，共 {len(set(industry_map.values()))} 个分组")

    # 批量获取实时行情
    print("\n[3/4] 批量获取实时行情...")
    pairs = [(_market_of(c), c) for c in codes]
    snapshot = {}
    chunks = [pairs[i:i+400] for i in range(0, len(pairs), 400)]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = [ex.submit(batch_quotes, ck) for ck in chunks]
        for f in as_completed(futs):
            for q in f.result():
                code = str(q['code']).zfill(6)
                snapshot[code] = q

    # 构建股票数据列表（包含涨幅、成交额等）
    print("\n[4/4] 分析龙头...")
    stock_data = []
    for code, q in snapshot.items():
        try:
            price = float(q['price'])
            last_close = float(q['last_close'])
            if price <= 0 or last_close <= 0:
                continue
            pct = (price - last_close) / last_close * 100
            amount = float(q['amount'])
            name = stocks.get(code, code)
            # 涨停判断
            if code.startswith(('688','300')):
                is_limit = pct >= 19.0
            else:
                is_limit = pct >= 9.5
            stock_data.append({
                'code': code,
                'name': name,
                'price': price,
                'pct': pct,
                'amount': amount,
                'turnover': float(q.get('turnover', 0)) if q.get('turnover') else 0,
                'is_limit': is_limit,
                'industry': industry_map.get(code, '其他'),
            })
        except:
            continue

    # 筛选强势股作为龙头候选：涨幅>3% 或 成交额>2亿（避免漏掉高成交但涨幅不高的）
    candidates = [s for s in stock_data if s['pct'] > 3.0 or s['amount'] > 2e8]
    if not candidates:
        print("  未找到符合强势条件的个股（可能非交易时段）")
        input("按回车退出...")
        return

    # 为候选股计算连板数（只对涨幅>5%或成交额靠前的计算，节省时间）
    calc_codes = [s['code'] for s in candidates if s['pct'] > 5.0 or s['amount'] > 5e8]
    print(f"  正在估算 {len(calc_codes)} 只股票的连板数...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(calc_consecutive_boards, code): code for code in calc_codes}
        board_map = {}
        for f in as_completed(futs):
            code = futs[f]
            board_map[code] = f.result()
    for s in candidates:
        s['consecutive'] = board_map.get(s['code'], 0)

    # ============ 排序算法 ============
    # 综合得分：涨停优先（+1000），然后连板（每板+100），再涨幅（0~100），再成交额（归一化）
    max_amount = max([s['amount'] for s in candidates]) if candidates else 1
    for s in candidates:
        score = 0
        if s['is_limit']:
            score += 1000
        score += s['consecutive'] * 100
        score += s['pct'] * 2  # 涨幅权重
        score += (s['amount'] / max_amount) * 50  # 成交额权重
        s['score'] = round(score, 2)

    # 按评分降序
    candidates.sort(key=lambda x: x['score'], reverse=True)
    total_leaders = candidates[:3]

    # 按行业分组，每个行业取前三
    industry_groups = {}
    for s in candidates:
        ind = s['industry']
        industry_groups.setdefault(ind, []).append(s)
    industry_leaders = {}
    for ind, items in industry_groups.items():
        items.sort(key=lambda x: x['score'], reverse=True)
        industry_leaders[ind] = items[:3]

    # ============ 输出 ============
    print("\n" + "=" * 70)
    print("【全市场总龙头（情绪资金龙头）】")
    if total_leaders:
        col_widths = [12, 10, 10, 10, 14, 10, 8, 10]
        headers = ["名称", "代码", "涨幅", "现价", "成交额", "换手%", "连板", "评分"]
        line = "+" + "+".join(["-"*(w+2) for w in col_widths]) + "+"
        print(line)
        hdr = "| " + " | ".join([format_cell(h, col_widths[i]) for i,h in enumerate(headers)]) + " |"
        print(hdr)
        print(line)
        ranks = ["总龙头", "龙二", "龙三"]
        for idx, s in enumerate(total_leaders):
            cells = [
                format_cell(s['name'], col_widths[0]),
                format_cell(s['code'], col_widths[1]),
                format_cell(f"{s['pct']:+.2f}%", col_widths[2], 'right'),
                format_cell(f"{s['price']:.2f}", col_widths[3], 'right'),
                format_cell(format_amount(s['amount']), col_widths[4], 'right'),
                format_cell(f"{s['turnover']:.2f}", col_widths[5], 'right'),
                format_cell(str(s.get('consecutive', 0)), col_widths[6], 'right'),
                format_cell(f"{s['score']:.1f}", col_widths[7], 'right'),
            ]
            print("| " + " | ".join(cells) + " |")
        print(line)
    else:
        print("  未找到强势龙头")

    print("\n" + "=" * 70)
    print("【各板块龙头（按评分排序）】")
    # 按板块名称排序
    sorted_industries = sorted(industry_leaders.items(), key=lambda x: x[0])
    for ind, leaders in sorted_industries:
        if not leaders:
            continue
        print(f"\n--- {ind} ---")
        col_widths2 = [12, 12, 10, 10, 14, 10, 8, 10]
        headers2 = ["席位", "名称", "代码", "涨幅", "成交额", "换手%", "连板", "评分"]
        line2 = "+" + "+".join(["-"*(w+2) for w in col_widths2]) + "+"
        print(line2)
        hdr2 = "| " + " | ".join([format_cell(h, col_widths2[i]) for i,h in enumerate(headers2)]) + " |"
        print(hdr2)
        print(line2)
        for idx, s in enumerate(leaders):
            rank = "龙头" if idx==0 else f"龙{['二','三'][idx-1] if idx<3 else str(idx+1)}"
            cells = [
                format_cell(rank, col_widths2[0]),
                format_cell(s['name'], col_widths2[1]),
                format_cell(s['code'], col_widths2[2]),
                format_cell(f"{s['pct']:+.2f}%", col_widths2[3], 'right'),
                format_cell(format_amount(s['amount']), col_widths2[4], 'right'),
                format_cell(f"{s['turnover']:.2f}", col_widths2[5], 'right'),
                format_cell(str(s.get('consecutive', 0)), col_widths2[6], 'right'),
                format_cell(f"{s['score']:.1f}", col_widths2[7], 'right'),
            ]
            print("| " + " | ".join(cells) + " |")
        print(line2)

    print("\n提示：评分算法 = 涨停奖励 + 连板×100 + 涨幅×2 + 成交额归一化×50")
    input("\n按回车键退出...")

if __name__ == "__main__":
    main()