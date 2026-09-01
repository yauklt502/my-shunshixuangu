import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tdx_source import Quotes
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import threading
import sys
import time
import akshare as ak

# 解决终端显示中文乱码问题
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

MAX_WORKERS = 10

def get_display_width(s):
    """计算字符串在终端显示的实际宽度（中文计2，英文/数字计1）"""
    width = 0
    for char in str(s):
        if '\u4e00' <= char <= '\u9fff':
            width += 2
        else:
            width += 1
    return width

def format_cell(text, width, align='left'):
    """根据实际显示宽度手动填充空格实现对齐"""
    text = str(text)
    actual_w = get_display_width(text)
    space_count = max(0, width - actual_w)
    if align == 'left':
        return text + ' ' * space_count
    else:
        return ' ' * space_count + text

_local = threading.local()

def get_client():
    if not hasattr(_local, 'client'):
        _local.client = Quotes.factory(market='std')
    return _local.client

def get_ma_data_enhanced(code):
    """增强版均线数据获取（含换手率、量比、乖离率、回撤）"""
    try:
        client = get_client()
        kl = client.bars(symbol=code, frequency=9, offset=150, fwd=True)  # 前复权：避免除权跳空污染涨幅/均线
        if kl is None or len(kl) < 120:
            return None
        
        close = kl['close'].astype(float)
        high = kl['high'].astype(float)
        vol = kl['vol'].astype(float)
        
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
        
        # ---- 换手率（优先akshare，失败则估算） ----
        turnover = 0.0
        try:
            df_hist = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
            if len(df_hist) >= 1:
                turnover = float(df_hist['换手率'].iloc[-1])
        except:
            turnover = round(real_vol_ratio * 1.2, 1)
        
        # ---- 30日高点及回撤 ----
        high30 = high.iloc[-30:].max()
        pullback = (high30 - price) / high30 * 100
        
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
    except Exception as e:
        return None

def get_fast_spot():
    """通过 mootdx 获取实时行情初筛（与原版相同）"""
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
    
    print(f"  共 {len(all_df)} 只主板股票，正在获取实时行情...")
    
    codes = all_df['code'].tolist()
    spot_data = []
    
    for i, code in enumerate(codes):
        if i % 100 == 0 and i > 0:
            print(f"  进度 {i}/{len(codes)}")
        
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
            
            if (2 < pct_chg < 5.5 and 
                amount >= 100000000 and 
                amplitude <= 10):
                spot_data.append({
                    'code': code,
                    'name': all_df[all_df['code'] == code]['name'].iloc[0],
                    'price': price,
                    'pct_chg': pct_chg,
                    'amount': amount,
                    'high': high,
                    'low': low,
                    'amplitude': amplitude
                })
        except Exception as e:
            continue
        
        if i % 50 == 0:
            time.sleep(0.05)
    
    print(f"  行情获取完成，初筛 {len(spot_data)} 只")
    return pd.DataFrame(spot_data)

def main():
    print("=" * 60)
    print("🚀 极速精简选股·趋势王【优化增强版】")
    print("=" * 60)
    
    # 连接测试
    try:
        client = Quotes.factory(market='std')
        test_kl = client.bars(symbol='600000', frequency=9, offset=1)
        if test_kl is None or len(test_kl) == 0:
            print("❌ 服务器连接失败，请检查通达信是否开启")
            input("按回车键退出...")
            return
        print("✅ 连接成功")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        input("按回车键退出...")
        return
    
    print("\n[2/4] 获取实时行情并初筛...")
    snapshot = get_fast_spot()
    if snapshot.empty:
        print("💡 当前行情未发现符合初筛条件的个股。")
        input("按回车键退出...")
        return
        
    print(f"\n✅ 初筛剩余：{len(snapshot)} 只，开始深度趋势核验...")

    code_list = snapshot["code"].tolist()
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
            
            row = snapshot[snapshot["code"] == code].iloc[0]
            price = tech['price']
            pct = tech['pct_chg']
            
            # 提取数据
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