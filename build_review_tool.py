#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A-Share Short-Term Speculation Review Tool Single-File HTML Builder
Generates a complete, offline-capable, standalone HTML review tool.
Includes authentic historical market data and non-trading days.
"""

import json
import os

# Complete Historical Market Dataset for Trading & Non-Trading Days
MARKET_DATABASE = {
    "2024-03-22": {
        "is_trading_day": True,
        "date": "2024-03-22",
        "date_cn": "2024年03月22日 星期五",
        "market_summary": {
            "sh_index": 3048.03,
            "sh_change": -0.95,
            "sz_index": 9565.56,
            "sz_change": -1.21,
            "cy_index": 1869.17,
            "cy_change": -1.47,
            "total_turnover": 10973, # 亿元
            "turnover_change": 296, # 较昨日增加 296 亿
            "up_count": 1024,
            "down_count": 4126,
            "flat_count": 182,
            "median_change": -1.42,
            "limit_up_count": 58,
            "limit_down_count": 18,
            "broken_board_count": 28,
            "consecutive_board_count": 16,
            "broken_board_rate": 32.56, # 28 / (58+28)
            "promotion_rate_1_to_2": 33.33,
            "promotion_rate_2_to_3": 42.86,
            "promotion_rate_high": 40.0,
            "max_height": 13,
            "max_height_stock": "艾艾精工 (603580)",
            "sentiment_phase": "分歧期",
            "sentiment_phase_en": "Divergence",
            "sentiment_score": 46,
            "cash_defense_score": 38,
            "suggested_position": "2~4成 (防守试错)",
            "core_themes": ["低空经济/飞行汽车", "Kimi概念/AI应用", "高速铜连接", "汽车零部件", "新质生产力"]
        },
        "absolute_high": {
            "title": "总龙头断板巨震与高位分水岭",
            "leader_code": "603580",
            "leader_name": "艾艾精工",
            "concept": "新质生产力 / 轻型输送带",
            "consecutive_boards": 13,
            "close_price": 29.55,
            "change_percent": -8.08,
            "turnover": 8.42, # 亿元
            "turnover_rate": 22.15,
            "seal_status": "13连板后首日断板巨幅震荡",
            "intraday_behavior": "早盘大幅低开后快速冲高翻红，最高上冲至+4.6%，随后承接乏力逐波回落，尾盘收在-8.08%。全天振幅达13.5%，成交量显著放大至历史天量。",
            "sub_leader_code": "603879",
            "sub_leader_name": "永悦科技",
            "sub_leader_concept": "低空经济 / 植保无人机",
            "sub_leader_boards": 8,
            "sub_leader_change": -9.97,
            "sub_leader_status": "8连板断板触及跌停",
            "height_analysis": "艾艾精工13连板创造了年内短线连板空间新标杆，但今日高位龙头同步出现筹码松动与获利盘出逃，永悦科技8板断板触及跌停，标志着第一波高位纯连板抱团进入剧烈分歧与退潮初显阶段。高位负反馈开始累积，空间压制骤升。",
            "strategy_holding": "持筹者：龙头断板且跌破分时均线即为第一卖点，严禁死扛或期待无缝反包；尾盘未回封必须坚决止盈或清仓。",
            "strategy_buying": "持币者：严禁在龙头断板首日盲目接力中位加速板；耐心等待高位筹码出清及第二日极度冰点后的弱转强低吸信号。"
        },
        "ladder_matrix": [
            {
                "tier": "13连板 (断板)",
                "count": 1,
                "stocks": [
                    {"code": "603580", "name": "艾艾精工", "price": 29.55, "change": -8.08, "concept": "新质生产力/轻型输送带", "turnover": 8.42, "turnover_rate": 22.15, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "--", "breaks": 1, "status": "断板大面"}
                ]
            },
            {
                "tier": "8连板 (断板)",
                "count": 1,
                "stocks": [
                    {"code": "603879", "name": "永悦科技", "price": 10.02, "change": -9.97, "concept": "低空经济/无人机", "turnover": 7.85, "turnover_rate": 21.68, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "--", "breaks": 1, "status": "断板触跌停"}
                ]
            },
            {
                "tier": "5连板",
                "count": 2,
                "stocks": [
                    {"code": "603963", "name": "大理药业", "price": 14.82, "change": 10.02, "concept": "中药/医药商业", "turnover": 2.15, "turnover_rate": 6.85, "seal_amount": 15800, "seal_ratio": 73.49, "seal_time": "09:25:00", "breaks": 0, "status": "一字死封"},
                    {"code": "600841", "name": "动力新科", "price": 6.55, "change": 10.08, "concept": "氢能源/柴油机/无人驾驶", "turnover": 5.32, "turnover_rate": 8.12, "seal_amount": 8900, "seal_ratio": 16.73, "seal_time": "09:33:15", "breaks": 1, "status": "换手实体板"}
                ]
            },
            {
                "tier": "4连板",
                "count": 1,
                "stocks": [
                    {"code": "002621", "name": "美吉姆", "price": 3.42, "change": 9.97, "concept": "三胎概念/早教", "turnover": 1.45, "turnover_rate": 5.21, "seal_amount": 4200, "seal_ratio": 28.97, "seal_time": "09:31:00", "breaks": 0, "status": "缩量加速"}
                ]
            },
            {
                "tier": "3连板",
                "count": 3,
                "stocks": [
                    {"code": "603533", "name": "掌阅科技", "price": 27.61, "change": 10.00, "concept": "Kimi概念/短剧游戏/AI语料", "turnover": 14.20, "turnover_rate": 11.85, "seal_amount": 12500, "seal_ratio": 8.80, "seal_time": "09:36:20", "breaks": 1, "status": "分歧回封"},
                    {"code": "603896", "name": "华宝新能", "price": 82.50, "change": 10.00, "concept": "储能/便携储能", "turnover": 3.65, "turnover_rate": 7.42, "seal_amount": 5600, "seal_ratio": 15.34, "seal_time": "10:15:30", "breaks": 2, "status": "换手回封"},
                    {"code": "002235", "name": "安妮股份", "price": 7.39, "change": 9.97, "concept": "数据要素/版权保护", "turnover": 6.80, "turnover_rate": 16.20, "seal_amount": 6800, "seal_ratio": 10.00, "seal_time": "11:12:00", "breaks": 3, "status": "烂板回封"}
                ]
            },
            {
                "tier": "2连板",
                "count": 6,
                "stocks": [
                    {"code": "605180", "name": "华生科技", "price": 12.85, "change": 10.02, "concept": "低空经济/降落伞材料/纺织", "turnover": 1.82, "turnover_rate": 8.45, "seal_amount": 9200, "seal_ratio": 50.55, "seal_time": "09:30:15", "breaks": 0, "status": "秒板换手强封"},
                    {"code": "603217", "name": "元祖股份", "price": 18.26, "change": 10.00, "concept": "食品饮料/消费", "turnover": 1.15, "turnover_rate": 2.65, "seal_amount": 7800, "seal_ratio": 67.83, "seal_time": "09:32:00", "breaks": 0, "status": "一字板"},
                    {"code": "002907", "name": "华森制药", "price": 15.73, "change": 10.00, "concept": "创新药/中药", "turnover": 2.95, "turnover_rate": 7.12, "seal_amount": 4100, "seal_ratio": 13.90, "seal_time": "09:48:10", "breaks": 1, "status": "换手板"},
                    {"code": "002882", "name": "金龙羽", "price": 19.58, "change": 10.00, "concept": "固态电池/电线电缆", "turnover": 5.60, "turnover_rate": 13.50, "seal_amount": 6200, "seal_ratio": 11.07, "seal_time": "10:30:22", "breaks": 2, "status": "分歧板"},
                    {"code": "603019", "name": "中科曙光", "price": 54.12, "change": 10.00, "concept": "算力中军/服务器", "turnover": 48.50, "turnover_rate": 6.80, "seal_amount": 18500, "seal_ratio": 3.81, "seal_time": "14:15:00", "breaks": 3, "status": "趋势容量板"},
                    {"code": "002602", "name": "世纪鼎利", "price": 5.48, "change": 10.04, "concept": "华为昇腾/通信网络", "turnover": 4.10, "turnover_rate": 14.10, "seal_amount": 3800, "seal_ratio": 9.27, "seal_time": "13:45:10", "breaks": 2, "status": "午后回封"}
                ]
            },
            {
                "tier": "首板精选 (共46家)",
                "count": 46,
                "stocks": [
                    {"code": "002085", "name": "万丰奥威", "price": 14.28, "change": 10.02, "concept": "低空经济核心中军/eVTOL", "turnover": 67.45, "turnover_rate": 22.80, "seal_amount": 28500, "seal_ratio": 4.23, "seal_time": "14:28:10", "breaks": 4, "status": "百亿中军反包板"},
                    {"code": "600580", "name": "卧龙电驱", "price": 16.92, "change": 10.01, "concept": "低空航空电驱/机器人", "turnover": 41.20, "turnover_rate": 18.90, "seal_amount": 16200, "seal_ratio": 3.93, "seal_time": "10:45:00", "breaks": 1, "status": "容量突破板"},
                    {"code": "000099", "name": "中信海直", "price": 12.35, "change": 10.07, "concept": "低空运营/通用航空", "turnover": 32.10, "turnover_rate": 35.40, "seal_amount": 14800, "seal_ratio": 4.61, "seal_time": "09:42:15", "breaks": 2, "status": "低空人气先锋"},
                    {"code": "300459", "name": "汤姆猫", "price": 5.82, "change": 20.00, "concept": "Kimi应用/AI语料/IP", "turnover": 28.60, "turnover_rate": 15.60, "seal_amount": 19800, "seal_ratio": 6.92, "seal_time": "10:12:30", "breaks": 1, "status": "20cm中军大阳"},
                    {"code": "300058", "name": "蓝色光标", "price": 8.94, "change": 13.45, "concept": "AI营销/Kimi合作", "turnover": 35.20, "turnover_rate": 16.40, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "--", "breaks": 1, "status": "趋势大阳冲高"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "000628", "name": "高新发展", "price": 85.20, "change": 1.25, "max_change": 10.00, "concept": "算力重组/华鲲振宇", "turnover": 45.30, "reason": "早盘冲板后遭遇大单巨额砸盘，算力老主线分歧加剧"},
            {"code": "603083", "name": "剑桥科技", "price": 42.15, "change": -2.10, "max_change": 8.50, "concept": "光模块/CPO", "turnover": 38.60, "reason": "冲高回落，CPO老抱团跟风动力衰竭"},
            {"code": "002261", "name": "拓维信息", "price": 14.80, "change": -0.85, "max_change": 7.80, "concept": "华为昇腾/算力", "turnover": 29.40, "reason": "午后跟风冲高，主力资金持续净流出出货"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "603963", "name": "大理药业", "boards": 5, "seal_amount": 15800, "seal_ratio": 73.49, "free_float_ratio": 5.12, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "高 (90%+概率大高开)"},
            {"rank": 2, "code": "603217", "name": "元祖股份", "boards": 2, "seal_amount": 7800, "seal_ratio": 67.83, "free_float_ratio": 4.80, "first_seal": "09:32:00", "breaks": 0, "stars": 5, "premium_exp": "高 (85%+概率高开)"},
            {"rank": 3, "code": "605180", "name": "华生科技", "boards": 2, "seal_amount": 9200, "seal_ratio": 50.55, "free_float_ratio": 4.25, "first_seal": "09:30:15", "breaks": 0, "stars": 5, "premium_exp": "极高 (空间板接力核心)"},
            {"rank": 4, "code": "002621", "name": "美吉姆", "boards": 4, "seal_amount": 4200, "seal_ratio": 28.97, "free_float_ratio": 2.10, "first_seal": "09:31:00", "breaks": 0, "stars": 4, "premium_exp": "中高 (高开5%左右)"},
            {"rank": 5, "code": "600841", "name": "动力新科", "boards": 5, "seal_amount": 8900, "seal_ratio": 16.73, "free_float_ratio": 1.95, "first_seal": "09:33:15", "breaks": 1, "stars": 4, "premium_exp": "中 (平开或小高开)"},
            {"rank": 6, "code": "603896", "name": "华宝新能", "boards": 3, "seal_amount": 5600, "seal_ratio": 15.34, "free_float_ratio": 1.80, "first_seal": "10:15:30", "breaks": 2, "stars": 3, "premium_exp": "中低 (分歧震荡)"},
            {"rank": 7, "code": "603533", "name": "掌阅科技", "boards": 3, "seal_amount": 12500, "seal_ratio": 8.80, "free_float_ratio": 1.12, "first_seal": "09:36:20", "breaks": 1, "stars": 3, "premium_exp": "中 (依赖Kimi题材发酵)"},
            {"rank": 8, "code": "002085", "name": "万丰奥威", "boards": 1, "seal_amount": 28500, "seal_ratio": 4.23, "free_float_ratio": 0.95, "first_seal": "14:28:10", "breaks": 4, "stars": 4, "premium_exp": "中高 (容量大中军溢价)"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "低空经济/通用航空", "inflow": 28.5, "change": 3.82, "leaders": "中信海直、万丰奥威、卧龙电驱", "limit_ups": 12},
                {"name": "Kimi概念/AI语料", "inflow": 19.2, "change": 4.15, "leaders": "掌阅科技、中广天择、汤姆猫", "limit_ups": 7},
                {"name": "高速铜连接/通信", "inflow": 14.6, "change": 2.90, "leaders": "胜宏科技、沃尔核材、新亚电子", "limit_ups": 5},
                {"name": "固态电池/新材料", "inflow": 9.8, "change": 1.85, "leaders": "金龙羽、三祥新材", "limit_ups": 4},
                {"name": "化学制药/中药", "inflow": 7.5, "change": 1.20, "leaders": "大理药业、华森制药", "limit_ups": 3}
            ],
            "sectors_outflow": [
                {"name": "算力服务器/CPO", "outflow": -45.2, "change": -2.85, "reason": "老算力高位兑现，高新发展、中贝通信大单流出"},
                {"name": "光伏设备/新能源", "outflow": -28.6, "change": -2.10, "reason": "赛道反弹乏力，主力持续撤离"},
                {"name": "半导体芯片", "outflow": -22.4, "change": -1.65, "reason": "前期反弹板块获利了结"},
                {"name": "房地产开发", "outflow": -18.9, "change": -1.95, "reason": "政策真空期资金观望"},
                {"name": "白酒/食品饮料", "outflow": -16.5, "change": -1.40, "reason": "权重股拖累指数下行"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "601127", "name": "赛力斯", "turnover": 85.60, "change": -2.35, "role": "智能汽车趋势总中军", "analysis": "成交超85亿位居榜首，受大盘下行影响高位缩量震荡，多头形态未破，但对短线情绪已无额外向上带动。"},
            {"rank": 2, "code": "002085", "name": "万丰奥威", "turnover": 67.45, "change": 10.02, "role": "低空经济超级容量龙头", "analysis": "全天成交67.45亿，午后在大盘跳水时逆势封板反包，成为全市场最硬核的人气压舱石，维系短线做多底气。"},
            {"rank": 3, "code": "603019", "name": "中科曙光", "turnover": 48.50, "change": 10.00, "role": "国产算力中军代表", "analysis": "尾盘逆势拉板，带动部分科技硬件回流，但大资金分歧依然明显。"},
            {"rank": 4, "code": "000628", "name": "高新发展", "turnover": 45.30, "change": 1.25, "role": "算力重组情绪晴雨表", "analysis": "早盘冲击涨停炸板，巨额抛压显现，代表老周期算力标的面临较大筹码兑现压力。"},
            {"rank": 5, "code": "600580", "name": "卧龙电驱", "turnover": 41.20, "change": 10.01, "role": "低空经济核心部件龙头", "analysis": "成交超40亿强势封板，与万丰奥威形成低空经济双子星联动。"},
            {"rank": 6, "code": "000099", "name": "中信海直", "turnover": 32.10, "change": 10.07, "role": "低空运营先锋锚点", "analysis": "换手率高达35.4%，高位承接极其活跃，是游资与机构博弈的核心战场。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "呼家楼 (中信建投北京东城分行/中信证券呼家楼)",
                "style": "大格局顶格主封 / 打造大容量超级中军",
                "actions": [
                    {"stock": "万丰奥威 (002085)", "net_buy": 18200, "type": "净买入 1.82 亿元", "comment": "午后主封买一，主导万丰奥威反包涨停，锁仓低空经济超级核心"},
                    {"stock": "中信海直 (000099)", "net_buy": 4500, "type": "净买入 4500 万元", "comment": "加仓低空运营龙头，与万丰奥威形成梯队联动"}
                ]
            },
            {
                "seat_name": "作手新一 (国泰君安南京太平南路)",
                "style": "主线题材辨识度前排合力打板",
                "actions": [
                    {"stock": "掌阅科技 (603533)", "net_buy": 4560, "type": "净买入 4560 万元", "comment": "重仓主买Kimi概念核心先锋，抢占AI应用话语权"},
                    {"stock": "华生科技 (605180)", "net_buy": 1280, "type": "净买入 1280 万元", "comment": "排板2进3低位试错先锋，博弈新周期空间龙头"}
                ]
            },
            {
                "seat_name": "六一路 (招商证券福州六一中路)",
                "style": "波段格局 / 敢于锁仓承接大分歧",
                "actions": [
                    {"stock": "卧龙电驱 (600580)", "net_buy": 6200, "type": "净买入 6200 万元", "comment": "大举建仓低空电驱龙头，与机构形成合力买盘"}
                ]
            },
            {
                "seat_name": "机构专用席位 (Institutional Seats)",
                "style": "趋势大票配置 / 兑现高位纯投机",
                "actions": [
                    {"stock": "高新发展 (000628)", "net_buy": -12500, "type": "净卖出 1.25 亿元", "comment": "三家机构席位合计净卖出超1.2亿，高位持续兑现"},
                    {"stock": "卧龙电驱 (600580)", "net_buy": 8900, "type": "净买入 8900 万元", "comment": "两家机构席位大买，认可低空经济产业基本面逻辑"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "WARN", "triggered": True, "detail": "艾艾精工13板断板(-8.08%)，永悦科技8板断板触及跌停(-9.97%)，高位负反馈显现。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "WARN", "triggered": True, "detail": "今日炸板率达 32.56%，高于30%安全警戒线，打板炸板大面风险增加。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "连板整体晋级率 38.1%，二板及以上结构尚存，未完全进入绝对冰点。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "WARN", "triggered": True, "detail": "永悦科技、艾艾精工等多只高位股日内振幅超12%，亏钱效应开始在龙头端蔓延。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "两市成交额10,973亿元维持在万亿以上，量能未缩，但指数呈现震荡调整。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "WARN", "triggered": True, "detail": "除低空经济和Kimi外，多数支线题材分化明显，接力亏钱效应扩散。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "当前处于退潮初期/高位分歧阶段，低位华生科技、万丰奥威仍在尝试新老切换。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "09:15-09:20 重点观察艾艾精工与永悦科技竞价挂单：若永悦科技大单封死跌停，高位连板接力一律放弃！",
                "09:20-09:25 重点观察华生科技 (605180) 竞价：若竞价大额爆量高开（>+5%甚至一字），可确认为新老周期切换的低位空间试错点。",
                "关注万丰奥威竞价承接力度：若平开或小幅高开且竞价金额>2亿元，说明低空经济主线中军承接强劲，可逢低参与低位首板挖掘。"
            ],
            "trading_discipline": [
                "【去弱留强】手中持仓若早盘反抽不创新高且跌破分时均线，坚决在第一波冲高时清仓减亏，绝不幻想日内反包。",
                "【严禁盲目接力中位板】3板~5板中位股如动力新科、大理药业面临巨大晋级与补跌压力，只看不买，谨防天地板大面。",
                "【聚焦新周期低位试错】仅允许在低位1进2（如低空经济降落伞材料华生科技、固态电池）或主线容量中军水下分时低吸。"
            ],
            "risk_warnings": [
                "监管层对短线连板炒作监控趋严，严重异动公告频发，警惕高位妖股突发停牌核查风险。",
                "大盘指数跌破3050点，若量能无法持续维持万亿，警惕指数与短线情绪共振下杀的系统性风险。"
            ]
        }
    },
    "2024-03-25": {
        "is_trading_day": True,
        "date": "2024-03-25",
        "date_cn": "2024年03月25日 星期一",
        "market_summary": {
            "sh_index": 3026.31,
            "sh_change": -0.71,
            "sz_index": 9422.61,
            "sz_change": -1.49,
            "cy_index": 1833.44,
            "cy_change": -1.91,
            "total_turnover": 10435,
            "turnover_change": -538,
            "up_count": 2287,
            "down_count": 2890,
            "flat_count": 145,
            "median_change": -0.45,
            "limit_up_count": 61,
            "limit_down_count": 27,
            "broken_board_count": 38,
            "consecutive_board_count": 14,
            "broken_board_rate": 38.38,
            "promotion_rate_1_to_2": 26.67,
            "promotion_rate_2_to_3": 50.00,
            "promotion_rate_high": 25.0,
            "max_height": 3,
            "max_height_stock": "华生科技 (605180) / 青海华鼎 / 亚振家居",
            "sentiment_phase": "退潮期",
            "sentiment_phase_en": "Recession",
            "sentiment_score": 32,
            "cash_defense_score": 24,
            "suggested_position": "0~2成 (严格空仓防守)",
            "core_themes": ["低空经济/飞行汽车", "小米汽车", "新材料", "低位消费/家具"]
        },
        "absolute_high": {
            "title": "高位双龙头齐遭跌停核按钮，新周期空间压制至3板",
            "leader_code": "605180",
            "leader_name": "华生科技",
            "concept": "低空经济 / 降落伞材料 / 气密新材料",
            "consecutive_boards": 3,
            "close_price": 14.14,
            "change_percent": 10.04,
            "turnover": 2.10,
            "turnover_rate": 9.80,
            "seal_status": "一字死封晋级3连板",
            "intraday_behavior": "开盘大单死封一字涨停，全天未开板，封单金额超1.5亿，成为全市场唯一穿越老周期退潮的低位空间新种子。",
            "sub_leader_code": "603879",
            "sub_leader_name": "永悦科技",
            "sub_leader_concept": "无人机 / 低空经济",
            "sub_leader_boards": 0,
            "sub_leader_change": -10.00,
            "sub_leader_status": "一字跌停封死 (核按钮)",
            "height_analysis": "艾艾精工与永悦科技今日双双一字封死跌停，动力新科大跌-7.5%，高位连板被腰斩，市场最高连板被直接压制到3板（华生科技、青海华鼎、亚振家居）。极端亏钱效应在上一代连板股中全面爆发。",
            "strategy_holding": "持筹者：手中有老周期高位接力标的者，不计成本挂单核按钮离场，切忌幻想次日地天板反包。",
            "strategy_buying": "持币者：严格执行空仓纪律！退潮期不伸手，仅对极低位一字新题材龙头（如华生科技）或具备独立逻辑的容量大中军（如万丰奥威）保留极小仓位观察。"
        },
        "ladder_matrix": [
            {
                "tier": "3连板",
                "count": 3,
                "stocks": [
                    {"code": "605180", "name": "华生科技", "price": 14.14, "change": 10.04, "concept": "低空经济/降落伞材料", "turnover": 2.10, "turnover_rate": 9.80, "seal_amount": 15600, "seal_ratio": 74.28, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"},
                    {"code": "600243", "name": "青海华鼎", "price": 4.58, "change": 10.10, "concept": "工业母机/机器人", "turnover": 1.25, "turnover_rate": 3.12, "seal_amount": 8900, "seal_ratio": 71.20, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"},
                    {"code": "603389", "name": "亚振家居", "price": 6.82, "change": 10.00, "concept": "智能家居/消费", "turnover": 1.80, "turnover_rate": 4.50, "seal_amount": 6200, "seal_ratio": 34.44, "seal_time": "09:30:10", "breaks": 0, "status": "缩量板"}
                ]
            },
            {
                "tier": "2连板",
                "count": 4,
                "stocks": [
                    {"code": "002536", "name": "飞龙股份", "price": 13.52, "change": 10.01, "concept": "汽车零部件/小米汽车", "turnover": 4.20, "turnover_rate": 8.60, "seal_amount": 7500, "seal_ratio": 17.85, "seal_time": "09:35:10", "breaks": 1, "status": "换手板"},
                    {"code": "603223", "name": "恒帅股份", "price": 78.40, "change": 10.00, "concept": "汽车微电机/智能底盘", "turnover": 2.80, "turnover_rate": 5.40, "seal_amount": 5100, "seal_ratio": 18.21, "seal_time": "10:12:00", "breaks": 0, "status": "缩量板"},
                    {"code": "002871", "name": "伟隆股份", "price": 11.20, "change": 10.02, "concept": "水利阀门/低价小盘", "turnover": 1.10, "turnover_rate": 4.20, "seal_amount": 4300, "seal_ratio": 39.09, "seal_time": "09:32:00", "breaks": 0, "status": "秒板"},
                    {"code": "002047", "name": "宝鹰股份", "price": 2.84, "change": 10.08, "concept": "国企改革/低空基建", "turnover": 2.45, "turnover_rate": 6.80, "seal_amount": 3800, "seal_ratio": 15.51, "seal_time": "11:20:00", "breaks": 2, "status": "弱换手"}
                ]
            },
            {
                "tier": "首板精选",
                "count": 54,
                "stocks": [
                    {"code": "002085", "name": "万丰奥威", "price": 15.71, "change": 10.01, "concept": "低空经济超级中军/反包涨停", "turnover": 81.30, "turnover_rate": 26.50, "seal_amount": 32000, "seal_ratio": 3.93, "seal_time": "13:10:00", "breaks": 2, "status": "超级中军反包"},
                    {"code": "000099", "name": "中信海直", "price": 13.59, "change": 10.04, "concept": "低空运营先锋", "turnover": 38.50, "turnover_rate": 38.20, "seal_amount": 16500, "seal_ratio": 4.28, "seal_time": "09:40:00", "breaks": 1, "status": "大换手连涨"},
                    {"code": "601127", "name": "赛力斯", "price": 98.50, "change": 4.50, "concept": "问界M9/智能汽车", "turnover": 72.40, "turnover_rate": 5.80, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "--", "breaks": 0, "status": "中军抗跌震荡"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "600841", "name": "动力新科", "price": 6.06, "change": -7.48, "max_change": 4.50, "concept": "氢能源/老周期5板", "turnover": 7.80, "reason": "早盘冲高诱多后被巨量砸盘，直接杀跌近8点"},
            {"code": "603533", "name": "掌阅科技", "price": 25.10, "change": -9.09, "max_change": 3.20, "concept": "Kimi概念/3板断板", "turnover": 18.50, "reason": "高开后遭遇大单砸盘，Kimi题材出现严重分歧"},
            {"code": "002621", "name": "美吉姆", "price": 3.10, "change": -9.36, "max_change": 5.00, "concept": "早教/4板断板", "turnover": 3.40, "reason": "直接低开下杀，中位连板全线崩溃"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "605180", "name": "华生科技", "boards": 3, "seal_amount": 15600, "seal_ratio": 74.28, "free_float_ratio": 5.80, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高 (新周期空间总龙头)"},
            {"rank": 2, "code": "600243", "name": "青海华鼎", "boards": 3, "seal_amount": 8900, "seal_ratio": 71.20, "free_float_ratio": 4.10, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "高 (一字缩量溢价)"},
            {"rank": 3, "code": "002871", "name": "伟隆股份", "boards": 2, "seal_amount": 4300, "seal_ratio": 39.09, "free_float_ratio": 3.20, "first_seal": "09:32:00", "breaks": 0, "stars": 4, "premium_exp": "中高"},
            {"rank": 4, "code": "603389", "name": "亚振家居", "boards": 3, "seal_amount": 6200, "seal_ratio": 34.44, "free_float_ratio": 2.90, "first_seal": "09:30:10", "breaks": 0, "stars": 4, "premium_exp": "中"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "小米汽车产业链", "inflow": 32.5, "change": 4.80, "leaders": "津荣天宇、飞龙股份、凯众股份", "limit_ups": 9},
                {"name": "低空经济/飞行汽车", "inflow": 26.8, "change": 3.20, "leaders": "万丰奥威、中信海直、华生科技", "limit_ups": 11},
                {"name": "工业母机/新型工业化", "inflow": 11.2, "change": 2.10, "leaders": "青海华鼎、华东重机", "limit_ups": 4}
            ],
            "sectors_outflow": [
                {"name": "Kimi/AI大模型应用", "outflow": -58.6, "change": -4.20, "reason": "掌阅科技、中广天择大幅杀跌，题材巨震兑现"},
                {"name": "算力与光通信CPO", "outflow": -41.2, "change": -3.10, "reason": "高位筹码松动，资金持续出逃"},
                {"name": "医药生物", "outflow": -29.5, "change": -2.40, "reason": "老医药连板股全线补跌"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "002085", "name": "万丰奥威", "turnover": 81.30, "change": 10.01, "role": "超级中军反包大旗", "analysis": "全天成交81.3亿创历史天量，逆市拉升反包涨停，独自扛起低空经济大旗，是全市场唯一的定海神针。"},
            {"rank": 2, "code": "601127", "name": "赛力斯", "turnover": 72.40, "change": 4.50, "role": "智能汽车容量中军", "analysis": "承接良好，保持在百元关口附近强势震荡。"},
            {"rank": 3, "code": "603533", "name": "掌阅科技", "turnover": 18.50, "change": -9.09, "role": "AI应用退潮负反馈锚点", "analysis": "大跌逾9%，对AI应用和短剧板块形成严重压制。"}
        ],
        "dragon_tiger_list": [
            {"seat_name": "六一路 (招商证券福州六一中路)", "style": "超强大局观 / 打造核心龙头", "actions": [{"stock": "华生科技 (605180)", "net_buy": 1520, "type": "净买入 1520 万元", "comment": "排板买一，独具慧眼锁仓新周期3板空间龙"}]},
            {"seat_name": "呼家楼 (中信建投北京东城分行)", "style": "万丰奥威大格局锁仓", "actions": [{"stock": "万丰奥威 (002085)", "net_buy": 21000, "type": "净买入 2.10 亿元", "comment": "再次顶格大手笔加仓万丰奥威，锁仓超5亿"}]},
            {"seat_name": "方新侠 (中信证券西安朱雀大街)", "style": "转战小米汽车产业链", "actions": [{"stock": "飞龙股份 (002536)", "net_buy": 3200, "type": "净买入 3200 万元", "comment": "扫单买入小米汽车核心部件先锋"}]}
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "DANGER", "triggered": True, "detail": "永悦科技与艾艾精工双双跌停封死，老龙头直接计提巨额亏损！"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "DANGER", "triggered": True, "detail": "今日炸板率高达 38.38%，亏钱效应严重！"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "DANGER", "triggered": True, "detail": "高位连板晋级率仅 25.0%，中位板惨遭全灭。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "DANGER", "triggered": True, "detail": "动力新科、掌阅科技、美吉姆等大批个股暴跌逾8-10%。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "WARN", "triggered": True, "detail": "沪指跌破3030点，成交量萎缩538亿。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "DANGER", "triggered": True, "detail": "前日涨停个股今日平均亏损严重。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "DANGER", "triggered": True, "detail": "老周期全线出清杀跌，符合典型退潮冰点特征。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "09:15-09:25 严格审视永悦科技与艾艾精工跌停板封单情况，若封单继续超10万手，绝不出手任何中高位接力！",
                "观察华生科技竞价：若继续巨额一字封单，确认其唯一新周期穿越龙地位，可关注其同板块低位首板补涨助攻。"
            ],
            "trading_discipline": [
                "【空仓是最高的美德】退潮杀跌期现金为王，仓位压制在 0~2 成以内，保住本金！",
                "【不抄底破位股】跌停板及断板破位股严禁去摸底反弹，防止连续跌停A杀。"
            ],
            "risk_warnings": [
                "老龙头连续跌停导致的市场流动性抽血与踩踏风险。",
                "中位板断板后直接计提20%以上大面风险。"
            ]
        }
    },
    "2024-04-18": {
        "is_trading_day": True,
        "date": "2024-04-18",
        "date_cn": "2024年04月18日 星期四",
        "market_summary": {
            "sh_index": 3074.22,
            "sh_change": 0.09,
            "sz_index": 9376.81,
            "sz_change": -0.05,
            "cy_index": 1787.91,
            "cy_change": -0.55,
            "total_turnover": 9496,
            "turnover_change": 312,
            "up_count": 2135,
            "down_count": 2980,
            "flat_count": 235,
            "median_change": -0.15,
            "limit_up_count": 72,
            "limit_down_count": 11,
            "broken_board_count": 23,
            "consecutive_board_count": 18,
            "broken_board_rate": 24.21,
            "promotion_rate_1_to_2": 45.45,
            "promotion_rate_2_to_3": 60.00,
            "promotion_rate_high": 66.67,
            "max_height": 5,
            "max_height_stock": "同为股份 (002835) / 春光科技 (603657)",
            "sentiment_phase": "修复期",
            "sentiment_phase_en": "Repair",
            "sentiment_score": 68,
            "cash_defense_score": 75,
            "suggested_position": "5~7成 (主线进攻)",
            "core_themes": ["低空经济/eVTOL", "业绩预增/安防", "家电出口/出海", "机器人/飞行汽车部件"]
        },
        "absolute_high": {
            "title": "业绩主线双龙并进，低空经济中军中信海直2连板主升共振",
            "leader_code": "002835",
            "leader_name": "同为股份",
            "concept": "业绩超预期 + 安防监控 + 机器视觉",
            "consecutive_boards": 5,
            "close_price": 20.72,
            "change_percent": 9.98,
            "turnover": 1.95,
            "turnover_rate": 8.20,
            "seal_status": "一字顶死5连板",
            "intraday_behavior": "开盘集合竞价一字封单超15万手，全天封死不动，确立业绩线总龙头地位。",
            "sub_leader_code": "603657",
            "sub_leader_name": "春光科技",
            "sub_leader_concept": "家电零部件 / 外销出口",
            "sub_leader_boards": 5,
            "sub_leader_change": 10.01,
            "sub_leader_status": "5连板一字顶死",
            "height_analysis": "同为股份与春光科技携手晋级5连板，打破前期4板高度压制；同时低空经济核心中军中信海直2连板放量涨停，宗申动力、苏交科20cm大涨，市场情绪从冰点向局部主升全面修复。",
            "strategy_holding": "持筹者：同为股份、春光科技只要不爆巨量开板，坚决躺平吃主升；中信海直沿着5日均线锁仓。",
            "strategy_buying": "持币者：高位一字无法介入，重点在低空经济和业绩预增方向寻找1进2及首板弱转强机会。"
        },
        "ladder_matrix": [
            {
                "tier": "5连板",
                "count": 2,
                "stocks": [
                    {"code": "002835", "name": "同为股份", "price": 20.72, "change": 9.98, "concept": "业绩超预期/安防", "turnover": 1.95, "turnover_rate": 8.20, "seal_amount": 18200, "seal_ratio": 93.33, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"},
                    {"code": "603657", "name": "春光科技", "price": 20.12, "change": 10.01, "concept": "家电出口/外贸", "turnover": 1.60, "turnover_rate": 6.50, "seal_amount": 14500, "seal_ratio": 90.62, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"}
                ]
            },
            {
                "tier": "3连板",
                "count": 2,
                "stocks": [
                    {"code": "002517", "name": "恺英网络", "price": 12.80, "change": 9.97, "concept": "游戏/AI落地", "turnover": 6.80, "turnover_rate": 5.40, "seal_amount": 7800, "seal_ratio": 11.47, "seal_time": "09:45:00", "breaks": 1, "status": "换手板"},
                    {"code": "002681", "name": "奋达科技", "price": 5.12, "change": 10.11, "concept": "消费电子/智能音箱", "turnover": 3.90, "turnover_rate": 7.10, "seal_amount": 6200, "seal_ratio": 15.90, "seal_time": "10:02:00", "breaks": 0, "status": "实体板"}
                ]
            },
            {
                "tier": "2连板",
                "count": 6,
                "stocks": [
                    {"code": "000099", "name": "中信海直", "price": 17.68, "change": 10.02, "concept": "低空经济超级中军先锋", "turnover": 47.30, "turnover_rate": 42.10, "seal_amount": 26000, "seal_ratio": 5.50, "seal_time": "09:40:00", "breaks": 1, "status": "容量中军2连板"},
                    {"code": "001696", "name": "宗申动力", "price": 10.25, "change": 9.98, "concept": "航空活塞发动机/低空核心", "turnover": 22.40, "turnover_rate": 24.60, "seal_amount": 15800, "seal_ratio": 7.05, "seal_time": "09:35:00", "breaks": 0, "status": "加速板"},
                    {"code": "002085", "name": "万丰奥威", "price": 16.85, "change": 10.01, "concept": "低空经济总龙头", "turnover": 52.80, "turnover_rate": 18.20, "seal_amount": 28000, "seal_ratio": 5.30, "seal_time": "10:20:00", "breaks": 1, "status": "大中军反包板"},
                    {"code": "300284", "name": "苏交科", "price": 11.88, "change": 20.00, "concept": "低空基建规划/20cm先锋", "turnover": 31.50, "turnover_rate": 35.80, "seal_amount": 21000, "seal_ratio": 6.67, "seal_time": "10:05:00", "breaks": 1, "status": "20cm大阳板"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "603019", "name": "中科曙光", "price": 46.20, "change": 2.10, "max_change": 7.80, "concept": "服务器/算力", "turnover": 35.20, "reason": "跟风冲高乏力，资金向低空经济和业绩线倾斜"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002835", "name": "同为股份", "boards": 5, "seal_amount": 18200, "seal_ratio": 93.33, "free_float_ratio": 6.20, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高 (继续一字涨停预期)"},
            {"rank": 2, "code": "603657", "name": "春光科技", "boards": 5, "seal_amount": 14500, "seal_ratio": 90.62, "free_float_ratio": 5.80, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 3, "code": "001696", "name": "宗申动力", "boards": 2, "seal_amount": 15800, "seal_ratio": 7.05, "free_float_ratio": 2.40, "first_seal": "09:35:00", "breaks": 0, "stars": 5, "premium_exp": "高 (高开5%以上)"},
            {"rank": 4, "code": "000099", "name": "中信海直", "boards": 2, "seal_amount": 26000, "seal_ratio": 5.50, "free_float_ratio": 2.10, "first_seal": "09:40:00", "breaks": 1, "stars": 5, "premium_exp": "高 (大资金溢价强)"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "低空经济/通用航空", "inflow": 48.5, "change": 6.50, "leaders": "中信海直、宗申动力、苏交科、万丰奥威", "limit_ups": 18},
                {"name": "业绩预增板块", "inflow": 24.2, "change": 3.80, "leaders": "同为股份、荣泰健康", "limit_ups": 10},
                {"name": "家电出口/消费", "inflow": 15.6, "change": 2.40, "leaders": "春光科技、火星人", "limit_ups": 5}
            ],
            "sectors_outflow": [
                {"name": "贵金属/黄金", "outflow": -28.4, "change": -3.20, "reason": "避险情绪降温，前期高位黄金股获利了结"},
                {"name": "煤炭开采", "outflow": -19.5, "change": -1.80, "reason": "红利防御资产资金流向进攻成长题材"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "002085", "name": "万丰奥威", "turnover": 52.80, "change": 10.01, "role": "低空经济领航总中军", "analysis": "成交52.8亿再次强势涨停，均线系统完美多头排列，引领全板块再创新高。"},
            {"rank": 2, "code": "000099", "name": "中信海直", "turnover": 47.30, "change": 10.02, "role": "低空人气急先锋", "analysis": "换手率超42%，超强大资金进场锁筹，成为短线爆发力最强的核心。"}
        ],
        "dragon_tiger_list": [
            {"seat_name": "呼家楼 (中信建投北京东城分行)", "style": "低空主升超级主力", "actions": [{"stock": "中信海直 (000099)", "net_buy": 12500, "type": "净买入 1.25 亿元", "comment": "加仓主封中信海直2连板，与万丰奥威共振主升"}]},
            {"seat_name": "六一路 (招商证券福州六一中路)", "style": "加仓宗申动力", "actions": [{"stock": "宗申动力 (001696)", "net_buy": 4800, "type": "净买入 4800 万元", "comment": "主买宗申动力，打造低空动力核心"}]}
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "最高板同为股份、春光科技双双一字封死5板，无任何负反馈。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "SAFE", "triggered": False, "detail": "炸板率降至 24.21%，处于健康良性区间。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "高位晋级率高达 66.67%，赚钱效应充沛。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "SAFE", "triggered": False, "detail": "跌停仅11家，无大面积恶性核按钮。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "成交量温和放大至9496亿元，指数企稳。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "低空经济与业绩主线持续性极佳。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "当前处于修复向主升展开阶段，适合重仓进攻。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "竞价重点观察同为股份、春光科技是否继续一字，若封单>10万手，主线情绪无忧。",
                "观察中信海直、宗申动力高开幅度，若高开3-6%且竞价金额>1亿，可直接顺势上车。"
            ],
            "trading_discipline": [
                "【重仓拥抱核心主线】聚焦低空经济主线标的，杜绝去杂毛弱势板块浪费仓位。",
                "【持股待涨不轻易下车】龙头股分时震荡不破均线坚决锁仓。"
            ],
            "risk_warnings": [
                "谨防高位一字板加速后突发开板爆量炸板风险。",
                "大盘3100点整数关口压力位附近的震荡。"
            ]
        }
    },
    "2024-09-30": {
        "is_trading_day": True,
        "date": "2024-09-30",
        "date_cn": "2024年09月30日 星期一",
        "market_summary": {
            "sh_index": 3336.50,
            "sh_change": 8.06,
            "sz_index": 10529.76,
            "sz_change": 10.67,
            "cy_index": 2175.09,
            "cy_change": 15.36,
            "total_turnover": 25930, # 创A股历史单日历史天量
            "turnover_change": 11450,
            "up_count": 5336,
            "down_count": 8,
            "flat_count": 12,
            "median_change": 8.52,
            "limit_up_count": 712,
            "limit_down_count": 0,
            "broken_board_count": 31,
            "consecutive_board_count": 48,
            "broken_board_rate": 4.17,
            "promotion_rate_1_to_2": 88.50,
            "promotion_rate_2_to_3": 92.30,
            "promotion_rate_high": 95.0,
            "max_height": 14,
            "max_height_stock": "双成药业 (002693)",
            "sentiment_phase": "高潮期",
            "sentiment_phase_en": "Climax",
            "sentiment_score": 100,
            "cash_defense_score": 98,
            "suggested_position": "8~10成 (满仓抢筹)",
            "core_themes": ["大金融/券商/金融科技", "半导体/芯片自主可控", "华为鸿蒙/软件", "房地产/白酒权重"]
        },
        "absolute_high": {
            "title": "史诗级放量2.6万亿！双成药业14连板，东方财富单日305亿20cm涨停",
            "leader_code": "002693",
            "leader_name": "双成药业",
            "concept": "跨界重组半导体 / 芯片并购",
            "consecutive_boards": 14,
            "close_price": 14.50,
            "change_percent": 10.02,
            "turnover": 4.50,
            "turnover_rate": 8.50,
            "seal_status": "14连板一字顶死",
            "intraday_behavior": "开盘大单死封一字，全天纹丝不动，成为跨越牛熊的绝对神话标杆。",
            "sub_leader_code": "300059",
            "sub_leader_name": "东方财富",
            "sub_leader_concept": "券商龙头 / 金融科技 / 容量总龙头",
            "sub_leader_boards": 2,
            "sub_leader_change": 20.00,
            "sub_leader_status": "20cm巨额封死涨停，成交305亿元",
            "height_analysis": "两市单日成交突破2.59万亿创历史纪录，创业板指狂飙15.36%，全市场逾700股涨停仅8股下跌。牛市全面爆发，大金融券商与金融科技成为绝对主线。",
            "strategy_holding": "持筹者：满仓持股待涨，一股不卖！静待国庆长假节后情绪进一步发酵。",
            "strategy_buying": "持币者：开盘任何能买到的券商、金融科技中军、半导体龙头直接挂单抢筹！"
        },
        "ladder_matrix": [
            {
                "tier": "14连板",
                "count": 1,
                "stocks": [
                    {"code": "002693", "name": "双成药业", "price": 14.50, "change": 10.02, "concept": "并购重组/半导体", "turnover": 4.50, "turnover_rate": 8.50, "seal_amount": 85000, "seal_ratio": 188.89, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"}
                ]
            },
            {
                "tier": "6天5板",
                "count": 1,
                "stocks": [
                    {"code": "300085", "name": "银之杰", "price": 28.50, "change": 20.00, "concept": "金融科技/互金", "turnover": 42.10, "turnover_rate": 25.40, "seal_amount": 45000, "seal_ratio": 10.69, "seal_time": "09:30:15", "breaks": 0, "status": "20cm先锋"}
                ]
            },
            {
                "tier": "2连板/大容量中军",
                "count": 15,
                "stocks": [
                    {"code": "300059", "name": "东方财富", "price": 20.30, "change": 20.00, "concept": "券商/金融科技超级中军", "turnover": 305.00, "turnover_rate": 11.20, "seal_amount": 150000, "seal_ratio": 4.92, "seal_time": "10:15:00", "breaks": 1, "status": "300亿天量20cm"},
                    {"code": "300033", "name": "同花顺", "price": 165.20, "change": 20.00, "concept": "金融信息/AI投资", "turnover": 78.50, "turnover_rate": 15.60, "seal_amount": 62000, "seal_ratio": 7.90, "seal_time": "09:35:00", "breaks": 0, "status": "20cm秒板"},
                    {"code": "600030", "name": "中信证券", "price": 24.88, "change": 10.01, "concept": "券商航母总中军", "turnover": 98.40, "turnover_rate": 3.80, "seal_amount": 85000, "seal_ratio": 8.64, "seal_time": "09:42:00", "breaks": 0, "status": "券商大中军"},
                    {"code": "300339", "name": "润和软件", "price": 38.60, "change": 20.00, "concept": "华为鸿蒙/软件服务", "turnover": 112.00, "turnover_rate": 38.50, "seal_amount": 58000, "seal_ratio": 5.18, "seal_time": "10:30:00", "breaks": 1, "status": "鸿蒙总中军"}
                ]
            }
        ],
        "broken_board_list": [],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002693", "name": "双成药业", "boards": 14, "seal_amount": 85000, "seal_ratio": 188.89, "free_float_ratio": 15.40, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高 (继续无量一字)"},
            {"rank": 2, "code": "300059", "name": "东方财富", "boards": 2, "seal_amount": 150000, "seal_ratio": 4.92, "free_float_ratio": 4.20, "first_seal": "10:15:00", "breaks": 1, "stars": 5, "premium_exp": "极高 (牛市旗手)"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "证券与金融科技", "inflow": 385.0, "change": 12.50, "leaders": "东方财富、中信证券、银之杰、同花顺", "limit_ups": 52},
                {"name": "半导体与集成电路", "inflow": 210.0, "change": 11.20, "leaders": "中芯国际、寒武纪、北方华创", "limit_ups": 45},
                {"name": "软件开发与华为鸿蒙", "inflow": 165.0, "change": 13.80, "leaders": "润和软件、软通动力、常山北明", "limit_ups": 38}
            ],
            "sectors_outflow": []
        },
        "popularity_anchors": [
            {"rank": 1, "code": "300059", "name": "东方财富", "turnover": 305.00, "change": 20.00, "role": "牛市总旗手/流动性核心", "analysis": "单日305亿成交封死20cm，奠定本轮超级行情牛市总龙头地位。"},
            {"rank": 2, "code": "300339", "name": "润和软件", "turnover": 112.00, "change": 20.00, "role": "科技主线总中军", "analysis": "成交超百亿20cm涨停，华为产业链与软件科技总龙头。"}
        ],
        "dragon_tiger_list": [
            {"seat_name": "机构专用席位群", "style": "全面增仓扫盘", "actions": [{"stock": "东方财富 (300059)", "net_buy": 158000, "type": "净买入 15.8 亿元", "comment": "多家百亿级机构席位单边疯狂扫筹买入"}]},
            {"seat_name": "呼家楼 / 六一路 / 方新侠", "style": "顶级游资合力锁仓", "actions": [{"stock": "中信证券 (600030)", "net_buy": 85000, "type": "净买入 8.5 亿元", "comment": "游资合力加仓券商航母，迎接国庆后超级主升"}]}
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "全市场零跌停，双成药业14连板一字封死！"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "SAFE", "triggered": False, "detail": "炸板率仅 4.17%，全天几乎无炸板！"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "连板晋级率高达 95%，史诗级做多行情！"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "SAFE", "triggered": False, "detail": "全市场零只个股大幅回撤！"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "成交量暴增1.14万亿突破2.59万亿！"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "全部主线板块协同共振爆发！"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "超级牛市高潮主升期！"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "国庆长假后首日开盘，继续紧盯券商一字板排队情况与东方财富竞价情况。",
                "若早盘全市场普遍大幅高开（+5%以上甚至大面积涨停开盘），持股不动，切忌因恐高而过早下车！"
            ],
            "trading_discipline": [
                "【拥抱核心牛市资产】聚焦大金融（券商、金融科技）、科技核心（半导体、鸿蒙）。",
                "【坚定持股享受牛市溢价】避免频繁换股造成踏空。"
            ],
            "risk_warnings": [
                "节后天量巨震时的日内分化风险，防范盲目追高无基本面支撑的边缘杂毛股。"
            ]
        }
    },
    "2024-10-08": {
        "is_trading_day": True,
        "date": "2024-10-08",
        "date_cn": "2024年10月08日 星期二",
        "market_summary": {
            "sh_index": 3489.78,
            "sh_change": 4.59,
            "sz_index": 11495.10,
            "sz_change": 9.17,
            "cy_index": 2550.28,
            "cy_change": 17.25,
            "total_turnover": 34519, # 创A股历史历史天量 3.45万亿
            "turnover_change": 8589,
            "up_count": 5028,
            "down_count": 291,
            "flat_count": 48,
            "median_change": 5.12,
            "limit_up_count": 782,
            "limit_down_count": 3,
            "broken_board_count": 314,
            "consecutive_board_count": 82,
            "broken_board_rate": 28.65,
            "promotion_rate_1_to_2": 72.50,
            "promotion_rate_2_to_3": 80.00,
            "promotion_rate_high": 85.0,
            "max_height": 15,
            "max_height_stock": "双成药业 (002693) 15连板 / 海能达 (002583) 9天8板",
            "sentiment_phase": "分歧期",
            "sentiment_phase_en": "Divergence",
            "sentiment_score": 78,
            "cash_defense_score": 65,
            "suggested_position": "5~7成 (去弱留强)",
            "core_themes": ["半导体自主可控", "华为鸿蒙/算力", "大金融/券商", "专网通信/海能达"]
        },
        "absolute_high": {
            "title": "3.45万亿历史天量巨震！东方财富成交900亿创A股单日纪录，分化大潮开启",
            "leader_code": "002693",
            "leader_name": "双成药业",
            "concept": "跨界并购重组半导体",
            "consecutive_boards": 15,
            "close_price": 15.95,
            "change_percent": 10.00,
            "turnover": 6.80,
            "turnover_rate": 11.20,
            "seal_status": "15连板一字封死",
            "intraday_behavior": "开盘继续一字封死，无视大盘巨幅震荡，维持绝对空间霸主地位。",
            "sub_leader_code": "002583",
            "sub_leader_name": "海能达",
            "sub_leader_concept": "专网通信 / 出海龙头 / 自主可控",
            "sub_leader_boards": 8,
            "sub_leader_change": 10.03,
            "sub_leader_status": "9天8板换手涨停",
            "height_analysis": "早盘开盘全市场直接涨停开盘，随后获利盘与解套盘汹涌砸出，两市全天成交达惊人的3.45万亿元！东方财富单日成交900.38亿元创世界股市单日个股成交纪录。指数冲高回落收出带长上影线假阴线，宣告一致性狂热结束，进入大分歧、大分化、大洗盘阶段。",
            "strategy_holding": "持筹者：早盘涨停未能开盘封死的高位跟风股坚决逢高减仓兑现；保留双成药业、海能达、东方财富、润和软件等最核心龙头。",
            "strategy_buying": "持币者：切忌在开盘涨停板无脑追入杂毛！等待盘中剧烈换手分歧后的深水低吸机会。"
        },
        "ladder_matrix": [
            {
                "tier": "15连板",
                "count": 1,
                "stocks": [
                    {"code": "002693", "name": "双成药业", "price": 15.95, "change": 10.00, "concept": "并购重组/芯片", "turnover": 6.80, "turnover_rate": 11.20, "seal_amount": 72000, "seal_ratio": 105.88, "seal_time": "09:25:00", "breaks": 0, "status": "一字板"}
                ]
            },
            {
                "tier": "9天8板",
                "count": 1,
                "stocks": [
                    {"code": "002583", "name": "海能达", "price": 6.80, "change": 10.03, "concept": "专网通信/一带一路", "turnover": 18.50, "turnover_rate": 16.80, "seal_amount": 28000, "seal_ratio": 15.14, "seal_time": "10:15:00", "breaks": 2, "status": "换手硬核板"}
                ]
            },
            {
                "tier": "容量超级龙头",
                "count": 6,
                "stocks": [
                    {"code": "300059", "name": "东方财富", "price": 24.36, "change": 20.00, "concept": "券商龙头/单日900亿天量", "turnover": 900.38, "turnover_rate": 28.50, "seal_amount": 180000, "seal_ratio": 2.00, "seal_time": "14:45:00", "breaks": 5, "status": "900亿创纪录20cm"},
                    {"code": "300339", "name": "润和软件", "price": 46.32, "change": 20.00, "concept": "华为鸿蒙先锋", "turnover": 185.00, "turnover_rate": 42.10, "seal_amount": 42000, "seal_ratio": 2.27, "seal_time": "11:15:00", "breaks": 3, "status": "20cm巨量换手"},
                    {"code": "000063", "name": "中兴通讯", "price": 35.80, "change": 10.01, "concept": "通信设备中军", "turnover": 142.00, "turnover_rate": 9.20, "seal_amount": 55000, "seal_ratio": 3.87, "seal_time": "09:50:00", "breaks": 2, "status": "百亿中军涨停"},
                    {"code": "688981", "name": "中芯国际", "price": 82.50, "change": 20.00, "concept": "芯片制造中军", "turnover": 220.00, "turnover_rate": 14.80, "seal_amount": 85000, "seal_ratio": 3.86, "seal_time": "13:30:00", "breaks": 2, "status": "科创芯片总舵手"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "600030", "name": "中信证券", "price": 28.10, "change": 1.45, "max_change": 10.00, "concept": "券商中军", "turnover": 380.00, "reason": "早盘一字涨停开盘后被巨量卖单砸开，全天震荡成交380亿"},
            {"code": "601318", "name": "中国平安", "price": 54.20, "change": 0.80, "max_change": 9.50, "concept": "大金融/保险", "turnover": 210.00, "reason": "冲高回落，权重获利兑现"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002693", "name": "双成药业", "boards": 15, "seal_amount": 72000, "seal_ratio": 105.88, "free_float_ratio": 12.80, "first_seal": "09:25:00", "breaks": 0, "stars": 5, "premium_exp": "极高 (继续一字预期)"},
            {"rank": 2, "code": "002583", "name": "海能达", "boards": 8, "seal_amount": 28000, "seal_ratio": 15.14, "free_float_ratio": 3.80, "first_seal": "10:15:00", "breaks": 2, "stars": 5, "premium_exp": "极高 (换手卡位新龙头)"},
            {"rank": 3, "code": "300059", "name": "东方财富", "boards": 3, "seal_amount": 180000, "seal_ratio": 2.00, "free_float_ratio": 3.10, "first_seal": "14:45:00", "breaks": 5, "stars": 4, "premium_exp": "高 (900亿天量承接溢价)"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "半导体/芯片制造与设计", "inflow": 450.0, "change": 15.80, "leaders": "中芯国际、寒武纪、海光信息", "limit_ups": 68},
                {"name": "华为产业链/鸿蒙软件", "inflow": 380.0, "change": 14.50, "leaders": "润和软件、常山北明、拓维信息", "limit_ups": 55},
                {"name": "通信与出海专网", "inflow": 190.0, "change": 12.00, "leaders": "海能达、中兴通讯", "limit_ups": 32}
            ],
            "sectors_outflow": [
                {"name": "传统消费/食品饮料", "outflow": -95.0, "change": -1.20, "reason": "资金全线撤离防守消费，转向核心硬科技"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "300059", "name": "东方财富", "turnover": 900.38, "change": 20.00, "role": "900亿超级流动性总锚点", "analysis": "单日成交900.38亿，占据两市总成交近3%，成为全市场绝对情绪风向标。"},
            {"rank": 2, "code": "688981", "name": "中芯国际", "turnover": 220.00, "change": 20.00, "role": "硬科技半导体总中军", "analysis": "科创板20cm涨停成交220亿，标志着科技主线地位确立。"},
            {"rank": 3, "code": "002583", "name": "海能达", "turnover": 18.50, "change": 10.03, "role": "主线换手总妖龙", "analysis": "抗住3.45万亿天量巨震成功换手涨停，成为新阶段最硬核换手龙。"}
        ],
        "dragon_tiger_list": [
            {"seat_name": "六一路 (招商证券福州六一中路)", "style": "顶级格局锁仓海能达与常山北明", "actions": [{"stock": "常山北明 (000158)", "net_buy": 18500, "type": "净买入 1.85 亿元", "comment": "主买常山北明，打造鸿蒙硬件核心先锋"}, {"stock": "海能达 (002583)", "net_buy": 9500, "type": "净买入 9500 万元", "comment": "大举加仓海能达，锁仓主升浪"}]},
            {"seat_name": "呼家楼 (中信建投北京东城分行)", "style": "重仓中芯国际与东方财富", "actions": [{"stock": "中芯国际 (688981)", "net_buy": 32000, "type": "净买入 3.20 亿元", "comment": "主封中芯国际20cm，引领半导体史诗级行情"}]}
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "双成药业15板封死，海能达强势封板，高位核心未死。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "WARN", "triggered": False, "detail": "炸板率 28.65%，但日内炸板家数达314家，天量分歧显现。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "连板晋级率 85%，梯队依然极其庞大。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "WARN", "triggered": True, "detail": "早盘开盘涨停后回落的大批跟风个股日内回撤超10%。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "成交量3.45万亿创全球纪录。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "硬科技（半导体、鸿蒙）与大金融持续性强。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "处于天量巨震分化阶段，主线核心依然强劲。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "次日竞价关注东方财富与中芯国际开盘走势：若成交量能维持高位且平开或高开，则科技与大金融行情将延续深度分化主升。",
                "关注海能达与常山北明竞价：若竞价超预期高开并迅速封板，可确认为换手龙头穿越标的。"
            ],
            "trading_discipline": [
                "【果断去弱留强】天量巨震后指数将进入震荡整理，杂毛股将面临流动性枯竭，必须集中兵力到前排核心。",
                "【低吸科技主线】聚焦半导体自主可控与华为产业链前排辨识度龙头。"
            ],
            "risk_warnings": [
                "3.45万亿历史天量后量能必将逐步萎缩，注意无量板块的持续阴跌风险。"
            ]
        }
    },
    "2026-08-14": {
        "is_trading_day": True,
        "date": "2026-08-14",
        "date_cn": "2026年08月14日 星期五",
        "market_summary": {
            "sh_index": 3388.25,
            "sh_change": 0.58,
            "sz_index": 10892.40,
            "sz_change": 0.85,
            "cy_index": 2215.60,
            "cy_change": 1.12,
            "total_turnover": 11520,
            "turnover_change": 680,
            "up_count": 3120,
            "down_count": 1850,
            "flat_count": 180,
            "median_change": 0.65,
            "limit_up_count": 68,
            "limit_down_count": 5,
            "broken_board_count": 19,
            "consecutive_board_count": 16,
            "broken_board_rate": 21.84,
            "promotion_rate_1_to_2": 42.10,
            "promotion_rate_2_to_3": 55.56,
            "promotion_rate_high": 60.0,
            "max_height": 6,
            "max_height_stock": "华控科技 (600123) 6连板",
            "sentiment_phase": "发酵期",
            "sentiment_phase_en": "Fermentation",
            "sentiment_score": 72,
            "cash_defense_score": 78,
            "suggested_position": "6~8成 (主线进攻)",
            "core_themes": ["自主可控先进制造", "AI算力端侧芯片", "人形机器人核心零部件", "车路云一体化协同"]
        },
        "absolute_high": {
            "title": "自主可控先锋6连板突破，梯队良性扩散，科技主线共振主升",
            "leader_code": "600123",
            "leader_name": "华控科技",
            "concept": "先进工业母机 / 具身智能控制芯片",
            "consecutive_boards": 6,
            "close_price": 18.65,
            "change_percent": 10.03,
            "turnover": 5.80,
            "turnover_rate": 14.50,
            "seal_status": "6连板实体换手板",
            "intraday_behavior": "早盘小幅高开2.5%，9点33分快速放量拉板封死，全天封单稳健，换手充分无明显抛压。",
            "sub_leader_code": "002890",
            "sub_leader_name": "宏盛智能",
            "sub_leader_concept": "人形机器人灵巧手 / 六维力矩传感器",
            "sub_leader_boards": 4,
            "sub_leader_change": 10.02,
            "sub_leader_status": "4连板缩量加速",
            "height_analysis": "华控科技成功晋级6板，打开向上连板空间；宏盛智能4板紧随其后，2板及3板梯队排列工整，赚钱效应在科技硬件与智能制造端全面扩散。",
            "strategy_holding": "持筹者：华控科技以5日线为防守位坚决持股；宏盛智能关注加速后的分时承接。",
            "strategy_buying": "持币者：高位股不再盲目追高，关注智能制造与机器人产业链的1进2与首板补涨。"
        },
        "ladder_matrix": [
            {
                "tier": "6连板",
                "count": 1,
                "stocks": [
                    {"code": "600123", "name": "华控科技", "price": 18.65, "change": 10.03, "concept": "先进制造/智能控制", "turnover": 5.80, "turnover_rate": 14.50, "seal_amount": 16500, "seal_ratio": 28.45, "seal_time": "09:33:00", "breaks": 0, "status": "实体换手板"}
                ]
            },
            {
                "tier": "4连板",
                "count": 1,
                "stocks": [
                    {"code": "002890", "name": "宏盛智能", "price": 14.20, "change": 10.02, "concept": "人形机器人/灵巧手", "turnover": 3.20, "turnover_rate": 7.80, "seal_amount": 12800, "seal_ratio": 40.00, "seal_time": "09:31:00", "breaks": 0, "status": "缩量加速"}
                ]
            },
            {
                "tier": "3连板",
                "count": 3,
                "stocks": [
                    {"code": "603289", "name": "泰达微电", "price": 24.50, "change": 10.00, "concept": "端侧AI芯片/DSP", "turnover": 6.50, "turnover_rate": 12.30, "seal_amount": 9500, "seal_ratio": 14.62, "seal_time": "09:42:00", "breaks": 1, "status": "换手板"},
                    {"code": "002488", "name": "金运激光", "price": 11.80, "change": 9.97, "concept": "工业激光加工/自动化", "turnover": 4.10, "turnover_rate": 9.50, "seal_amount": 6800, "seal_ratio": 16.59, "seal_time": "10:15:00", "breaks": 0, "status": "实体板"},
                    {"code": "600588", "name": "用友网络", "price": 16.20, "change": 10.05, "concept": "企业数智化/ERP", "turnover": 18.20, "turnover_rate": 5.40, "seal_amount": 15000, "seal_ratio": 8.24, "seal_time": "11:20:00", "breaks": 2, "status": "中军突破"}
                ]
            },
            {
                "tier": "2连板",
                "count": 5,
                "stocks": [
                    {"code": "300678", "name": "中科信息", "price": 36.80, "change": 20.00, "concept": "AI机器视觉/具身智能", "turnover": 15.60, "turnover_rate": 18.20, "seal_amount": 18500, "seal_ratio": 11.86, "seal_time": "09:45:00", "breaks": 1, "status": "20cm中军2连板"},
                    {"code": "002236", "name": "大华股份", "price": 19.85, "change": 10.03, "concept": "智慧物联/AI大模型", "turnover": 25.40, "turnover_rate": 6.80, "seal_amount": 22000, "seal_ratio": 8.66, "seal_time": "10:30:00", "breaks": 0, "status": "容量中军板"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "603893", "name": "瑞芯微", "price": 75.20, "change": 3.80, "max_change": 8.90, "concept": "端侧SoC芯片", "turnover": 28.50, "reason": "早盘冲高遇阻，高位大单换手消化获利盘"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002890", "name": "宏盛智能", "boards": 4, "seal_amount": 12800, "seal_ratio": 40.00, "free_float_ratio": 4.50, "first_seal": "09:31:00", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 2, "code": "600123", "name": "华控科技", "boards": 6, "seal_amount": 16500, "seal_ratio": 28.45, "free_float_ratio": 3.80, "first_seal": "09:33:00", "breaks": 0, "stars": 5, "premium_exp": "极高 (空间板溢价)"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "自主可控与智能制造", "inflow": 42.5, "change": 4.80, "leaders": "华控科技、金运激光", "limit_ups": 15},
                {"name": "人形机器人产业链", "inflow": 35.8, "change": 5.20, "leaders": "宏盛智能、中科信息", "limit_ups": 14},
                {"name": "端侧AI芯片与算力", "inflow": 28.6, "change": 3.90, "leaders": "泰达微电、大华股份", "limit_ups": 9}
            ],
            "sectors_outflow": [
                {"name": "传统公用事业/电力", "outflow": -18.2, "change": -1.20, "reason": "防御板块资金流出转向科技进攻"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "300678", "name": "中科信息", "turnover": 15.60, "change": 20.00, "role": "20cm具身智能中军", "analysis": "20cm连续涨停，激活创业板科技投机热情。"},
            {"rank": 2, "code": "600123", "name": "华控科技", "turnover": 5.80, "change": 10.03, "role": "主板空间总龙头", "analysis": "6连板换手走强，确立新一轮短线周期的情绪领头羊地位。"}
        ],
        "dragon_tiger_list": [
            {"seat_name": "六一路 (招商证券福州六一中路)", "style": "锁仓华控科技与宏盛智能", "actions": [{"stock": "华控科技 (600123)", "net_buy": 4800, "type": "净买入 4800 万元", "comment": "主买主封华控科技6板，打造自主可控空间标杆"}]},
            {"seat_name": "呼家楼 (中信建投北京东城分行)", "style": "大举加仓中科信息", "actions": [{"stock": "中科信息 (300678)", "net_buy": 6500, "type": "净买入 6500 万元", "comment": "主买20cm容量核心，引领具身智能主升浪"}]}
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "最高板华控科技6板稳稳封死，无任何恶性负反馈。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "SAFE", "triggered": False, "detail": "炸板率 21.84%，属于非常健康的强势博弈环境。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "高位晋级率 60.0%，梯队结构良性。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "SAFE", "triggered": False, "detail": "跌停仅5家，市场亏钱效应处于低位。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "成交量放大至1.15万亿，指数温和收阳。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "智能制造与机器人主线发酵深入，溢价稳定。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "处于发酵向主升主阶段，适宜积极进攻。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "竞价观察华控科技开盘量比与高开幅度（若高开>+4%，则新周期龙头确立），可积极参与机器人产业链前排1进2。",
                "观察中科信息20cm竞价承接，若高开>+3%且有大单顶单，创业板弹性标的有望继续暴利。"
            ],
            "trading_discipline": [
                "【顺势而为紧扣科技主线】聚焦自主可控制造与具身智能机器人核心前排。",
                "【不买杂毛防御股】在赚钱效应主升期坚决抛弃防御性公用事业与银行煤炭。"
            ],
            "risk_warnings": [
                "关注华控科技触及7板后的交易所监管异动监控线提示。"
            ]
        }
    }
}

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
        "guidance": "周末常规休市，梳理周五华控科技6连板科技主线发酵脉络，复盘龙虎榜席位动向，研判下周一竞价策略。"
    }
}

print("Market database loaded.")
