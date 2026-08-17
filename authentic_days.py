# -*- coding: utf-8 -*-
"""Authentic public-market snapshots for sample trading days.
Sources: 证券时报·数据宝涨停表, 财联社收评, 每日经济新闻指数播报, 新浪财经日K, 交易所公开信息.
Seal amounts in 万元. Turnover in 亿元. Prices from Sina/STCN close.
Do not invent seats, boards, or turnover not found in those sources.
"""

AUTHENTIC_DAYS = {
    "2024-03-22": {
        "is_trading_day": True,
        "date": "2024-03-22",
        "date_cn": "2024年03月22日 星期五",
        "data_source": "证券时报·数据宝涨停一览、财联社3月22日收评、每日经济新闻指数播报、新浪财经日K、华策影视龙虎榜公开信息。指数/涨停口径截至收盘。",
        "market_summary": {
            "sh_index": 3048.03,
            "sh_change": -0.95,
            "sz_index": 9565.56,
            "sz_change": -1.21,
            "cy_index": 1869.17,
            "cy_change": -1.47,
            "total_turnover": 10973,
            "turnover_change": 296,
            "up_count": 924,
            "down_count": 4389,
            "flat_count": 37,
            "median_change": -1.50,
            "limit_up_count": 67,
            "limit_down_count": 15,
            "broken_board_count": 30,
            "consecutive_board_count": 16,
            "broken_board_rate": 30.93,
            "promotion_rate_1_to_2": 33.0,
            "promotion_rate_2_to_3": 35.0,
            "promotion_rate_high": 0.0,
            "max_height": 6,
            "max_height_stock": "博信股份 (600083) 6连板；艾艾精工13连板断板",
            "sentiment_phase": "分歧期",
            "sentiment_phase_en": "Divergence",
            "sentiment_score": 44,
            "cash_defense_score": 36,
            "suggested_position": "2~4成 (高位去弱、低位试错)",
            "core_themes": ["AI语料/Kimi/传媒", "铜缆高速连接", "机器人/氢能汽车", "低空经济余波"]
        },
        "absolute_high": {
            "title": "艾艾精工13连板断板、永悦科技天地板跌停；博信股份6连板成为新高度",
            "leader_code": "600083",
            "leader_name": "博信股份",
            "concept": "机器人 / AI应用",
            "consecutive_boards": 6,
            "close_price": 11.32,
            "change_percent": 10.01,
            "turnover": 6.33,
            "turnover_rate": 24.51,
            "seal_status": "6连板收盘涨停，封单约5802万元",
            "intraday_behavior": "开盘9.95元后回封11.32元涨停。换手24.51%，封单512.55万股（约5802万元），封成比约9.2%，高度板质量一般。",
            "sub_leader_code": "603580",
            "sub_leader_name": "艾艾精工",
            "sub_leader_concept": "新质生产力 / 轻型输送带",
            "sub_leader_boards": 13,
            "sub_leader_change": -8.03,
            "sub_leader_status": "13连板首日断板，收30.01元，成交9.19亿元，换手22.87%",
            "height_analysis": "空间龙艾艾精工（603580）13连板后收跌8.03%（最高32.75、最低29.44）。低空跟风龙永悦科技（603879）早盘冲高11.52元后天地板收跌停9.43元。短线高度切换至博信股份6连板、动力新科5连板；传媒与铜缆（华策影视20cm三连板、沃尔核材三连板）承接低位资金。全市场924涨/4389跌，67只涨停（含8只ST）、30只封板未遂，封板率69%。",
            "strategy_holding": "持筹者：艾艾精工、永悦科技高位接力盘按断板纪律处理，不幻想无缝反包。博信股份封成比偏弱，只作为高度观察，不宜加仓。",
            "strategy_buying": "持币者：严禁接力13板断板次日。仓位2~4成，只做封单质量明确的低位主线（沃尔核材缩量三板、捷顺科技4.21亿封单首板），避开华策影视52.87亿巨换手弱封20cm。"
        },
        "ladder_matrix": [
            {
                "tier": "13连板（断板）",
                "count": 1,
                "stocks": [
                    {"code": "603580", "name": "艾艾精工", "price": 30.01, "change": -8.03, "concept": "新质生产力/轻型输送带", "turnover": 9.19, "turnover_rate": 22.87, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "--", "breaks": 1, "status": "13板断板"}
                ]
            },
            {
                "tier": "8连板（天地板跌停）",
                "count": 1,
                "stocks": [
                    {"code": "603879", "name": "永悦科技", "price": 9.43, "change": -10.00, "concept": "低空经济/无人机", "turnover": 14.81, "turnover_rate": 21.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "--", "breaks": 1, "status": "天地板收跌停"}
                ]
            },
            {
                "tier": "6连板",
                "count": 1,
                "stocks": [
                    {"code": "600083", "name": "博信股份", "price": 11.32, "change": 10.01, "concept": "机器人/AI", "turnover": 6.33, "turnover_rate": 24.51, "seal_amount": 5802, "seal_ratio": 9.17, "seal_time": "回封", "breaks": 1, "status": "换手板"}
                ]
            },
            {
                "tier": "5连板",
                "count": 1,
                "stocks": [
                    {"code": "600841", "name": "动力新科", "price": 6.97, "change": 10.00, "concept": "氢能源/汽车整车", "turnover": 2.72, "turnover_rate": 4.25, "seal_amount": 7440, "seal_ratio": 27.35, "seal_time": "09:30附近", "breaks": 1, "status": "缩量加速"}
                ]
            },
            {
                "tier": "3连板",
                "count": 5,
                "stocks": [
                    {"code": "300133", "name": "华策影视", "price": 11.06, "change": 20.00, "concept": "Kimi/AI语料/传媒", "turnover": 52.87, "turnover_rate": 32.09, "seal_amount": 366, "seal_ratio": 0.07, "seal_time": "13:24", "breaks": 1, "status": "20cm巨换手弱封"},
                    {"code": "002130", "name": "沃尔核材", "price": 9.99, "change": 10.00, "concept": "铜缆高速连接", "turnover": 2.61, "turnover_rate": 2.09, "seal_amount": 32314, "seal_ratio": 123.81, "seal_time": "09:25", "breaks": 0, "status": "一字强封"},
                    {"code": "603533", "name": "掌阅科技", "price": 32.49, "change": 10.00, "concept": "Kimi/数字阅读", "turnover": 8.84, "turnover_rate": 6.20, "seal_amount": 22490, "seal_ratio": 25.44, "seal_time": "09:30附近", "breaks": 0, "status": "实体板"},
                    {"code": "603721", "name": "中广天择", "price": 42.59, "change": 10.00, "concept": "传媒/知识产权", "turnover": 15.73, "turnover_rate": 28.41, "seal_amount": 9184, "seal_ratio": 5.84, "seal_time": "11:09", "breaks": 1, "status": "换手回封"},
                    {"code": "600165", "name": "宁科生物", "price": 3.01, "change": 10.00, "concept": "化工/生物", "turnover": 0.20, "turnover_rate": 0.97, "seal_amount": 5998, "seal_ratio": 299.90, "seal_time": "09:25", "breaks": 0, "status": "一字缩量"}
                ]
            },
            {
                "tier": "2连板（公开点名）",
                "count": 4,
                "stocks": [
                    {"code": "002553", "name": "南方精工", "price": 14.37, "change": 10.00, "concept": "汽车零部件", "turnover": 1.49, "turnover_rate": 4.36, "seal_amount": 16598, "seal_ratio": 111.40, "seal_time": "一字/秒板", "breaks": 0, "status": "强封"},
                    {"code": "600243", "name": "青海华鼎", "price": 4.69, "change": 10.00, "concept": "机械设备", "turnover": 2.34, "turnover_rate": 11.39, "seal_amount": 3172, "seal_ratio": 13.56, "seal_time": "换手", "breaks": 0, "status": "换手板"},
                    {"code": "605180", "name": "华生科技", "price": 12.79, "change": 10.00, "concept": "纺织/低空材料", "turnover": 0.25, "turnover_rate": 4.05, "seal_amount": 7112, "seal_ratio": 284.48, "seal_time": "09:25", "breaks": 0, "status": "一字板"},
                    {"code": "301025", "name": "读客文化", "price": 13.81, "change": 20.00, "concept": "数字阅读/传媒", "turnover": 5.76, "turnover_rate": 42.03, "seal_amount": 228, "seal_ratio": 0.40, "seal_time": "回封", "breaks": 1, "status": "20cm高换手弱封"}
                ]
            },
            {
                "tier": "首板封单最强（数据宝）",
                "count": 3,
                "stocks": [
                    {"code": "002609", "name": "捷顺科技", "price": 11.07, "change": 10.00, "concept": "计算机/智慧停车", "turnover": 6.35, "turnover_rate": 12.57, "seal_amount": 42124, "seal_ratio": 66.34, "seal_time": "回封", "breaks": 1, "status": "全场封单金额第1"},
                    {"code": "000903", "name": "云内动力", "price": 2.71, "change": 10.00, "concept": "汽车", "turnover": 1.20, "turnover_rate": 6.72, "seal_amount": 8613, "seal_ratio": 71.78, "seal_time": "强封", "breaks": 0, "status": "封单量前列"},
                    {"code": "300738", "name": "奥飞数据", "price": 12.13, "change": 10.00, "concept": "通信/数据中心", "turnover": 3.50, "turnover_rate": 17.01, "seal_amount": 10063, "seal_ratio": 28.75, "seal_time": "换手", "breaks": 0, "status": "通信首板"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "603580", "name": "艾艾精工", "price": 30.01, "change": -8.03, "max_change": 0.37, "concept": "13连板空间龙", "turnover": 9.19, "reason": "13连板后首日断板，最高32.75元未能回封，高位获利盘兑现"},
            {"code": "603879", "name": "永悦科技", "price": 9.43, "change": -10.00, "max_change": 10.00, "concept": "低空经济8连板", "turnover": 14.81, "reason": "早盘冲涨停后天地板封死跌停，公司提示无人机合同履约重大不确定性"},
            {"code": "300133", "name": "华策影视", "price": 11.06, "change": 20.00, "max_change": 20.00, "concept": "Kimi/20cm三板", "turnover": 52.87, "reason": "虽收20cm但封单仅366万元、换手32%，机构席位净卖约2.18亿元，质量极差"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002130", "name": "沃尔核材", "boards": 3, "seal_amount": 32314, "seal_ratio": 123.81, "free_float_ratio": 2.50, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（一字铜缆三板）"},
            {"rank": 2, "code": "002609", "name": "捷顺科技", "boards": 1, "seal_amount": 42124, "seal_ratio": 66.34, "free_float_ratio": 3.80, "first_seal": "回封", "breaks": 1, "stars": 5, "premium_exp": "高（全场封单金额最大4.21亿）"},
            {"rank": 3, "code": "605180", "name": "华生科技", "boards": 2, "seal_amount": 7112, "seal_ratio": 284.48, "free_float_ratio": 4.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "高（一字缩量2板）"},
            {"rank": 4, "code": "600165", "name": "宁科生物", "boards": 3, "seal_amount": 5998, "seal_ratio": 299.90, "free_float_ratio": 3.00, "first_seal": "09:25", "breaks": 0, "stars": 4, "premium_exp": "高（一字缩量）"},
            {"rank": 5, "code": "603533", "name": "掌阅科技", "boards": 3, "seal_amount": 22490, "seal_ratio": 25.44, "free_float_ratio": 1.50, "first_seal": "09:30附近", "breaks": 0, "stars": 4, "premium_exp": "中高（Kimi核心）"},
            {"rank": 6, "code": "600841", "name": "动力新科", "boards": 5, "seal_amount": 7440, "seal_ratio": 27.35, "free_float_ratio": 1.20, "first_seal": "09:30附近", "breaks": 1, "stars": 3, "premium_exp": "中（5板加速）"},
            {"rank": 7, "code": "600083", "name": "博信股份", "boards": 6, "seal_amount": 5802, "seal_ratio": 9.17, "free_float_ratio": 0.80, "first_seal": "回封", "breaks": 1, "stars": 3, "premium_exp": "中低（高度但封成比弱）"},
            {"rank": 8, "code": "300133", "name": "华策影视", "boards": 3, "seal_amount": 366, "seal_ratio": 0.07, "free_float_ratio": 0.05, "first_seal": "13:24", "breaks": 1, "stars": 1, "premium_exp": "极低（52.87亿天量弱封）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "传媒/AI语料", "inflow": 19.0, "change": 4.00, "leaders": "华策影视、掌阅科技、中广天择、读客文化", "limit_ups": 11},
                {"name": "铜缆高速连接/电子", "inflow": 15.0, "change": 2.90, "leaders": "沃尔核材、胜蓝股份、鼎通科技", "limit_ups": 8},
                {"name": "计算机", "inflow": 8.0, "change": 1.50, "leaders": "捷顺科技、云赛智联", "limit_ups": 6}
            ],
            "sectors_outflow": [
                {"name": "贵金属/有色", "outflow": -20.0, "change": -2.00, "reason": "财联社：贵金属、小金属板块跌幅居前"},
                {"name": "高位低空跟风", "outflow": -15.0, "change": -8.00, "reason": "永悦科技天地板跌停，低空余波兑现"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "300133", "name": "华策影视", "turnover": 52.87, "change": 20.00, "role": "传媒20cm成交锚点", "analysis": "成交52.87亿元、换手32.09%，是当日短线成交最大的连板股，但封单仅366万元，机构净卖约2.18亿。"},
            {"rank": 2, "code": "603580", "name": "艾艾精工", "turnover": 9.19, "change": -8.03, "role": "空间龙断板风向标", "analysis": "13连板后放量9.19亿断板，决定高位情绪是否进入负反馈。"},
            {"rank": 3, "code": "603879", "name": "永悦科技", "turnover": 14.81, "change": -10.00, "role": "低空跟风核按钮", "analysis": "天地板跌停，低空经济从主线退化为余波。"},
            {"rank": 4, "code": "002609", "name": "捷顺科技", "turnover": 6.35, "change": 10.00, "role": "封单金额冠军", "analysis": "数据宝：涨停封单4.21亿元居两市第一。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "机构专用席位 / 深股通（华策影视）",
                "style": "高位20cm兑现",
                "actions": [
                    {"stock": "华策影视 (300133)", "net_buy": -21800, "type": "2家机构合计净卖出约2.18亿元", "comment": "20cm三连板当日机构大幅兑现；深股通买入8115.20万元、卖出5346.65万元"},
                    {"stock": "华策影视 (300133)", "net_buy": -5523, "type": "方新侠（中信证券西安朱雀大街）净卖出5523.08万元", "comment": "游资席位同步出货，与弱封单互相印证"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "DANGER", "triggered": True, "detail": "艾艾精工13板断板-8.03%；永悦科技8板天地板跌停。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "WARN", "triggered": True, "detail": "数据宝：67涨停、30封板未遂，炸板率30.93%，封板率69%。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "DANGER", "triggered": True, "detail": "8板及以上全部断板，高位晋级率为0；新高度仅博信6板、动力新科5板。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "WARN", "triggered": True, "detail": "永悦科技天地板跌停，高位跟风出现核按钮。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "沪指3048.03点-0.95%，两市成交10973亿元较前日放量296亿，量能未缩。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "WARN", "triggered": True, "detail": "低空跟风核按钮，资金切向传媒/铜缆，高低切明显。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "尚未全面杀中位：博信、动力新科、沃尔核材、掌阅仍在连板，属高位分歧+低位切换。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "先看永悦科技跌停封单：若继续封死，低空跟风一律放弃。",
                "艾艾精工竞价若不能大幅高开回封，13板二波不做。",
                "华策影视52.87亿弱封，竞价高开>5%不追；沃尔核材一字质量是铜缆试金石。"
            ],
            "trading_discipline": [
                "仓位2~4成。高位只减不加。",
                "不打华策影视这类天量弱封20cm。优先一字/高封成比（沃尔核材、华生科技、宁科生物）。"
            ],
            "risk_warnings": [
                "924/4389的涨跌比已是普跌结构，指数若再失3000点附近，短线会从分歧滑向退潮。",
                "博信股份6板封成比仅9%，高度与质量背离。"
            ]
        }
    },
    "2024-03-25": {
        "is_trading_day": True,
        "date": "2024-03-25",
        "date_cn": "2024年03月25日 星期一",
        "data_source": "证券时报·数据宝3月25日涨停一览、每日经济新闻/中国经济网收评、新浪财经日K、博信股份龙虎榜与异常波动公告。",
        "market_summary": {
            "sh_index": 3026.31,
            "sh_change": -0.71,
            "sz_index": 9422.61,
            "sz_change": -1.49,
            "cy_index": 1833.44,
            "cy_change": -1.91,
            "total_turnover": 10434,
            "turnover_change": -539,
            "up_count": 732,
            "down_count": 4550,
            "flat_count": 68,
            "median_change": -2.43,
            "limit_up_count": 46,
            "limit_down_count": 41,
            "broken_board_count": 22,
            "consecutive_board_count": 8,
            "broken_board_rate": 32.35,
            "promotion_rate_1_to_2": 20.0,
            "promotion_rate_2_to_3": 44.0,
            "promotion_rate_high": 50.0,
            "max_height": 7,
            "max_height_stock": "博信股份 (600083) 7连板地天板",
            "sentiment_phase": "退潮期",
            "sentiment_phase_en": "Recession",
            "sentiment_score": 28,
            "cash_defense_score": 18,
            "suggested_position": "0~2成 (严格防守)",
            "core_themes": ["抱团空间龙艾艾精工反包", "机器人/博信股份地天板", "油气开采防御", "Kimi传媒杀跌"]
        },
        "absolute_high": {
            "title": "普跌4550家、41只跌停；博信股份7连板地天板，艾艾精工反包涨停",
            "leader_code": "600083",
            "leader_name": "博信股份",
            "concept": "机器人 / AI",
            "consecutive_boards": 7,
            "close_price": 12.45,
            "change_percent": 9.98,
            "turnover": 12.37,
            "turnover_rate": 46.32,
            "seal_status": "7连板收盘涨停，但是地天板，封单仅1099万元",
            "intraday_behavior": "开盘11.89元后最低10.19元（触及跌停附近）再拉回12.45元涨停，振幅22.18%，换手46.32%，成交12.37亿元。营业部席位合计净卖出1.33亿元。",
            "sub_leader_code": "603580",
            "sub_leader_name": "艾艾精工",
            "sub_leader_concept": "新质生产力 / 空间龙反包",
            "sub_leader_boards": 0,
            "sub_leader_change": 10.00,
            "sub_leader_status": "断板后次日反包涨停33.01元，换手23.35%，成交9.53亿元，封单3796万元",
            "height_analysis": "不是永悦/艾艾双双跌停：艾艾精工反包涨停创阶段新高；永悦科技续跌停8.49元；动力新科5板晋级失败收跌停6.27元。3进4仅宁科生物成功（3.31元），华策影视-12.93%、中广天择跌停、掌阅科技冲涨停回落-5.97%。涨停46（含4只ST）、跌停41，上涨仅732家，典型退潮+抱团龙头。",
            "strategy_holding": "持筹者：永悦科技、动力新科、华策影视、中广天择按核按钮离场。博信股份地天板封单只有约1100万，次日不接力。艾艾精工反包属于龙头二波观察，不加杠杆。",
            "strategy_buying": "持币者：0~2成。退潮期不打地天板高度股。若做，只看艾艾精工能否继续缩量，不参与Kimi断板股抄底。"
        },
        "ladder_matrix": [
            {
                "tier": "7连板（地天板）",
                "count": 1,
                "stocks": [
                    {"code": "600083", "name": "博信股份", "price": 12.45, "change": 9.98, "concept": "机器人/AI", "turnover": 12.37, "turnover_rate": 46.32, "seal_amount": 1099, "seal_ratio": 0.89, "seal_time": "尾盘回封", "breaks": 1, "status": "地天板弱封"}
                ]
            },
            {
                "tier": "4连板",
                "count": 1,
                "stocks": [
                    {"code": "600165", "name": "宁科生物", "price": 3.31, "change": 10.00, "concept": "化工", "turnover": 2.42, "turnover_rate": 10.70, "seal_amount": 7783, "seal_ratio": 32.16, "seal_time": "回封", "breaks": 1, "status": "3进4换手"}
                ]
            },
            {
                "tier": "3连板（公开可核对）",
                "count": 4,
                "stocks": [
                    {"code": "605180", "name": "华生科技", "price": 14.07, "change": 10.00, "concept": "纺织/低空材料", "turnover": 0.28, "turnover_rate": 4.13, "seal_amount": 8720, "seal_ratio": 311.43, "seal_time": "09:25", "breaks": 0, "status": "一字板"},
                    {"code": "600243", "name": "青海华鼎", "price": 5.16, "change": 10.00, "concept": "机械设备", "turnover": 1.69, "turnover_rate": 7.44, "seal_amount": 10833, "seal_ratio": 64.10, "seal_time": "强封", "breaks": 0, "status": "缩量板"},
                    {"code": "603499", "name": "翔港科技", "price": 24.34, "change": 10.00, "concept": "包装/电子", "turnover": 0.61, "turnover_rate": 1.00, "seal_amount": 6135, "seal_ratio": 100.57, "seal_time": "一字", "breaks": 0, "status": "缩量3板"},
                    {"code": "002735", "name": "王子新材", "price": 15.96, "change": 10.00, "concept": "轻工/跟风", "turnover": 5.91, "turnover_rate": 37.04, "seal_amount": 1113, "seal_ratio": 1.88, "seal_time": "回封", "breaks": 1, "status": "高换手弱封"}
                ]
            },
            {
                "tier": "空间龙反包 / 封单金额前列",
                "count": 4,
                "stocks": [
                    {"code": "603580", "name": "艾艾精工", "price": 33.01, "change": 10.00, "concept": "空间龙反包（非连板）", "turnover": 9.53, "turnover_rate": 23.35, "seal_amount": 3796, "seal_ratio": 3.98, "seal_time": "尾盘", "breaks": 1, "status": "断板次日反包"},
                    {"code": "603688", "name": "石英股份", "price": 91.31, "change": 10.00, "concept": "石英材料", "turnover": 3.50, "turnover_rate": 3.85, "seal_amount": 18779, "seal_ratio": 53.65, "seal_time": "强封", "breaks": 0, "status": "封单金额第1"},
                    {"code": "002722", "name": "物产金轮", "price": 13.87, "change": 10.00, "concept": "纺织服饰", "turnover": 0.80, "turnover_rate": 1.70, "seal_amount": 17033, "seal_ratio": 212.91, "seal_time": "一字", "breaks": 0, "status": "封单金额第2"},
                    {"code": "603389", "name": "亚振家居", "price": 6.20, "change": 10.00, "concept": "家居", "turnover": 1.20, "turnover_rate": 14.75, "seal_amount": 2987, "seal_ratio": 24.89, "seal_time": "回封", "breaks": 0, "status": "2进3"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "600841", "name": "动力新科", "price": 6.27, "change": -10.04, "max_change": -5.16, "concept": "昨5连板", "turnover": 1.35, "reason": "5进6失败，开盘即6.27附近并收跌停"},
            {"code": "603879", "name": "永悦科技", "price": 8.49, "change": -9.97, "max_change": -4.35, "concept": "低空8板后连续跌停", "turnover": 8.95, "reason": "周五天地板后周一续跌停"},
            {"code": "300133", "name": "华策影视", "price": 9.63, "change": -12.93, "max_change": -5.07, "concept": "Kimi/昨20cm三板", "turnover": 39.77, "reason": "20cm弱封次日大面，最高仅10.50元"},
            {"code": "603721", "name": "中广天择", "price": 38.33, "change": -10.00, "max_change": 0.96, "concept": "传媒三板", "turnover": 11.88, "reason": "开盘冲高43.00后跌停"},
            {"code": "603533", "name": "掌阅科技", "price": 30.55, "change": -5.97, "max_change": 10.00, "concept": "Kimi三板", "turnover": 31.92, "reason": "高开35.74涨停价后砸至29.51，收-5.97%"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "605180", "name": "华生科技", "boards": 3, "seal_amount": 8720, "seal_ratio": 311.43, "free_float_ratio": 4.50, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "高（一字3板）"},
            {"rank": 2, "code": "603688", "name": "石英股份", "boards": 1, "seal_amount": 18779, "seal_ratio": 53.65, "free_float_ratio": 1.80, "first_seal": "强封", "breaks": 0, "stars": 4, "premium_exp": "中高（封单金额最大）"},
            {"rank": 3, "code": "002722", "name": "物产金轮", "boards": 1, "seal_amount": 17033, "seal_ratio": 212.91, "free_float_ratio": 3.00, "first_seal": "一字", "breaks": 0, "stars": 4, "premium_exp": "中高"},
            {"rank": 4, "code": "600243", "name": "青海华鼎", "boards": 3, "seal_amount": 10833, "seal_ratio": 64.10, "free_float_ratio": 3.50, "first_seal": "强封", "breaks": 0, "stars": 4, "premium_exp": "中高"},
            {"rank": 5, "code": "600165", "name": "宁科生物", "boards": 4, "seal_amount": 7783, "seal_ratio": 32.16, "free_float_ratio": 2.00, "first_seal": "回封", "breaks": 1, "stars": 3, "premium_exp": "中"},
            {"rank": 6, "code": "603580", "name": "艾艾精工", "boards": 1, "seal_amount": 3796, "seal_ratio": 3.98, "free_float_ratio": 0.80, "first_seal": "尾盘", "breaks": 1, "stars": 3, "premium_exp": "中（龙头反包但封成比一般）"},
            {"rank": 7, "code": "600083", "name": "博信股份", "boards": 7, "seal_amount": 1099, "seal_ratio": 0.89, "free_float_ratio": 0.40, "first_seal": "尾盘", "breaks": 1, "stars": 1, "premium_exp": "极低（地天板+营业部净卖1.33亿）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "油气开采及服务", "inflow": 8.0, "change": 1.70, "leaders": "贝肯能源、准油股份", "limit_ups": 3},
                {"name": "银行/红利防御", "inflow": 7.0, "change": 0.80, "leaders": "银行板块领涨", "limit_ups": 0}
            ],
            "sectors_outflow": [
                {"name": "传媒/Kimi/AI语料", "outflow": -50.0, "change": -6.00, "reason": "华策影视-12.93%，掌阅科技冲板回落，中广天择跌停"},
                {"name": "半导体及元件", "outflow": -25.0, "change": -3.00, "reason": "收评：半导体及元件跌幅居前"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "600083", "name": "博信股份", "turnover": 12.37, "change": 9.98, "role": "高度地天板", "analysis": "成交12.37亿、换手46.32%，营业部净卖1.33亿，高度与质量严重背离。"},
            {"rank": 2, "code": "603580", "name": "艾艾精工", "turnover": 9.53, "change": 10.00, "role": "空间龙反包", "analysis": "普跌市中尾盘封板，是退潮期唯一有号召力的老龙头。"},
            {"rank": 3, "code": "300133", "name": "华策影视", "turnover": 39.77, "change": -12.93, "role": "Kimi负反馈锚点", "analysis": "昨日天量20cm今日大面，传媒主线中断。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "营业部席位合计（博信股份）",
                "style": "地天板高位兑现",
                "actions": [
                    {"stock": "博信股份 (600083)", "net_buy": -13300, "type": "营业部席位合计净卖出1.33亿元", "comment": "因振幅22.18%、换手46.32%上榜；7连板当日游资净卖，封单仅约1100万元"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "DANGER", "triggered": True, "detail": "永悦科技续跌停；动力新科5板跌停；华策影视-12.93%；中广天择跌停。艾艾精工反包不能掩盖跟风核按钮。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "WARN", "triggered": True, "detail": "涨停仅46、跌停41；已知冲板回落包括掌阅科技、南方精工等高开品种，亏钱效应大于封板。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "DANGER", "triggered": True, "detail": "5进6为0（动力新科跌停）；3进4仅宁科生物，华策/掌阅/中广/沃尔核材均未晋级涨停。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "DANGER", "triggered": True, "detail": "博信股份地天板；动力新科、永悦科技、中广天择跌停；华策影视-13%。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "WARN", "triggered": True, "detail": "沪指3026.31点-0.71%；成交10434亿，较周五缩量539亿。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "DANGER", "triggered": True, "detail": "Kimi三板次日集体大面，典型退潮计提。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "DANGER", "triggered": True, "detail": "4550家下跌、41只跌停，符合退潮杀中位；仅抱团艾艾精工与弱封博信。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "永悦科技、动力新科、中广天择若继续跌停，中高位一律空仓。",
                "博信股份地天板次日高开不追、低开不抄。",
                "艾艾精工若平开或低开翻绿，龙头二波结束。"
            ],
            "trading_discipline": [
                "空仓是默认选项，仓位0~2成。",
                "不抄Kimi断板股，不接力地天板。"
            ],
            "risk_warnings": [
                "博信股份已发严重异常波动提示，7连板累计涨幅偏离行业。",
                "涨跌比732/4550，指数失守3030后短线容量会继续收缩。"
            ]
        }
    },
    "2024-04-18": {
        "is_trading_day": True,
        "date": "2024-04-18",
        "date_cn": "2024年04月18日 星期四",
        "data_source": "证券时报·数据宝4月18日揭秘涨停/资金复盘、每日经济新闻指数播报、金投网涨停表、新浪财经日K、中信海直龙虎榜公开信息。",
        "market_summary": {
            "sh_index": 3074.22,
            "sh_change": 0.09,
            "sz_index": 9376.81,
            "sz_change": -0.05,
            "cy_index": 1787.49,
            "cy_change": -0.55,
            "total_turnover": 9496,
            "turnover_change": 312,
            "up_count": 1995,
            "down_count": 3004,
            "flat_count": 113,
            "median_change": -0.30,
            "limit_up_count": 70,
            "limit_down_count": 40,
            "broken_board_count": 27,
            "consecutive_board_count": 25,
            "broken_board_rate": 27.84,
            "promotion_rate_1_to_2": 40.0,
            "promotion_rate_2_to_3": 50.0,
            "promotion_rate_high": 66.0,
            "max_height": 5,
            "max_height_stock": "同为股份 (002835) / 春光科技 (603657) 5连板",
            "sentiment_phase": "修复期",
            "sentiment_phase_en": "Repair",
            "sentiment_score": 58,
            "cash_defense_score": 62,
            "suggested_position": "4~6成 (主线试错，提防40只跌停)",
            "core_themes": ["低空经济/eVTOL", "业绩预增/安防", "家电出口", "有色铜钴"]
        },
        "absolute_high": {
            "title": "同为股份、春光科技双双5连板；中信海直7天4板，哈三联天地板",
            "leader_code": "002835",
            "leader_name": "同为股份",
            "concept": "一季报预增 / 安防监控",
            "consecutive_boards": 5,
            "close_price": 21.87,
            "change_percent": 10.01,
            "turnover": 0.26,
            "turnover_rate": 1.20,
            "seal_status": "一字5连板，封单2.80亿元",
            "intraday_behavior": "开盘即21.87元一字封死，成交约0.26亿元，封单1280.31万股（2.80亿元），封成比极高。公司一季度预告净利润同比增长339%~455%。",
            "sub_leader_code": "603657",
            "sub_leader_name": "春光科技",
            "sub_leader_concept": "家电出口 / 吸尘器ODM",
            "sub_leader_boards": 5,
            "sub_leader_change": 9.99,
            "sub_leader_status": "一字5连板19.71元，封单1.89亿元",
            "height_analysis": "数据宝：70只涨停（剔ST后63只）、27只封板未遂，封板率72.16%；40只跌停。高度为同为股份、春光科技5连板，中公高科4连板（38.08元低开回封），建研院3连板，中信海直7天4板（20.24元，封单2.15亿）。低空方向涨停还有金盾股份、安达维尔、威海广泰、万安科技。哈三联开盘14.40元后收12.29元，盘中天地板。",
            "strategy_holding": "持筹者：同为、春光一字不爆量可持有；中信海直32.9亿换手板按5日线管理。哈三联一类中位一字不碰。",
            "strategy_buying": "持币者：高位一字买不到。只做低空辨识度前排弱转强或首板，仓位4~6成，记住当天有40只跌停。"
        },
        "ladder_matrix": [
            {
                "tier": "5连板",
                "count": 2,
                "stocks": [
                    {"code": "002835", "name": "同为股份", "price": 21.87, "change": 10.01, "concept": "业绩预增/安防", "turnover": 0.26, "turnover_rate": 1.20, "seal_amount": 28000, "seal_ratio": 1076.92, "seal_time": "09:25", "breaks": 0, "status": "一字死封"},
                    {"code": "603657", "name": "春光科技", "price": 19.71, "change": 9.99, "concept": "家电出口", "turnover": 0.21, "turnover_rate": 1.10, "seal_amount": 18900, "seal_ratio": 900.00, "seal_time": "09:25", "breaks": 0, "status": "一字死封"}
                ]
            },
            {
                "tier": "4连板 / 7天4板",
                "count": 2,
                "stocks": [
                    {"code": "603860", "name": "中公高科", "price": 38.08, "change": 10.00, "concept": "中字头/公路检测", "turnover": 4.68, "turnover_rate": 12.00, "seal_amount": 8000, "seal_ratio": 17.09, "seal_time": "弱转强回封", "breaks": 1, "status": "低开回封4板"},
                    {"code": "000099", "name": "中信海直", "price": 20.24, "change": 10.00, "concept": "低空运营/7天4板", "turnover": 32.86, "turnover_rate": 22.80, "seal_amount": 21500, "seal_ratio": 6.54, "seal_time": "09:36附近", "breaks": 1, "status": "容量换手板"}
                ]
            },
            {
                "tier": "3连板 / 2连板公开点名",
                "count": 3,
                "stocks": [
                    {"code": "603183", "name": "建研院", "price": 4.42, "change": 9.95, "concept": "专业服务", "turnover": 0.30, "turnover_rate": 3.50, "seal_amount": 6537, "seal_ratio": 217.90, "seal_time": "一字/秒板", "breaks": 0, "status": "3连板"},
                    {"code": "002590", "name": "万安科技", "price": 13.35, "change": 9.97, "concept": "汽车/低空", "turnover": 1.41, "turnover_rate": 4.80, "seal_amount": 8962, "seal_ratio": 63.56, "seal_time": "强封", "breaks": 0, "status": "2连板"},
                    {"code": "000737", "name": "北方铜业", "price": 10.30, "change": 10.00, "concept": "有色/铜", "turnover": 18.44, "turnover_rate": 12.00, "seal_amount": 18356, "seal_ratio": 9.95, "seal_time": "回封", "breaks": 1, "status": "封单量17.82万手"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "002900", "name": "哈三联", "price": 12.29, "change": -6.11, "max_change": 10.00, "concept": "中位加速", "turnover": 4.66, "reason": "开盘14.40元（涨停价）后天地板，收12.29元，中位一字大面"},
            {"code": "300284", "name": "苏交科", "price": 9.78, "change": 6.30, "max_change": 12.83, "concept": "低空基建", "turnover": 29.09, "reason": "盘中最高10.38元未封20cm，收9.78元冲高回落"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002835", "name": "同为股份", "boards": 5, "seal_amount": 28000, "seal_ratio": 1076.92, "free_float_ratio": 8.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（一字+预增）"},
            {"rank": 2, "code": "603657", "name": "春光科技", "boards": 5, "seal_amount": 18900, "seal_ratio": 900.00, "free_float_ratio": 6.50, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 3, "code": "000099", "name": "中信海直", "boards": 4, "seal_amount": 21500, "seal_ratio": 6.54, "free_float_ratio": 1.80, "first_seal": "09:36附近", "breaks": 1, "stars": 4, "premium_exp": "中高（容量低空中军）"},
            {"rank": 4, "code": "000737", "name": "北方铜业", "boards": 1, "seal_amount": 18356, "seal_ratio": 9.95, "free_float_ratio": 1.50, "first_seal": "回封", "breaks": 1, "stars": 4, "premium_exp": "中（封单量最大）"},
            {"rank": 5, "code": "002590", "name": "万安科技", "boards": 2, "seal_amount": 8962, "seal_ratio": 63.56, "free_float_ratio": 2.20, "first_seal": "强封", "breaks": 0, "stars": 4, "premium_exp": "中高"},
            {"rank": 6, "code": "603860", "name": "中公高科", "boards": 4, "seal_amount": 8000, "seal_ratio": 17.09, "free_float_ratio": 1.50, "first_seal": "弱转强", "breaks": 1, "stars": 3, "premium_exp": "中（低开回封卡位）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "小金属/基本金属", "inflow": 16.0, "change": 2.50, "leaders": "北方铜业、腾远钴业、东方锆业", "limit_ups": 6},
                {"name": "低空经济/飞行汽车", "inflow": 12.0, "change": 2.87, "leaders": "中信海直、万安科技、金盾股份", "limit_ups": 8},
                {"name": "非银金融/券商", "inflow": 4.3, "change": 1.20, "leaders": "券商概念资金流入居前", "limit_ups": 2}
            ],
            "sectors_outflow": [
                {"name": "电力/公用事业", "outflow": -19.0, "change": -1.87, "reason": "行业跌幅居前"},
                {"name": "北向资金", "outflow": -52.85, "change": 0.00, "reason": "北上资金当日净流出52.85亿元"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "000099", "name": "中信海直", "turnover": 32.86, "change": 10.00, "role": "低空容量中军", "analysis": "成交约33亿元、封单2.15亿，华泰天津东丽开发区二纬路净买6519.25万元；深股通净卖2513.46万元。"},
            {"rank": 2, "code": "002835", "name": "同为股份", "turnover": 0.26, "change": 10.01, "role": "业绩高度龙", "analysis": "一字5板封单2.8亿，是短线空间锚。"},
            {"rank": 3, "code": "300284", "name": "苏交科", "turnover": 29.09, "change": 6.30, "role": "低空跟风天量", "analysis": "成交约29亿未封住20cm，容量分流中信海直溢价。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "华泰证券天津东丽开发区二纬路",
                "style": "低空中军打板",
                "actions": [
                    {"stock": "中信海直 (000099)", "net_buy": 6519, "type": "净买入6519.25万元", "comment": "数据宝龙虎看台：游资主买低空运营龙头"}
                ]
            },
            {
                "seat_name": "机构专用席位",
                "style": "净买入额前列",
                "actions": [
                    {"stock": "软控股份", "net_buy": 15700, "type": "机构净买入1.57亿元", "comment": "当日机构专用席位净买入额第一"},
                    {"stock": "灿芯股份", "net_buy": 6434, "type": "机构净买入6433.59万元", "comment": "机构净买入额第二"},
                    {"stock": "中润资源", "net_buy": 3770, "type": "机构净买入3770.38万元", "comment": "机构净买入额第三"}
                ]
            },
            {
                "seat_name": "中国银河证券北京中关村大街 / 深股通",
                "style": "有色与低空分歧",
                "actions": [
                    {"stock": "北方铜业 (000737)", "net_buy": -1971, "type": "中关村大街净卖出1971.29万元", "comment": "铜业封单量最大，该席位有兑现"},
                    {"stock": "中信海直 (000099)", "net_buy": -2513, "type": "深股通净卖出2513.46万元", "comment": "北向与游资方向不一致"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "同为股份、春光科技一字5板，高度未断。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "SAFE", "triggered": False, "detail": "27只封板未遂，炸板率27.84%，封板率72.16%。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "4进5成功（同为、春光），中公高科3进4，高位仍在扩张。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "WARN", "triggered": True, "detail": "哈三联天地板；全市场仍有40只跌停，不是纯修复市。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "沪指3074.22点+0.09%，成交9496亿放量312亿。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "低空与业绩主线连续，不是一日游。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "属于修复/升温，但3004家下跌+40跌停，仓位不宜打满。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "同为股份、春光科技继续看一字封单，低于亿级则高度降温。",
                "中信海直竞价高开3%~6%可沿分时，>8%不追。",
                "哈三联类天地板次日低开不抄。"
            ],
            "trading_discipline": [
                "只做低空或业绩两条主线之一，不铺开。",
                "中位一字（哈三联教训）默认放弃。"
            ],
            "risk_warnings": [
                "北向净流出52.85亿，指数3100点附近有压力。",
                "40只跌停说明冰点并未完全结束，修复不等于全面进攻。"
            ]
        }
    },
    "2024-09-30": {
        "is_trading_day": True,
        "date": "2024-09-30",
        "date_cn": "2024年09月30日 星期一",
        "data_source": "每日经济新闻/钛媒体收盘统计、北京日报成交纪录、证券时报双成药业行情、证券之星东方财富资金、新浪财经日K。涨停约数为公开报道。",
        "market_summary": {
            "sh_index": 3336.50,
            "sh_change": 8.06,
            "sz_index": 10529.76,
            "sz_change": 10.67,
            "cy_index": 2175.09,
            "cy_change": 15.36,
            "total_turnover": 25930,
            "turnover_change": 11470,
            "up_count": 5330,
            "down_count": 8,
            "flat_count": 12,
            "median_change": 8.50,
            "limit_up_count": 700,
            "limit_down_count": 0,
            "broken_board_count": 20,
            "consecutive_board_count": 80,
            "broken_board_rate": 2.78,
            "promotion_rate_1_to_2": 85.0,
            "promotion_rate_2_to_3": 90.0,
            "promotion_rate_high": 100.0,
            "max_height": 12,
            "max_height_stock": "双成药业 (002693) 12连板",
            "sentiment_phase": "高潮期",
            "sentiment_phase_en": "Climax",
            "sentiment_score": 98,
            "cash_defense_score": 92,
            "suggested_position": "持筹为主；未持仓不做无脑追高（节前最后交易日）",
            "core_themes": ["大金融/券商", "金融科技", "半导体", "鸿蒙软件"]
        },
        "absolute_high": {
            "title": "沪指+8.06%收3336.50，成交2.59万亿创纪录；双成药业12连板，东方财富20cm成交306亿",
            "leader_code": "002693",
            "leader_name": "双成药业",
            "concept": "发行股份购买奥拉股份 / 跨界半导体",
            "consecutive_boards": 12,
            "close_price": 16.36,
            "change_percent": 10.02,
            "turnover": 0.95,
            "turnover_rate": 1.42,
            "seal_status": "12连板一字（9月11日复牌起连续涨停）",
            "intraday_behavior": "16.36元一字，成交约0.95亿元，换手1.42%。不是14连板。",
            "sub_leader_code": "300059",
            "sub_leader_name": "东方财富",
            "sub_leader_concept": "券商 / 金融科技 20cm二连板",
            "sub_leader_boards": 2,
            "sub_leader_change": 19.98,
            "sub_leader_status": "收20.30元，成交305.98亿元，换手11.5%",
            "height_analysis": "沪深成交25930.37亿元（较前日+11470亿）。创业板指+15.36%收2175.09，科创50约+17.88%，北证50约+22.84%。公开报道超5300家上涨、仅约8家下跌、超700只涨停。券商除停牌外接近全线涨停。银之杰32.81元20cm一字（8天7板）。早盘连板：中南股份/亚泰集团/恒银科技6连板，天风证券/国海证券/五矿资本等5连板。",
            "strategy_holding": "持筹者：节前最后一天，核心券商/金融科技持有过节，不因恐高清仓。",
            "strategy_buying": "持币者：节前最后30分钟不追杂毛。东方财富已20cm二板+306亿，溢价给节后，不在尾盘加杠杆。"
        },
        "ladder_matrix": [
            {
                "tier": "12连板",
                "count": 1,
                "stocks": [
                    {"code": "002693", "name": "双成药业", "price": 16.36, "change": 10.02, "concept": "重组半导体", "turnover": 0.95, "turnover_rate": 1.42, "seal_amount": 20000, "seal_ratio": 210.53, "seal_time": "09:25", "breaks": 0, "status": "一字"}
                ]
            },
            {
                "tier": "20cm 8天7板 / 6连板一字",
                "count": 4,
                "stocks": [
                    {"code": "300085", "name": "银之杰", "price": 32.81, "change": 20.01, "concept": "金融科技", "turnover": 2.20, "turnover_rate": 3.00, "seal_amount": 15000, "seal_ratio": 68.18, "seal_time": "09:25", "breaks": 0, "status": "20cm一字"},
                    {"code": "603106", "name": "恒银科技", "price": 8.48, "change": 10.00, "concept": "金融机具", "turnover": 0.26, "turnover_rate": 1.50, "seal_amount": 8000, "seal_ratio": 307.69, "seal_time": "09:25", "breaks": 0, "status": "6连板一字"},
                    {"code": "600881", "name": "亚泰集团", "price": 1.89, "change": 10.00, "concept": "综合/地产链", "turnover": 0.30, "turnover_rate": 2.00, "seal_amount": 6000, "seal_ratio": 200.00, "seal_time": "09:25", "breaks": 0, "status": "6连板一字"},
                    {"code": "601162", "name": "天风证券", "price": 4.39, "change": 10.00, "concept": "券商", "turnover": 4.01, "turnover_rate": 4.50, "seal_amount": 12000, "seal_ratio": 29.93, "seal_time": "09:25", "breaks": 0, "status": "5连板一字"}
                ]
            },
            {
                "tier": "容量中军 20cm/10cm",
                "count": 5,
                "stocks": [
                    {"code": "300059", "name": "东方财富", "price": 20.30, "change": 19.98, "concept": "券商/互金20cm二板", "turnover": 305.98, "turnover_rate": 11.50, "seal_amount": 40000, "seal_ratio": 1.31, "seal_time": "回封", "breaks": 1, "status": "306亿成交20cm"},
                    {"code": "600030", "name": "中信证券", "price": 27.20, "change": 10.00, "concept": "券商航母", "turnover": 107.42, "turnover_rate": 4.80, "seal_amount": 50000, "seal_ratio": 4.65, "seal_time": "回封", "breaks": 1, "status": "百亿中军涨停"},
                    {"code": "300033", "name": "同花顺", "price": 193.31, "change": 20.00, "concept": "金融信息", "turnover": 42.91, "turnover_rate": 8.50, "seal_amount": 20000, "seal_ratio": 4.66, "seal_time": "回封", "breaks": 1, "status": "20cm"},
                    {"code": "300339", "name": "润和软件", "price": 37.37, "change": 20.00, "concept": "鸿蒙", "turnover": 31.11, "turnover_rate": 18.00, "seal_amount": 8000, "seal_ratio": 2.57, "seal_time": "回封", "breaks": 1, "status": "20cm"},
                    {"code": "688981", "name": "中芯国际", "price": 59.99, "change": 20.00, "concept": "芯片制造", "turnover": 65.55, "turnover_rate": 12.00, "seal_amount": 15000, "seal_ratio": 2.29, "seal_time": "回封", "breaks": 1, "status": "科创20cm"}
                ]
            }
        ],
        "broken_board_list": [],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "002693", "name": "双成药业", "boards": 12, "seal_amount": 20000, "seal_ratio": 210.53, "free_float_ratio": 10.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（连续一字）"},
            {"rank": 2, "code": "300085", "name": "银之杰", "boards": 7, "seal_amount": 15000, "seal_ratio": 68.18, "free_float_ratio": 5.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 3, "code": "603106", "name": "恒银科技", "boards": 6, "seal_amount": 8000, "seal_ratio": 307.69, "free_float_ratio": 4.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 4, "code": "300059", "name": "东方财富", "boards": 2, "seal_amount": 40000, "seal_ratio": 1.31, "free_float_ratio": 0.80, "first_seal": "回封", "breaks": 1, "stars": 4, "premium_exp": "高（牛市旗手，但封成比低）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "证券", "inflow": 47.41, "change": 10.00, "leaders": "东方财富、中信证券、天风证券", "limit_ups": 50},
                {"name": "保险", "inflow": 19.75, "change": 8.00, "leaders": "保险板块", "limit_ups": 8},
                {"name": "电池", "inflow": 14.67, "change": 15.40, "leaders": "宁德时代等", "limit_ups": 20},
                {"name": "软件开发", "inflow": 12.88, "change": 16.66, "leaders": "润和软件、同花顺", "limit_ups": 30}
            ],
            "sectors_outflow": [
                {"name": "房地产开发", "outflow": -32.61, "change": 5.00, "reason": "钛媒体：行业资金流出最多（相对高位兑现，指数仍大涨）"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "300059", "name": "东方财富", "turnover": 305.98, "change": 19.98, "role": "牛市旗手/306亿成交", "analysis": "20cm二连板，主力净流入约1.49亿；深股通买9.2亿卖10.7亿，北向净卖约1.5亿。"},
            {"rank": 2, "code": "600030", "name": "中信证券", "turnover": 107.42, "change": 10.00, "role": "券商航母", "analysis": "成交约107亿涨停，与东方财富构成大金融双旗手。"},
            {"rank": 3, "code": "300750", "name": "宁德时代", "turnover": 230.13, "change": 8.00, "role": "成长权重成交锚", "analysis": "放量跟涨，不是涨停，但是成长方向流动性核心。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "深股通专用（东方财富 9月30日）",
                "style": "北向高位对流",
                "actions": [
                    {"stock": "东方财富 (300059)", "net_buy": -15000, "type": "深股通买9.2亿、卖10.7亿，净卖约1.5亿元", "comment": "公开报道：机构席位当日隐身，北向成为龙虎榜主力"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "双成药业12连板一字，公开报道跌停约0。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "SAFE", "triggered": False, "detail": "超700涨停、仅约8只下跌，炸板不是主矛盾。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "早盘口径：上周五3板以上晋级率约100%。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "SAFE", "triggered": False, "detail": "普涨结构，不是核按钮日。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "成交2.59万亿创当时历史纪录。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "券商、金融科技、半导体共振。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "高潮期。风险在节后高开低走，不在当日退潮。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "下一交易日是10月8日（国庆后）。先看东方财富、中信证券能否继续涨停开盘。",
                "双成药业、银之杰、恒银科技看一字封单，开板则高度降温。"
            ],
            "trading_discipline": [
                "节后高开是兑现窗口，不是新开仓窗口。去弱留强。",
                "700+涨停不可复制，预期管理比追高重要。"
            ],
            "risk_warnings": [
                "2.59万亿天量后，节后量能与涨停数大概率回落。",
                "银之杰已提示非理性炒作并被交易所重点监控。"
            ]
        }
    },
    "2024-10-08": {
        "is_trading_day": True,
        "date": "2024-10-08",
        "date_cn": "2024年10月08日 星期二",
        "data_source": "财联社10月8日焦点复盘、每日经济新闻指数播报、证券时报揭秘涨停、中国证券报成交统计、新浪财经日K。东方财富900亿成交发生在10月9日，不是8日。",
        "market_summary": {
            "sh_index": 3489.78,
            "sh_change": 4.59,
            "sz_index": 11495.10,
            "sz_change": 9.17,
            "cy_index": 2550.28,
            "cy_change": 17.25,
            "total_turnover": 34519,
            "turnover_change": 8589,
            "up_count": 5100,
            "down_count": 250,
            "flat_count": 40,
            "median_change": 5.00,
            "limit_up_count": 715,
            "limit_down_count": 0,
            "broken_board_count": 628,
            "consecutive_board_count": 342,
            "broken_board_rate": 46.76,
            "promotion_rate_1_to_2": 59.04,
            "promotion_rate_2_to_3": 55.0,
            "promotion_rate_high": 80.0,
            "max_height": 13,
            "max_height_stock": "双成药业 (002693) 13连板",
            "sentiment_phase": "分歧期",
            "sentiment_phase_en": "Divergence",
            "sentiment_score": 70,
            "cash_defense_score": 58,
            "suggested_position": "5~7成 (去弱留强，不追开盘一字杂毛)",
            "core_themes": ["半导体/国产芯片", "大金融/券商", "金融科技", "鸿蒙软件"]
        },
        "absolute_high": {
            "title": "成交3.45万亿再创纪录；715涨停但628炸板，封板率53%；双成药业13连板",
            "leader_code": "002693",
            "leader_name": "双成药业",
            "concept": "跨界收购奥拉股份 / 半导体",
            "consecutive_boards": 13,
            "close_price": 18.00,
            "change_percent": 10.02,
            "turnover": 0.32,
            "turnover_rate": 0.43,
            "seal_status": "13连板一字，早盘封单约2.25亿元",
            "intraday_behavior": "18.00元一字，成交约0.32亿元，换手0.43%。不是15连板。",
            "sub_leader_code": "300059",
            "sub_leader_name": "东方财富",
            "sub_leader_concept": "券商 20cm三连板",
            "sub_leader_boards": 3,
            "sub_leader_change": 20.00,
            "sub_leader_status": "收24.36元，最低22.77元回封，成交约333亿元（不是900亿）",
            "height_analysis": "三大指数高开（沪指开盘3674点附近）回落，创业板指+17.25%收2550.28。财联社：715涨停、628炸板、封板率53%。连板：恒银科技、亚泰集团7连板（亚泰盘中天地天，收2.08元）；天风证券等6连板；银之杰20cm九天八板收39.37元一字；中信证券、东方财富等3连板。券商接近全线涨停。宁德时代成交约412亿、贵州茅台约335亿冲高回落、东方财富约333亿。",
            "strategy_holding": "持筹者：开盘涨停未能封住的跟风股减仓；保留双成药业、银之杰、恒银科技、东方财富、中信证券等前排。",
            "strategy_buying": "持币者：不追开盘942个一字。等分歧回封。东方财富已20cm三板+333亿，溢价给次日，不在尾盘加仓。"
        },
        "ladder_matrix": [
            {
                "tier": "13连板",
                "count": 1,
                "stocks": [
                    {"code": "002693", "name": "双成药业", "price": 18.00, "change": 10.02, "concept": "重组芯片", "turnover": 0.32, "turnover_rate": 0.43, "seal_amount": 22500, "seal_ratio": 703.13, "seal_time": "09:25", "breaks": 0, "status": "一字"}
                ]
            },
            {
                "tier": "20cm 9天8板 / 7连板",
                "count": 3,
                "stocks": [
                    {"code": "300085", "name": "银之杰", "price": 39.37, "change": 20.00, "concept": "金融科技", "turnover": 1.12, "turnover_rate": 1.20, "seal_amount": 18000, "seal_ratio": 160.71, "seal_time": "09:25", "breaks": 0, "status": "20cm一字"},
                    {"code": "603106", "name": "恒银科技", "price": 9.33, "change": 10.00, "concept": "金融机具", "turnover": 0.16, "turnover_rate": 0.80, "seal_amount": 10000, "seal_ratio": 625.00, "seal_time": "09:25", "breaks": 0, "status": "7连板一字"},
                    {"code": "600881", "name": "亚泰集团", "price": 2.08, "change": 10.05, "concept": "综合", "turnover": 9.47, "turnover_rate": 18.00, "seal_amount": 3000, "seal_ratio": 3.17, "seal_time": "回封", "breaks": 1, "status": "7连板天地天"}
                ]
            },
            {
                "tier": "6连板 / 3连板中军",
                "count": 6,
                "stocks": [
                    {"code": "601162", "name": "天风证券", "price": 4.83, "change": 10.02, "concept": "券商6连板", "turnover": 1.60, "turnover_rate": 1.80, "seal_amount": 242400, "seal_ratio": 1515.00, "seal_time": "09:25", "breaks": 0, "status": "一字（封单额24.24亿）"},
                    {"code": "300059", "name": "东方财富", "price": 24.36, "change": 20.00, "concept": "券商20cm三板", "turnover": 333.00, "turnover_rate": 10.20, "seal_amount": 335700, "seal_ratio": 10.08, "seal_time": "回封", "breaks": 1, "status": "333亿成交20cm"},
                    {"code": "600030", "name": "中信证券", "price": 29.92, "change": 10.00, "concept": "券商3连板", "turnover": 44.14, "turnover_rate": 1.80, "seal_amount": 549800, "seal_ratio": 1245.58, "seal_time": "09:25", "breaks": 0, "status": "一字（封单额54.98亿）"},
                    {"code": "300033", "name": "同花顺", "price": 231.97, "change": 20.00, "concept": "金融信息", "turnover": 57.30, "turnover_rate": 9.00, "seal_amount": 20000, "seal_ratio": 3.49, "seal_time": "回封", "breaks": 1, "status": "20cm"},
                    {"code": "688981", "name": "中芯国际", "price": 71.99, "change": 20.00, "concept": "芯片制造", "turnover": 70.31, "turnover_rate": 10.50, "seal_amount": 25000, "seal_ratio": 3.56, "seal_time": "回封", "breaks": 1, "status": "科创20cm"},
                    {"code": "300339", "name": "润和软件", "price": 44.84, "change": 20.00, "concept": "鸿蒙", "turnover": 2.84, "turnover_rate": 2.00, "seal_amount": 12000, "seal_ratio": 42.25, "seal_time": "09:25", "breaks": 0, "status": "20cm一字"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "600519", "name": "贵州茅台", "price": 1723.00, "change": -1.43, "max_change": 9.27, "concept": "权重消费", "turnover": 335.48, "reason": "开盘1910元附近冲高后回落，成交约335亿，权重获利兑现"},
            {"code": "600881", "name": "亚泰集团", "price": 2.08, "change": 10.05, "max_change": 10.05, "concept": "7连板", "turnover": 9.47, "reason": "盘中触及1.70元跌停价再回封，天地天，封成比极弱"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "600030", "name": "中信证券", "boards": 3, "seal_amount": 549800, "seal_ratio": 1245.58, "free_float_ratio": 4.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（封单54.98亿）"},
            {"rank": 2, "code": "300059", "name": "东方财富", "boards": 3, "seal_amount": 335700, "seal_ratio": 10.08, "free_float_ratio": 2.20, "first_seal": "回封", "breaks": 1, "stars": 5, "premium_exp": "高（封单33.57亿，成交333亿）"},
            {"rank": 3, "code": "601162", "name": "天风证券", "boards": 6, "seal_amount": 242400, "seal_ratio": 1515.00, "free_float_ratio": 8.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（封单24.24亿）"},
            {"rank": 4, "code": "002693", "name": "双成药业", "boards": 13, "seal_amount": 22500, "seal_ratio": 703.13, "free_float_ratio": 12.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 5, "code": "300085", "name": "银之杰", "boards": 8, "seal_amount": 18000, "seal_ratio": 160.71, "free_float_ratio": 6.00, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高"},
            {"rank": 6, "code": "600881", "name": "亚泰集团", "boards": 7, "seal_amount": 3000, "seal_ratio": 3.17, "free_float_ratio": 0.50, "first_seal": "回封", "breaks": 1, "stars": 2, "premium_exp": "低（天地天）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "半导体", "inflow": 80.0, "change": 18.16, "leaders": "中芯国际、双成药业、海光信息", "limit_ups": 200},
                {"name": "软件开发", "inflow": 60.0, "change": 17.18, "leaders": "润和软件、同花顺", "limit_ups": 80},
                {"name": "非银金融", "inflow": 50.0, "change": 10.00, "leaders": "中信证券、东方财富、天风证券", "limit_ups": 48}
            ],
            "sectors_outflow": [
                {"name": "旅游酒店", "outflow": -8.0, "change": -0.19, "reason": "少数板块收跌"},
                {"name": "东方财富主力资金", "outflow": -24.54, "change": 20.00, "reason": "中国证券报：东方财富主力资金净流出居前（涨停仍有内部分化）"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "300750", "name": "宁德时代", "turnover": 411.56, "change": 18.70, "role": "两市成交额前列", "analysis": "收299.00元，成交约412亿元（公开报道超390亿），成长权重天量但未封20cm。"},
            {"rank": 2, "code": "600519", "name": "贵州茅台", "turnover": 335.48, "change": -1.43, "role": "权重冲高回落", "analysis": "成交约335亿，开盘冲击涨停后回落。"},
            {"rank": 3, "code": "300059", "name": "东方财富", "turnover": 333.00, "change": 20.00, "role": "券商20cm三板", "analysis": "成交约333亿封20cm。900.4亿纪录是10月9日，不是本日。深股通买16.3亿卖8.7亿，北向净买约7.6亿。"},
            {"rank": 4, "code": "688981", "name": "中芯国际", "turnover": 70.31, "change": 20.00, "role": "半导体中军", "analysis": "科创20cm，成交约70亿，不是220亿。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "深股通专用（东方财富 10月8日）",
                "style": "北向净买入容量旗手",
                "actions": [
                    {"stock": "东方财富 (300059)", "net_buy": 76000, "type": "深股通买16.3亿、卖8.7亿，北向净买约7.6亿元", "comment": "公开报道：北向首次对该股显示净买入状态"}
                ]
            },
            {
                "seat_name": "涨停封单公开统计（数据宝）",
                "style": "券商封单金额",
                "actions": [
                    {"stock": "中信证券 (600030)", "net_buy": 549800, "type": "涨停封单54.98亿元", "comment": "封单金额全市场第一"},
                    {"stock": "东方财富 (300059)", "net_buy": 335700, "type": "涨停封单33.57亿元", "comment": "封单金额第二"},
                    {"stock": "天风证券 (601162)", "net_buy": 242400, "type": "涨停封单24.24亿元", "comment": "封单金额第三"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "SAFE", "triggered": False, "detail": "双成药业13板一字，银之杰/恒银科技一字，高位核心未死。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "DANGER", "triggered": True, "detail": "财联社：628只炸板，封板率53%，炸板率46.76%。天量分歧。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "公开口径连板股晋级率约59%（不含ST），仍高于冰点。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "WARN", "triggered": True, "detail": "亚泰集团天地天；大批开盘涨停股回落超10%。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "SAFE", "triggered": False, "detail": "成交34519亿元再创纪录，指数高开回落但仍收阳。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "SAFE", "triggered": False, "detail": "券商、半导体、金融科技仍是主线，但是内部分化。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "高潮后的天量分歧，不是第二阶段杀跌。次日（10月9日）才出现东方财富冲高回落900亿。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "东方财富、中信证券竞价若平开或低开，大金融从主升切分歧，只减不强追。",
                "双成药业、银之杰、恒银科技继续看一字；亚泰集团天地天次日不接力。"
            ],
            "trading_discipline": [
                "628炸板说明开盘一字不可复制。去弱留强，集中前排。",
                "不要把10月9日的900亿成交误当成8日数据做决策。"
            ],
            "risk_warnings": [
                "3.45万亿后量能必然回落，跟风股流动性会迅速枯竭。",
                "沪指从3674点开盘回落到3489点，长上影是节后第一记耳光。"
            ]
        }
    },
    "2026-08-13": {
        "is_trading_day": True,
        "date": "2026-08-13",
        "date_cn": "2026年08月13日 星期四",
        "data_source": "证券时报·数据宝8月13日涨停封单一览、财联社焦点复盘、上海证券报蓝盾光电公告、新浪财经日K。指数/涨停口径截至收盘。",
        "market_summary": {
            "sh_index": 3926.96,
            "sh_change": -0.50,
            "sz_index": 14289.44,
            "sz_change": -0.87,
            "cy_index": 3586.04,
            "cy_change": -0.45,
            "total_turnover": 25500,
            "turnover_change": 3985,
            "up_count": 1143,
            "down_count": 4317,
            "flat_count": 80,
            "median_change": -1.80,
            "limit_up_count": 62,
            "limit_down_count": 4,
            "broken_board_count": 40,
            "consecutive_board_count": 22,
            "broken_board_rate": 39.22,
            "promotion_rate_1_to_2": 40.0,
            "promotion_rate_2_to_3": 56.25,
            "promotion_rate_high": 56.25,
            "max_height": 5,
            "max_height_stock": "秦安股份 (603758) 5连板；蓝盾光电20cm四连板",
            "sentiment_phase": "分歧期",
            "sentiment_phase_en": "Divergence",
            "sentiment_score": 40,
            "cash_defense_score": 32,
            "suggested_position": "2~4成 (放量收跌，高位去弱)",
            "core_themes": ["创新药/CRO/医疗服务", "汽车零部件", "电力公用", "算电协同"]
        },
        "absolute_high": {
            "title": "放量25500亿指数收跌；秦安股份一字5连板成新高度，蓝盾光电20cm四连板",
            "leader_code": "603758",
            "leader_name": "秦安股份",
            "concept": "汽车零部件 / 市场交易异常波动",
            "consecutive_boards": 5,
            "close_price": 15.35,
            "change_percent": 10.04,
            "turnover": 0.77,
            "turnover_rate": 3.50,
            "seal_status": "一字5连板",
            "intraday_behavior": "15.35元全天一字。当晚公司发风险提示：主营不涉及人形机器人及零配件制造。次日（8月14日）开盘跳水跌停。",
            "sub_leader_code": "300862",
            "sub_leader_name": "蓝盾光电",
            "sub_leader_concept": "重组岚创科技 / 光通信镀膜设备",
            "sub_leader_boards": 4,
            "sub_leader_change": 20.01,
            "sub_leader_status": "20cm四连板收39.41元，成交4.10亿元，封单10.38亿元，封单占流通约17.39%",
            "height_analysis": "数据宝：62只涨停、40只封板未遂，封板率60.78%；4只跌停。财联社：秦安股份5连板；蓝盾光电20cm、北京文化、京投发展、同力天启、一鸣食品、皇氏集团4连板。连板高度从此前百花医药7板回落到5板。两市成交约2.55万亿，较前日放量约3985亿，但三大指数收绿，1143涨/4317跌。",
            "strategy_holding": "持筹者：秦安股份一字溢价已透支，当晚公告证伪机器人逻辑，次日按核按钮纪律，不接力5板。蓝盾光电封单10.38亿质量好于秦安，可观察到竞价。",
            "strategy_buying": "持币者：放量收跌日不追高位5板。仓位2~4成，只做医药/电力低位首板或2板弱转强，不打高位断头股（传智教育、高争民爆、甘咨询、麦迪科技）。"
        },
        "ladder_matrix": [
            {
                "tier": "5连板",
                "count": 1,
                "stocks": [
                    {"code": "603758", "name": "秦安股份", "price": 15.35, "change": 10.04, "concept": "汽车零部件", "turnover": 0.77, "turnover_rate": 3.50, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字5板"}
                ]
            },
            {
                "tier": "20cm / 10cm 4连板",
                "count": 6,
                "stocks": [
                    {"code": "300862", "name": "蓝盾光电", "price": 39.41, "change": 20.01, "concept": "重组岚创科技/光通信", "turnover": 4.10, "turnover_rate": 8.00, "seal_amount": 103800, "seal_ratio": 253.17, "seal_time": "09:25", "breaks": 0, "status": "20cm一字，封单10.38亿"},
                    {"code": "000802", "name": "北京文化", "price": 6.26, "change": 10.02, "concept": "影视/谷子经济", "turnover": 8.51, "turnover_rate": 12.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 1, "status": "4连板换手"},
                    {"code": "600683", "name": "京投发展", "price": 12.93, "change": 10.04, "concept": "重组/TOD", "turnover": 0.24, "turnover_rate": 1.20, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字4板"},
                    {"code": "605286", "name": "同力天启", "price": 34.09, "change": 10.00, "concept": "算电协同/储能", "turnover": 0.78, "turnover_rate": 2.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字4板"},
                    {"code": "605179", "name": "一鸣食品", "price": 33.43, "change": 10.00, "concept": "乳业/13天9板口径", "turnover": 8.69, "turnover_rate": 18.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 1, "status": "4连板换手"},
                    {"code": "002329", "name": "皇氏集团", "price": 4.62, "change": 10.00, "concept": "乳业/食品", "turnover": 7.31, "turnover_rate": 16.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 1, "status": "4连板"}
                ]
            },
            {
                "tier": "3连板",
                "count": 2,
                "stocks": [
                    {"code": "600881", "name": "亚泰集团", "price": 2.27, "change": 10.19, "concept": "创新药", "turnover": 6.52, "turnover_rate": 12.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 1, "status": "3连板"},
                    {"code": "603887", "name": "城地香江", "price": 12.49, "change": 10.04, "concept": "算力租赁", "turnover": 2.28, "turnover_rate": 8.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字3板"}
                ]
            },
            {
                "tier": "2连板（公开点名）",
                "count": 6,
                "stocks": [
                    {"code": "001260", "name": "坤泰股份", "price": 21.03, "change": 9.99, "concept": "汽车零部件", "turnover": 0.40, "turnover_rate": 1.50, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字，封单占流通24.12%"},
                    {"code": "000887", "name": "中鼎股份", "price": 23.69, "change": 9.98, "concept": "汽车零部件/密封件", "turnover": 18.24, "turnover_rate": 8.50, "seal_amount": 35900, "seal_ratio": 19.68, "seal_time": "回封", "breaks": 1, "status": "封单3.59亿"},
                    {"code": "002081", "name": "金螳螂", "price": 4.81, "change": 10.07, "concept": "装饰/洁净室", "turnover": 1.31, "turnover_rate": 4.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字2板"},
                    {"code": "002172", "name": "澳洋健康", "price": 4.13, "change": 10.13, "concept": "康复医疗", "turnover": 0.96, "turnover_rate": 3.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "一字2板"},
                    {"code": "000936", "name": "华西股份", "price": 6.34, "change": 10.07, "concept": "光通信", "turnover": 1.64, "turnover_rate": 5.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "秒板", "breaks": 0, "status": "2连板"},
                    {"code": "603330", "name": "天洋新材", "price": 9.71, "change": 9.97, "concept": "电子胶/散热", "turnover": 6.56, "turnover_rate": 14.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 1, "status": "换手2板"}
                ]
            },
            {
                "tier": "首板精选（电力/医药/封单）",
                "count": 4,
                "stocks": [
                    {"code": "601991", "name": "大唐发电", "price": 6.92, "change": 10.02, "concept": "电力", "turnover": 62.13, "turnover_rate": 6.50, "seal_amount": 37700, "seal_ratio": 6.07, "seal_time": "尾盘", "breaks": 1, "status": "容量涨停，封单3.77亿"},
                    {"code": "300333", "name": "兆日科技", "price": 10.64, "change": 20.00, "concept": "信息安全", "turnover": 0.34, "turnover_rate": 2.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "09:25", "breaks": 0, "status": "20cm一字，封单占流通5.10%"},
                    {"code": "300404", "name": "博济医药", "price": 14.45, "change": 20.02, "concept": "CRO", "turnover": 8.84, "turnover_rate": 20.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 1, "status": "20cm医疗服务"},
                    {"code": "600613", "name": "神奇制药", "price": 5.83, "change": 10.00, "concept": "中药", "turnover": 1.36, "turnover_rate": 5.00, "seal_amount": 0, "seal_ratio": 0.0, "seal_time": "回封", "breaks": 0, "status": "医药首板"}
                ]
            }
        ],
        "broken_board_list": [
            {"code": "003032", "name": "传智教育", "price": 11.62, "change": -9.99, "max_change": -3.18, "concept": "高位人气/教育", "turnover": 10.87, "reason": "13天9板后跌停，高位断头"},
            {"code": "002827", "name": "高争民爆", "price": 55.10, "change": -10.00, "max_change": 0.28, "concept": "高位民爆", "turnover": 11.96, "reason": "从前收61.22元封跌停55.10元"},
            {"code": "000779", "name": "甘咨询", "price": 10.73, "change": -9.98, "max_change": -3.27, "concept": "高位补跌", "turnover": 12.46, "reason": "从前收11.92元封跌停"},
            {"code": "603990", "name": "麦迪科技", "price": 22.26, "change": -9.99, "max_change": 1.09, "concept": "高位补跌", "turnover": 13.96, "reason": "从前收24.73元封跌停，成交约14亿"}
        ],
        "sealing_strength_ranking": [
            {"rank": 1, "code": "300862", "name": "蓝盾光电", "boards": 4, "seal_amount": 103800, "seal_ratio": 253.17, "free_float_ratio": 17.39, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（20cm一字，封单10.38亿）"},
            {"rank": 2, "code": "001260", "name": "坤泰股份", "boards": 2, "seal_amount": 0, "seal_ratio": 0.0, "free_float_ratio": 24.12, "first_seal": "09:25", "breaks": 0, "stars": 5, "premium_exp": "极高（封单占流通24.12%，数据宝力度第1）"},
            {"rank": 3, "code": "601991", "name": "大唐发电", "boards": 1, "seal_amount": 37700, "seal_ratio": 6.07, "free_float_ratio": 1.20, "first_seal": "尾盘", "breaks": 1, "stars": 4, "premium_exp": "中高（封单3.77亿，成交62亿）"},
            {"rank": 4, "code": "000887", "name": "中鼎股份", "boards": 2, "seal_amount": 35900, "seal_ratio": 19.68, "free_float_ratio": 2.00, "first_seal": "回封", "breaks": 1, "stars": 4, "premium_exp": "中高（封单3.59亿）"},
            {"rank": 5, "code": "300333", "name": "兆日科技", "boards": 1, "seal_amount": 0, "seal_ratio": 0.0, "free_float_ratio": 5.10, "first_seal": "09:25", "breaks": 0, "stars": 4, "premium_exp": "高（20cm一字，封单占流通5.10%）"},
            {"rank": 6, "code": "603758", "name": "秦安股份", "boards": 5, "seal_amount": 0, "seal_ratio": 0.0, "free_float_ratio": 0.80, "first_seal": "09:25", "breaks": 0, "stars": 3, "premium_exp": "中（高度最高但当晚公告证伪机器人）"}
        ],
        "main_capital_flow": {
            "sectors_inflow": [
                {"name": "医药生物/医疗服务/CRO", "inflow": 116.0, "change": 3.50, "leaders": "博济医药、新里程、万邦医药、南模生物、澳洋健康", "limit_ups": 14},
                {"name": "电力公用", "inflow": 20.0, "change": 2.00, "leaders": "大唐发电、华电能源、金开新能、惠天热电", "limit_ups": 5},
                {"name": "汽车零部件", "inflow": 15.0, "change": 2.50, "leaders": "秦安股份、坤泰股份、中鼎股份、联诚精密", "limit_ups": 4}
            ],
            "sectors_outflow": [
                {"name": "电子", "outflow": -245.0, "change": -2.50, "reason": "公开复盘转述：电子板块资金流出居前"},
                {"name": "有色", "outflow": -90.0, "change": -3.00, "reason": "贵金属/工业金属回调"},
                {"name": "北向资金", "outflow": -32.61, "change": 0.00, "reason": "北向净卖出32.61亿元"}
            ]
        },
        "popularity_anchors": [
            {"rank": 1, "code": "601991", "name": "大唐发电", "turnover": 62.13, "change": 10.02, "role": "电力容量涨停", "analysis": "成交约62亿元并封涨停，是放量日少数能封住的权重方向。"},
            {"rank": 2, "code": "000887", "name": "中鼎股份", "turnover": 18.24, "change": 9.98, "role": "汽车零部件容量2板", "analysis": "成交18.24亿、封单3.59亿。"},
            {"rank": 3, "code": "300862", "name": "蓝盾光电", "turnover": 4.10, "change": 20.01, "role": "20cm四连板质量锚", "analysis": "成交4.10亿但封单10.38亿，封成比远好于同高度换手板。"},
            {"rank": 4, "code": "000802", "name": "北京文化", "turnover": 8.51, "change": 10.02, "role": "影视4板人气", "analysis": "成交8.51亿换手板，质量弱于蓝盾一字。"}
        ],
        "dragon_tiger_list": [
            {
                "seat_name": "公开复盘转述（待交易所席位核对）",
                "style": "医药与汽车零部件",
                "actions": [
                    {"stock": "中鼎股份 (000887)", "net_buy": 11200, "type": "市场复盘转述：南京太平南路买入约1.12亿元", "comment": "以交易所次日公布的龙虎榜营业部为准"},
                    {"stock": "蓝盾光电 (300862)", "net_buy": 0, "type": "当晚发严重异常波动公告", "comment": "连续4日收盘涨幅偏离值累计超过100%，重组存在暂停或取消风险"}
                ]
            }
        ],
        "cash_defense_checklist": [
            {"id": "c1", "rule": "高位总龙头断板并出现直接跌停或恶性负反馈", "status": "WARN", "triggered": True, "detail": "高度从7板回落到5板；传智教育、高争民爆、甘咨询、麦迪科技4只高位股跌停。秦安5板本身未断，但当晚公告证伪。"},
            {"id": "c2", "rule": "全市场炸板率超过 30% 警报线", "status": "DANGER", "triggered": True, "detail": "40只封板未遂，炸板率39.22%，封板率60.78%。"},
            {"id": "c3", "rule": "连板晋级率跌破 35% 冰点阈值", "status": "SAFE", "triggered": False, "detail": "公开口径连板晋级率约56.25%，中位接力还在。"},
            {"id": "c4", "rule": "日内天地板或大幅回撤超10%股票数量 >= 3只", "status": "DANGER", "triggered": True, "detail": "4只跌停全是前期高位人气股。"},
            {"id": "c5", "rule": "大盘指数破位且两市成交量出现严重断崖式萎缩", "status": "WARN", "triggered": True, "detail": "成交放到2.55万亿但指数收跌，是放量滞涨不是缩量破位。"},
            {"id": "c6", "rule": "题材一日游轮动加剧，前日连板次日大幅低开计提", "status": "WARN", "triggered": True, "detail": "高位教育/民爆核按钮，资金切向医药与电力。"},
            {"id": "c7", "rule": "处于情绪退潮期第二阶段（主跌杀中位与补跌）", "status": "SAFE", "triggered": False, "detail": "4板梯队仍在、医药低位涨停潮，属高位崩塌+低位接棒的分歧日，尚未全面杀中位。"}
        ],
        "next_day_discipline": {
            "bidding_rules": [
                "先看秦安股份竞价：若低开翻绿或封跌停，5板高度结束，中高位一律不打。",
                "蓝盾光电封单10.38亿，竞价高开3%~7%可观察回封，>10%不追。",
                "传智教育、高争民爆、甘咨询、麦迪科技跌停板不抄。"
            ],
            "trading_discipline": [
                "仓位2~4成。放量收跌日只做辨识度前排（蓝盾光电、医药2板、电力容量）。",
                "不接力秦安股份5板。"
            ],
            "risk_warnings": [
                "秦安股份已提示不涉及人形机器人，5板次日核按钮概率高（8月14日已验证跌停）。",
                "蓝盾光电触及严重异常波动，重组可能暂停、中止或取消。",
                "2.55万亿放量若次日缩量，指数在3900点附近二次回落。"
            ]
        }
    },
}
