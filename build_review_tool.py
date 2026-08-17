#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A-Share Short-Term Speculation Review Tool Single-File HTML Builder
Generates a complete, offline-capable, standalone HTML review tool.
Includes authentic historical market data and non-trading days.
"""

import json
import os

# Historical sample days: verified public closes (see authentic_days.py)
from authentic_days import AUTHENTIC_DAYS

MARKET_DATABASE = dict(AUTHENTIC_DAYS)
MARKET_DATABASE.update({
    "2026-08-14": {
        "is_trading_day": True,
        "date": "2026-08-14",
        "date_cn": "2026年08月14日 星期五",
        "data_source": "公开行情：上交所/深交所收盘统计、财联社涨停复盘、证券时报·数据宝、交易所龙虎榜营业部公开信息、爱股网日K。统计口径截至2026-08-14收盘。",
        "market_summary": {
            "sh_index": 3927.18,
            "sh_change": 0.01,
            "sz_index": 14354.31,
            "sz_change": 0.45,
            "cy_index": 3626.30,
            "cy_change": 1.12,
            "total_turnover": 21429,  # 沪9904 + 深11525 = 21429 亿元
            "turnover_change": -4081,
            "up_count": 2400,
            "down_count": 2970,
            "flat_count": 162,
            "median_change": -0.38,
            "limit_up_count": 63,
            "limit_down_count": 13,
            "broken_board_count": 19,
            "consecutive_board_count": 19,
            "broken_board_rate": 23.17,  # 19/(63+19)
            "promotion_rate_1_to_2": 27.27,
            "promotion_rate_2_to_3": 27.27,
            "promotion_rate_high": 16.67,
            "max_height": 5,
            "max_height_stock": "蓝盾光电 (300862) 20cm 5连板",
            "sentiment_phase": "分歧期",
            "sentiment_phase_en": "Divergence",
            "sentiment_score": 44,
            "cash_defense_score": 36,
            "suggested_position": "2~4成 (高低切防守试错)",
            "core_themes": ["CPO/光通信散热", "算力租赁/CDN", "光纤光缆", "并购重组", "医药零售轮动"]
        },
        "absolute_high": {
            "title": "老高度板秦安股份跌停核按钮，蓝盾光电20cm五连板成为新高度；京投发展天地板",
            "leader_code": "300862",
            "leader_name": "蓝盾光电",
            "concept": "重大资产重组 / 光通信光学薄膜设备 / 拟收购岚创科技",
            "consecutive_boards": 5,
            "close_price": 47.29,
            "change_percent": 19.99,
            "turnover": 34.95,
            "turnover_rate": 51.69,
            "seal_status": "打开一字后换手回封，20cm 5连板",
            "intraday_behavior": "早盘打开一字板，最低下探41.46元，随后获资金承接回封47.29元涨停。全天换手51.69%、成交34.95亿元，振幅14.79%。8月10日复牌以来累计涨幅约148.76%。催化为8月7日重组预案：拟发行股份及支付现金购买苏州岚创科技控股权（真空镀膜设备）。",
            "sub_leader_code": "600272",
            "sub_leader_name": "开开实业",
            "sub_leader_concept": "医药零售 / 7天5板",
            "sub_leader_boards": 5,
            "sub_leader_change": 10.00,
            "sub_leader_status": "反包涨停走出7天5板，收盘17.60元，换手28.15%，成交7.65亿元",
            "height_analysis": "昨日高度板秦安股份（603758）5连板后开盘跳水跌停；昨4连板京投发展（600683）涨停开盘后天地板收跌停，成交11.6亿元。高位3板及以上除蓝盾光电4进5外全线收跌。新高度切换至光通信重组标的蓝盾光电20cm五连板。连板晋级率仅27.27%（上一交易日22只连板股），短线进入高低切与主线切换。",
            "strategy_holding": "持筹者：秦安股份、京投发展、德龙汇能、宝鹰股份等老高位接力盘按核按钮纪律离场，严禁幻想地天板。蓝盾光电换手板封单偏弱（买一约3128万元、封成比仅0.9%），次日竞价若大幅低开或无法回封，应兑现而非死扛。",
            "strategy_buying": "持币者：高位空间板溢价已透支，严禁盲目接力5板。聚焦CPO散热（中石科技一字）、算力租赁（网宿科技20cm）低位首板/1进2，以及封成比极高的缩量3板（坤泰股份、澳洋健康）观察，仓位控制在2~4成。"
        },
        "ladder_matrix": [
            {
                "tier": "20cm 5连板（新高度）",
                "count": 1,
                "stocks": [
                    {"code": "300862", "name": "蓝盾光电", "price": 47.29, "change": 19.99, "concept": "并购重组/光通信镀膜设备", "turnover": 34.95, "turnover_rate": 51.69, "seal_amount": 3128, "seal_ratio": 0.90, "seal_time": "13:09:00", "breaks": 1, "status": "开一字后换手回封"}
                ]
            },
            {
                "tier": "7天5板",
                "count": 1,
                "stocks": [
                    {"code": "600272", "name": "开开实业", "price": 17.60, "change": 10.00, "concept": "医药零售/中华老字号", "turnover": 7.65, "turnover_rate": 28.15, "seal_amount": 2896, "seal_ratio": 3.80, "seal_time": "09:45:00", "breaks": 1, "status": "反包换手板"}
                ]
            },
            {
                "tier": "3连板",
                "count": 5,
                "stocks": [
                    {"code": "001260", "name": "坤泰股份", "price": 23.13, "change": 9.99, "concept": "缩量加速/低位小盘", "turnover": 0.30, "turnover_rate": 1.13, "seal_amount": 34000, "seal_ratio": 1126.00, "seal_time": "09:25:00", "breaks": 0, "status": "一字死封"},
                    {"code": "002172", "name": "澳洋健康", "price": 4.54, "change": 9.90, "concept": "脑机接口/康复医疗/洋字辈", "turnover": 0.87, "turnover_rate": 2.50, "seal_amount": 14000, "seal_ratio": 157.10, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"},
                    {"code": "603330", "name": "天洋新材", "price": 10.68, "change": 9.99, "concept": "电子胶/光模块散热/洋字辈", "turnover": 2.68, "turnover_rate": 6.24, "seal_amount": 9364, "seal_ratio": 34.90, "seal_time": "09:30:00", "breaks": 0, "status": "秒板缩量"},
                    {"code": "000936", "name": "华西股份", "price": 6.97, "change": 9.94, "concept": "光通信VCSEL/硅光/AI芯片参股", "turnover": 9.51, "turnover_rate": 15.45, "seal_amount": 4394, "seal_ratio": 4.60, "seal_time": "10:57:00", "breaks": 1, "status": "换手回封"},
                    {"code": "002081", "name": "金螳螂", "price": 5.29, "change": 9.98, "concept": "半导体洁净室/装饰装修", "turnover": 26.50, "turnover_rate": 19.72, "seal_amount": 9374, "seal_ratio": 3.50, "seal_time": "11:09:00", "breaks": 1, "status": "容量换手板"}
                ]
            },
            {
                "tier": "2连板",
                "count": 3,
                "stocks": [
                    {"code": "600613", "name": "神奇制药", "price": 6.41, "change": 9.90, "concept": "抗肿瘤药/医药分销", "turnover": 0.80, "turnover_rate": 2.61, "seal_amount": 15000, "seal_ratio": 186.30, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"},
                    {"code": "300404", "name": "博济医药", "price": 17.34, "change": 20.00, "concept": "CRO/中药创新药/司美格鲁肽临床", "turnover": 13.20, "turnover_rate": 27.53, "seal_amount": 7366, "seal_ratio": 5.60, "seal_time": "09:44:00", "breaks": 1, "status": "20cm换手板"},
                    {"code": "603118", "name": "共进股份", "price": 17.56, "change": 10.03, "concept": "800G交换机/硅光芯片", "turnover": 19.50, "turnover_rate": 14.31, "seal_amount": 9215, "seal_ratio": 4.70, "seal_time": "09:52:00", "breaks": 0, "status": "实体加速板"}
                ]
            },
            {
                "tier": "首板精选（光通信/算力租赁/散热）",
                "count": 44,
                "stocks": [
                    {"code": "300684", "name": "中石科技", "price": 67.36, "change": 20.01, "concept": "中际旭创入股/光模块散热/一字", "turnover": 2.86, "turnover_rate": 2.08, "seal_amount": 104300, "seal_ratio": 364.10, "seal_time": "09:25:00", "breaks": 0, "status": "20cm一字死封"},
                    {"code": "300017", "name": "网宿科技", "price": 17.33, "change": 20.01, "concept": "算力租赁/CDN龙头", "turnover": 76.62, "turnover_rate": 20.52, "seal_amount": 26000, "seal_ratio": 3.40, "seal_time": "14:14:00", "breaks": 1, "status": "20cm容量板"},
                    {"code": "600487", "name": "亨通光电", "price": 62.98, "change": 10.01, "concept": "光纤光缆/空芯光纤", "turnover": 191.97, "turnover_rate": 12.97, "seal_amount": 84400, "seal_ratio": 4.40, "seal_time": "14:49:00", "breaks": 1, "status": "百亿中军尾盘封板"},
                    {"code": "603083", "name": "剑桥科技", "price": 185.90, "change": 10.00, "concept": "CPO/1.6T光模块", "turnover": 71.30, "turnover_rate": 14.44, "seal_amount": 31000, "seal_ratio": 4.30, "seal_time": "13:40:00", "breaks": 1, "status": "CPO中军板"},
                    {"code": "603618", "name": "杭电股份", "price": 29.87, "change": 10.02, "concept": "光纤光缆/AIDC", "turnover": 32.80, "turnover_rate": 16.37, "seal_amount": 15000, "seal_ratio": 4.60, "seal_time": "13:08:00", "breaks": 1, "status": "光纤跟风板"},
                    {"code": "301419", "name": "阿莱德", "price": 37.62, "change": 20.00, "concept": "导热材料/光模块散热", "turnover": 4.40, "turnover_rate": 12.00, "seal_amount": 17000, "seal_ratio": 38.60, "seal_time": "10:31:00", "breaks": 0, "status": "20cm散热先锋"},
                    {"code": "688662", "name": "富信科技", "price": 98.40, "change": 20.00, "concept": "CPO散热/Micro TEC", "turnover": 16.90, "turnover_rate": 15.52, "seal_amount": 9836, "seal_ratio": 5.80, "seal_time": "13:01:00", "breaks": 1, "status": "科创20cm"},
                    {"code": "603186", "name": "华正新材", "price": 167.55, "change": 10.00, "concept": "CCL覆铜板/ABF膜", "turnover": 15.40, "turnover_rate": 6.02, "seal_amount": 38200, "seal_ratio": 24.80, "seal_time": "09:37:00", "breaks": 0, "status": "强封实体板"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "603758", "name": "秦安股份", "price": 13.82, "change": -10.00, "max_change": 0.00, "concept": "昨5连板高度板", "turnover": 6.00, "reason": "5连板后开盘跳水封死跌停，老高度核按钮，高位负反馈兑现"},
            {"code": "600683", "name": "京投发展", "price": 11.64, "change": -10.00, "max_change": 10.00, "concept": "昨4连板/光通信重组预期", "turnover": 11.60, "reason": "涨停开盘后天地板收跌停，成交11.6亿元，典型高位接力大面"},
            {"code": "000593", "name": "德龙汇能", "price": 25.02, "change": -10.00, "max_change": 2.00, "concept": "人气高位股", "turnover": 7.12, "reason": "人气股跌停，深南东路席位净卖约7638万元"},
            {"code": "002047", "name": "宝鹰股份", "price": 3.78, "change": -10.00, "max_change": 0.00, "concept": "高位跟风", "turnover": 3.35, "reason": "高位股集体下挫，跟风盘流动性枯竭跌停"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "001260", "name": "坤泰股份", "boards": 3, "seal_amount": 34000, "seal_ratio": 1126.00, "free_float_ratio": 25.28, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高（一字缩量、封单占流通约25%）"},
            {"rank": 2, "code": "300684", "name": "中石科技", "boards": 1, "seal_amount": 104300, "seal_ratio": 364.10, "free_float_ratio": 7.57, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高（中际旭创入股催化，封单超10亿）"},
            {"rank": 3, "code": "600613", "name": "神奇制药", "boards": 2, "seal_amount": 15000, "seal_ratio": 186.30, "free_float_ratio": 4.86, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "高（一字医药2板）"},
            {"rank": 4, "code": "002172", "name": "澳洋健康", "boards": 3, "seal_amount": 14000, "seal_ratio": 157.10, "free_float_ratio": 3.90, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "高（一字3板、换手仅2.5%）"},
            {"rank": 5, "code": "600487", "name": "亨通光电", "boards": 1, "seal_amount": 84400, "seal_ratio": 4.40, "free_float_ratio": 0.60, "first_seal": "14:49:00", "breaks": 1, "stars": 4, "premium_exp": "中高（192亿天量中军，尾盘封单8.4亿）"},
            {"rank": 6, "code": "603186", "name": "华正新材", "boards": 1, "seal_amount": 38200, "seal_ratio": 24.80, "free_float_ratio": 1.60, "first_seal": "09:37:00", "breaks": 0, "stars": 4, "premium_exp": "中高（早盘强封）"},
            {"rank": 7, "code": "300017", "name": "网宿科技", "boards": 1, "seal_amount": 26000, "seal_ratio": 3.40, "free_float_ratio": 0.80, "first_seal": "14:14:00", "breaks": 1, "stars": 4, "premium_exp": "中高（76.6亿容量20cm，游资+机构合力）"},
            {"rank": 8, "code": "300862", "name": "蓝盾光电", "boards": 5, "seal_amount": 3128, "seal_ratio": 0.90, "free_float_ratio": 0.50, "first_seal": "13:09:00", "breaks": 1, "stars": 3, "premium_exp": "中低（高度板但封成比极弱，次日溢价不确定）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "CPO/光通信/光纤", "inflow": 85.0, "change": 4.80, "leaders": "亨通光电、剑桥科技、中石科技、杭电股份", "limit_ups": 12},
                {"name": "算力租赁/CDN", "inflow": 42.0, "change": 3.50, "leaders": "网宿科技、利通电子、数据港", "limit_ups": 6},
                {"name": "导热散热材料", "inflow": 28.0, "change": 6.20, "leaders": "中石科技、阿莱德、富信科技、金戈新材", "limit_ups": 5},
                {"name": "医药零售/CRO", "inflow": 18.5, "change": 1.80, "leaders": "开开实业、博济医药、重药控股、华森制药", "limit_ups": 9}
            ],
            "sectors_outflow": [
                {"name": "电力公用事业", "outflow": -45.0, "change": -6.50, "reason": "华银电力、京能电力、粤电力A等电力股集体大跌"},
                {"name": "高位题材/影视传媒", "outflow": -32.0, "change": -4.20, "reason": "秦安股份、京投发展、德龙汇能跌停，北京文化、省广集团走弱"},
                {"name": "养殖/医美", "outflow": -18.0, "change": -2.80, "reason": "非主线防御与消费板块资金流出"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "600487", "name": "亨通光电", "turnover": 191.97, "change": 10.01, "role": "光纤中军/192亿成交旗手", "analysis": "两市光纤龙头尾盘封涨停，封单8.44亿元，成交近192亿元，是光通信主线容量锚点。"},
            {"rank": 2, "code": "300017", "name": "网宿科技", "turnover": 76.62, "change": 20.01, "role": "算力租赁20cm容量龙头", "analysis": "成交76.6亿元，章盟主净买约1.57亿、紫阳东路净买约2.07亿、机构净买约1.84亿，三路资金合力锁定20cm。"},
            {"rank": 3, "code": "603083", "name": "剑桥科技", "turnover": 71.30, "change": 10.00, "role": "CPO 1.6T中军", "analysis": "成交71.3亿元涨停，北京知春路等席位三日榜持续加仓，与中石科技散热逻辑共振。"},
            {"rank": 4, "code": "300862", "name": "蓝盾光电", "turnover": 34.95, "change": 19.99, "role": "短线空间新高度", "analysis": "换手51.69%完成5连板，但封成比仅0.9%，高度与封单质量背离，次日需观察溢价成色。"},
            {"rank": 5, "code": "688825", "name": "长鑫科技", "turnover": 180.00, "change": 4.20, "role": "存储芯片市值锚点", "analysis": "财联社复盘：成交额居两市前列但已降至200亿元以下，存储回暖但套牢盘仍压制弹性。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "紫阳东路 (华泰证券上海紫阳路)",
                "style": "超大资金卡位容量科技",
                "actions": [
                    {"stock": "网宿科技 (300017)", "net_buy": 20700, "type": "净买入约 2.07 亿元", "comment": "主买20cm算力租赁龙头，与章盟主形成席位共振"},
                    {"stock": "杭电股份 (603618)", "net_buy": 10800, "type": "净买入约 1.08 亿元", "comment": "同步扫货光纤跟风中军"},
                    {"stock": "经纬辉开 (300120)", "net_buy": 6506, "type": "净买入 6506 万元", "comment": "尾盘点火20cm散热/显示驱动方向"}
                ]
            },
            {
                "seat_name": "章盟主 (国泰君安成都北一环路等)",
                "style": "辨识度前排合力打板",
                "actions": [
                    {"stock": "网宿科技 (300017)", "net_buy": 15700, "type": "净买入约 1.57 亿元", "comment": "与紫阳东路合力锁仓网宿科技20cm"}
                ]
            },
            {
                "seat_name": "机构专用席位",
                "style": "趋势配置科技硬件",
                "actions": [
                    {"stock": "网宿科技 (300017)", "net_buy": 18400, "type": "净买入约 1.84 亿元", "comment": "机构跟进算力租赁容量龙头"},
                    {"stock": "中国稀土 (000831)", "net_buy": 25300, "type": "净买入约 2.53 亿元", "comment": "稀土战略重估方向的机构单边买入"}
                ]
            },
            {
                "seat_name": "上海自贸区 / 葛卫东",
                "style": "重组高度板分歧接力",
                "actions": [
                    {"stock": "蓝盾光电 (300862)", "net_buy": 7856, "type": "葛卫东净买入约 7856 万元", "comment": "接力20cm五连板重组标的"},
                    {"stock": "蓝盾光电 (300862)", "net_buy": 6065, "type": "上海自贸区净买入 6065 万元", "comment": "与葛卫东同向，但温州帮等席位同时大额卖出，高度板分歧加大"}
                ]
            },
            {
                "seat_name": "开源证券西安太华路 / 国新北京分",
                "style": "医药零售反包与金螳螂容量",
                "actions": [
                    {"stock": "开开实业 (600272)", "net_buy": 6133, "type": "西安太华路买入 6133.45 万元", "comment": "营业部席位合计净买入9112.95万元，反包7天5板"},
                    {"stock": "金螳螂 (002081)", "net_buy": 5434, "type": "湛江万豪世家加仓约 5434 万元", "comment": "国新北京分同步买入；作手新一净卖约4030万元，3板容量股多空对撞"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "DANGER", "triggered": True, "detail": "昨5连板秦安股份跌停，昨4连板京投发展天地板跌停，德龙汇能、宝鹰股份跌停，高位负反馈明确。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "SAFE", "triggered": False, "detail": "炸板19家、封板率约77%，炸板率23.17%，未过30%线；但高位杀跌比炸板更伤情绪。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "DANGER", "triggered": True, "detail": "连板晋级率仅27.27%（上一交易日22只连板股），3板及以上除蓝盾光电外全线收跌。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "DANGER", "triggered": True, "detail": "京投发展天地板，秦安股份、德龙汇能、宝鹰股份、同力天启等多股跌停或触及跌停。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "WARN", "triggered": True, "detail": "沪指收3927.18点仅涨0.01%守住3900；两市成交2.14万亿，较上一交易日缩量4081亿。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "WARN", "triggered": True, "detail": "老高位题材集体退潮，资金切向CPO散热与算力租赁，高低切剧烈。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "尚未进入全面退潮第二阶段：新高度蓝盾光电仍在、低位3板（坤泰、澳洋、天洋）仍有溢价，属于高位杀跌+新主线试错的分歧期。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "09:15-09:25 先看秦安股份、京投发展跌停封单：若继续封死，则中高位接力一律放弃。",
                "观察蓝盾光电竞价：换手板次日若高开不足3%或迅速翻绿，高度板溢价结束，不可再打。",
                "中石科技一字质量是光通信主线试金石：若继续大额封单，可沿散热/光纤低位首板弱转强参与；若开板巨震，主线逻辑降温。",
                "网宿科技竞价若平开或小高开且金额过亿，算力租赁容量逻辑仍在，只做回封与低吸，不追高开>7%。"
            ],
            "trading_discipline": [
                "【去弱留强】手中老高位（秦安、京投、德龙）竞价不回封立刻清仓；仓位压在2~4成。",
                "【不打弱封高度板】蓝盾光电封成比0.9%，空间虽在但质量差，胜率低于中石科技一字与坤泰/澳洋缩量3板。",
                "【主线只做辨识度前排】CPO散热（中石科技、阿莱德、富信科技）、光纤（亨通光电、杭电股份）、算力租赁（网宿科技）三选一，禁止同时铺开。"
            ],
            "risk_warnings": [
                "蓝盾光电已发严重异常波动公告，重组存在暂停、中止或取消风险，且2025年净利润亏损、2026年一季度继续亏损，基本面无法支撑无脑接力。",
                "两市缩量超4000亿，若下周一量能无法回到2.5万亿以上，指数在3950点附近存在二次冲高回落风险。",
                "3板晋级率大幅下滑，坤泰股份、澳洋健康、天洋新材、华西股份、金螳螂下周初存在分化，不可5只一起打。"
            ]
        }
    }

})

# Non-trading Day Information (Holidays & Weekends)
NON_TRADING_DAYS = {
    "2024-04-04": {
        "is_trading_day": False,
        "date": "2024-04-04",
        "date_cn": "2024年04月04日 星期四",
        "holiday_name": "清明节法定假期",
        "holiday_period": "2024年4月4日(周四) 至 2024年4月6日(周六)",
        "next_trading_day": "2024-04-08",
        "next_trading_day_cn": "2024年4月8日 (星期一) 09:30 正常开市",
        "reason": "清明节法定假日，中国A股、港股通及北向资金按交易所安排休市。",
        "prev_trading_day": "2024-04-03",
        "guidance": "休市期间无场内短线博弈数据，建议关注外盘原油、贵金属走势，跟踪清明假期低空经济文旅应用及消费数据，规避外盘波动风险。"
    },
    "2024-05-01": {
        "is_trading_day": False,
        "date": "2024-05-01",
        "date_cn": "2024年05月01日 星期三",
        "holiday_name": "五一国际劳动节假期",
        "holiday_period": "2024年5月1日(周三) 至 2024年5月5日(周日)",
        "next_trading_day": "2024-05-06",
        "next_trading_day_cn": "2024年5月6日 (星期一) 09:30 正常开市",
        "reason": "劳动节休市，A股市场暂停交易，资金清算按假期规则顺延。",
        "prev_trading_day": "2024-04-30",
        "guidance": "关注五一假期文旅、民航运输出行数据，以及海外美股科技七巨头财报与美联储利率决议导向。"
    },
    "2024-10-01": {
        "is_trading_day": False,
        "date": "2024-10-01",
        "date_cn": "2024年10月01日 星期二",
        "holiday_name": "国庆节黄金周长假",
        "holiday_period": "2024年10月1日(周二) 至 2024年10月7日(周一)",
        "next_trading_day": "2024-10-08",
        "next_trading_day_cn": "2024年10月8日 (星期二) 09:30 正常开市",
        "reason": "国庆黄金周休市7天，中国A股各交易所休市闭市。",
        "prev_trading_day": "2024-09-30",
        "guidance": "9月30日万亿暴涨狂潮后进入长假，重点关注长假期间港股大涨幅度、外资中国资产ETF溢价、券商新开户数据爆发情况，节后开市做足大分化推演！"
    },
    "2026-08-16": {
        "is_trading_day": False,
        "date": "2026-08-16",
        "date_cn": "2026年08月16日 星期日",
        "holiday_name": "周末常规休市",
        "holiday_period": "2026年8月15日(周六) 至 2026年8月16日(周日)",
        "next_trading_day": "2026-08-17",
        "next_trading_day_cn": "2026年8月17日 (星期一) 09:30 正常开市",
        "reason": "周末休市日（非交易日），证券交易所闭市维护。",
        "prev_trading_day": "2026-08-14",
        "guidance": "周末常规休市。复盘周五真实盘面：蓝盾光电20cm五连板成为新高度，秦安股份/京投发展高位核按钮，资金切换CPO散热与网宿科技算力租赁。下周一先看跌停封单与中石科技一字质量。"
    }
}

print("Market database loaded.")
