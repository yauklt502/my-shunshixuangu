import { compactDate } from "@/lib/format";
import { kpl, liveHost, type CommonParams, type Host } from "./client";

type Common = CommonParams;

function call<T>(host: Host, method: "GET" | "POST", params: Record<string, string | number | undefined>, common: Common) {
  return kpl<T>({ host, method, params, common });
}

export const api = {
  changeStatistics: (date: string, common: Common) =>
    call<{ info: Array<{ strong: string; ztjs: string; lbgd: string; Day: string; df_num: string }>; tip: string }>(
      "his",
      "GET",
      { a: "ChangeStatistics", c: "HisHomeDingPan", Date: date, Index: 0, st: 12 },
      common,
    ),

  marketCapacity: (date: string, common: Common) =>
    call<{
      info: {
        last: string;
        s_zrcs: string;
        s_zrtj: string;
        s3_zrtj: string;
        yclnstr: string;
        color: number;
        csbl?: number;
        ycln?: string;
        date: string;
        trends?: Array<Array<string>>;
      };
    }>("his", "GET", { a: "MarketCapacity", c: "HisHomeDingPan", Date: date, Type: 0 }, common),

  getZsReal: (date: string, common: Common) =>
    call<Record<string, unknown>>("his", "POST", { a: "GetZsReal", c: "StockL2History", Day: date }, common),

  refreshStockList: (common: Common) =>
    call<{
      StockList: Array<{
        StockID: string;
        prod_name: string;
        last_px: string | number;
        increase_rate: string;
        increase_amount: string | number;
        turnover: string | number;
      }>;
    }>(
      "hq",
      "POST",
      { a: "RefreshStockList", c: "UserSelectStock", StockIDList: "SH000001,SZ399001,SZ399006,SH000688" },
      common,
    ),

  marketStockZDNum: (date: string, common: Common) =>
    call<{ info: { SJZT: string; SJDT: string } }>(
      "his",
      "POST",
      { a: "MarketStockZDNum", c: "HisHomeDingPan", Date: date },
      common,
    ),

  dailyLimitIndex: (date: string, today: string, common: Common) =>
    date === today
      ? call<{ info: number[] }>("hq", "GET", { a: "DailyLimitIndex", c: "HomeDingPan" }, common)
      : call<{ info: number[] }>("his", "GET", { a: "DailyLimitIndex", c: "HisHomeDingPan", Day: date }, common),

  zhangTingExpression: (date: string, common: Common) =>
    call<{ info: Array<number | string> }>(
      "his",
      "GET",
      { a: "ZhangTingExpression", c: "HisHomeDingPan", Day: date },
      common,
    ),

  getZhangTingTianTi: (date: string, today: string, common: Common) =>
    call<{ StockList: unknown[][]; ZhuShuList: unknown[][]; Date?: string; date?: string }>(
      liveHost(date, today),
      "POST",
      { a: "GetZhangTingTianTi", c: "FuPanLa", Date: date },
      common,
    ),

  dailyLimitPerformance: (date: string, today: string, pidType: number, common: Common) =>
    date === today
      ? call<{ info: unknown }>("hq", "GET", {
          a: "DailyLimitPerformance",
          c: "HomeDingPan",
          PidType: pidType,
          Type: 4,
          Index: 0,
          Order: 0,
          st: 1000,
        }, common)
      : call<{ info: unknown }>("his", "GET", {
          a: "DailyLimitPerformance",
          c: "HisHomeDingPan",
          Day: date,
          PidType: pidType,
          Type: 4,
          Index: 0,
          Order: 0,
          st: 1000,
        }, common),

  dailyLimitPerformance2: (date: string, today: string, pidType: number, common: Common) =>
    date === today
      ? call<{ info: unknown }>("hq", "GET", {
          a: "DailyLimitPerformance2",
          c: "HomeDingPan",
          PidType: pidType,
          Type: 5,
          Index: 0,
          Order: 1,
          st: 1000,
        }, common)
      : call<{ info: unknown }>("his", "GET", {
          a: "DailyLimitPerformance2",
          c: "HisHomeDingPan",
          Day: date,
          PidType: pidType,
          Type: 5,
          Index: 0,
          Order: 1,
          st: 1000,
        }, common),

  getPlateInfo: (date: string, common: Common) =>
    call<{
      nums: { SZJS: number; XDJS: number; ZT: number; DT: number; ZBL: number; yestRase: number };
      list: Array<{ ZSCode: string; ZSName: string; num: number; StockList: unknown[][] }>;
      date?: string;
    }>("his", "POST", { a: "GetPlateInfo_w38", c: "HisLimitResumption", Date: date, Index: 0, st: 40 }, common),

  getPMSL: (date: string, today: string, common: Common) =>
    call<{
      List: Array<{
        StockList: Array<[string, string]>;
        TimeMin: number;
        TagID: number;
        ZSCode: string;
        ZSName: string;
        TagName: string;
        Detail: string;
      }>;
      date?: string;
    }>(liveHost(date, today), "GET", { a: "GetPMSL_PMLD", c: "FuPanLa", Date: date, Index: 0, st: 50 }, common),

  sharpWithdrawal: (date: string, common: Common) =>
    call<{ info: unknown[][]; num?: number }>(
      "his",
      "GET",
      { a: "SharpWithdrawal", c: "HisHomeDingPan", Day: date },
      common,
    ),

  getDatePlate: (zsCode: string, common: Common) =>
    call<{ list: Array<{ ZSName: string; Date: string; num: number; StockList: unknown[][] }>; ZSCode: string; ZSName: string }>(
      "his",
      "POST",
      { a: "GetDatePlate", c: "HisLimitResumption", ZSCode: zsCode, Index: 0, st: 8 },
      common,
    ),

  realRankingInfo: (date: string, today: string, type: number, zsType: number, common: Common, st = 30) =>
    call<{ list: unknown[][]; Count: number; Day?: string[] }>(
      liveHost(date, today),
      "POST",
      {
        a: "RealRankingInfo",
        c: "ZhiShuRanking",
        Date: date,
        Type: type,
        Order: 1,
        ZSType: zsType,
        Index: 0,
        st,
      },
      common,
    ),

  weightPerformance: (date: string, common: Common) =>
    call<{ info: { SZ: unknown[][]; XD: unknown[][] } }>(
      "his",
      "GET",
      { a: "WeightPerformance", c: "HisHomeDingPan", Day: date },
      common,
    ),

  getBKJJ: (date: string, today: string, common: Common) =>
    call<{ List1: unknown[][]; List2: unknown[][]; List3: unknown[][]; Day?: string }>(
      liveHost(date, today),
      "POST",
      { a: "GetBKJJ_W36", c: "StockBidYiDong", Day: compactDate(date), Order: 1, Type: 0 },
      common,
    ),

  getBKJJBL: (date: string, today: string, stockId: string, common: Common) =>
    call<{ List: unknown[][]; Day?: string }>(
      liveHost(date, today),
      "POST",
      {
        a: "GetBKJJBL",
        c: "StockBidYiDong",
        Day: compactDate(date),
        StockID: stockId,
        Index: 0,
        Order: 1,
        Type: 1,
        IsLB: 0,
        IsZT: 0,
        Isst: 1,
        filter: 3,
        st: 40,
      },
      common,
    ),

  getYTFP: (date: string, today: string, common: Common) =>
    call<{
      List: Array<{
        BName: string;
        BID: number;
        Buy: Array<{ Sto: string; StoN: string; Money: number; Three: number }>;
        Sell: Array<{ Sto: string; StoN: string; Money: number; Three: number }>;
      }>;
      Date?: string;
    }>(liveHost(date, today), "GET", { a: "GetYTFP_LHBDX", c: "FuPanLa", Date: date }, common),

  lhbList: (date: string, common: Common) =>
    call<{
      list: Array<{
        ID: string;
        Name: string;
        IncreaseAmount: string;
        D3: string;
        BuyIn: string;
        JoinNum: number;
        Turnover: string;
        CircPrice: number;
        Amplitude: string;
        TurnoverRatio: string;
        Capitalization: number;
      }>;
      T?: string[];
      BIcon?: Record<string, string[]>;
      SIcon?: Record<string, string[]>;
      lb?: Record<string, number>;
      Total?: number;
    }>("lhb", "POST", { a: "GetStockList", c: "LongHuBang", Time: date, Index: 0, st: 300 }, common),

  lhbDetail: (date: string, stockId: string, common: Common) =>
    call<{
      Name: string;
      ID: string;
      Time: string;
      CurPrice: string;
      QuoteChange: string;
      TurnoverRatio: string;
      Circulation: string;
      BuyIn: number;
      Turnover: string;
      List: Array<{
        SellList: Seat[];
        BuyList: Seat[];
        UpReason: string[];
        BuyTotal: number;
        SellTotal: number;
      }>;
      OnTimeList?: string[];
      lbnum?: number;
    }>("lhb", "POST", { a: "GetNewOneStockInfo", c: "Stock", Type: 0, Time: date, StockID: stockId }, common),

  youZiDongXiang: (date: string, common: Common) =>
    call<{
      DongXiang: Array<{
        ID: string;
        ShortName: string;
        List: Array<{
          ID: number;
          Name: string;
          Money: number;
          D3: number;
          IncreaseAmount: string;
        }>;
      }>;
    }>("lhb", "POST", { a: "YouZiDongXiangByList", c: "Index", Time: date }, common),

  groupInfo: (gid: string, common: Common) =>
    call<{ GID: number; Info: string; ShortName: string; Total: number; BusinessList: Array<{ ID: string; Name: string }> }>(
      "lhb",
      "POST",
      { a: "GroupInfo", c: "BusinessGroup", GID: gid },
      common,
    ),

  morningBidding: (date: string, common: Common) =>
    call<{
      info: {
        tJJJE: string;
        lJJJE: string;
        ycln: string;
        lln: string;
        tSZ: string;
        tXD: string;
        lSZ: string;
        lXD: string;
      };
    }>("his", "GET", { a: "MorningBidding", c: "HisHomeDingPan", Date: date }, common),

  morningBiddingNum: (date: string, common: Common) =>
    call<{ info: number[] }>("his", "GET", { a: "MorningBiddingNum", c: "HisHomeDingPan", Date: date }, common),

  morningBiddingList: (date: string, today: string, pidType: number, type: number, common: Common) => {
    const live = date === today;
    return call<{ info: unknown[][] }>(
      live ? "hq" : "his",
      "GET",
      {
        a: "MorningBiddingList",
        c: live ? "HomeDingPan" : "HisHomeDingPan",
        Date: date,
        PidType: pidType,
        Type: type,
        Index: 0,
        Order: 1,
        st: 300,
      },
      common,
    );
  },

  getWPQC: (date: string, today: string, common: Common) =>
    call<{ List: unknown[][] }>(
      liveHost(date, today),
      "GET",
      { a: "GetWPQC", c: "StockBidYiDong", Day: compactDate(date), Type: 1, Index: 0, Order: 1, st: 40 },
      common,
    ),

  getStockIDPlate: (stockId: string, common: Common) =>
    call<{ List: unknown[][] }>(
      "shhq",
      "POST",
      { a: "GetStockIDPlate", c: "StockL2Data", StockID: stockId, Type: 1 },
      common,
    ),

  getFeaturedSection: (stockId: string, common: Common) =>
    call<{ info: unknown[][] }>("shhq", "GET", { a: "GetFeaturedSection", c: "StockL2Data", StockID: stockId }, common),

  groupStockHigh: (date: string, today: string, common: Common) =>
    call<{
      GroupList: Array<{ List: unknown[][]; GroupName: string; GroupID: number }>;
      GroupCount: number;
      Date?: string;
    }>(
      liveHost(date, today),
      "POST",
      { a: "GroupStock_W28", c: "StockNewHigh", Date: date, Type: "0_0_0_0_0", IsAll: 0, Index: 0, st: 40 },
      common,
    ),

  interviewsByZS: (start: string, end: string, today: string, common: Common) =>
    call<{ List: unknown[][]; Count: number }>(
      liveHost(end, today),
      "POST",
      {
        a: "GetInterviewsByDateZS",
        c: "StockLineData",
        DStart: start,
        DEnd: end,
        Type: 9,
        Order: 1,
        Index: 0,
        st: 30,
      },
      common,
    ),

  interviewsByStock: (start: string, end: string, today: string, common: Common) =>
    call<{ List: unknown[][]; Count: number }>(
      liveHost(end, today),
      "POST",
      {
        a: "GetInterviewsByDateStock",
        c: "StockLineData",
        DStart: start,
        DEnd: end,
        Type: 2,
        FilterBJS: 1,
        Order: 1,
        Index: 0,
        st: 40,
      },
      common,
    ),

  replayList: (common: Common) =>
    call<{ List: string[] }>("shhq", "POST", { a: "GetRQZ_Data", c: "Index" }, common),

  fengKBest: (date: string, today: string, common: Common) =>
    call<{ List: unknown[][]; Count?: number; Tips?: string; Tip?: string }>(
      liveHost(date, today),
      "POST",
      { a: "GetFengKListBest", c: "StockFengKData", Day: compactDate(date), Time: 1500 },
      common,
    ),

  fengKList: (date: string, today: string, common: Common) =>
    call<{ List: unknown[][]; Count?: number }>(
      liveHost(date, today),
      "POST",
      { a: "GetFengKList", c: "StockFengKData", Index: 0, st: 80, Order: 17, Day: compactDate(date), Time: 1500 },
      common,
    ),

  fengKPlate: (date: string, common: Common) =>
    call<{ List: Array<[string, number]> }>(
      "his",
      "POST",
      { a: "GetFengKYDPlate", c: "StockFengKData", Day: compactDate(date) },
      common,
    ),

  newGetList: (common: Common) =>
    call<{
      Theme?: { List: ThemeItem[]; Num?: number };
      Topic?: {
        Day?: string;
        LData?: { Day?: string; List?: Array<{ ID: string; Title: string; Time: string; HotVal?: number; HotTag?: number }> };
      };
    }>("lhb", "POST", { a: "NewGetList", c: "Index" }, common),

  themeSearch: (key: string, common: Common) =>
    call<{
      List: Array<{ ID: string; Name: string; Desc: string; CreateTime: string }>;
      SList: Array<{ ID: string; Name: string; LName: string[]; LID: string[] }>;
    }>("lhb", "POST", { a: "InfoSearch", c: "Theme", key }, common),

  themeInfo: (id: string, common: Common) =>
    call<{
      ID: string;
      Name: string;
      BriefIntro: string;
      Introduction?: string;
      StockList?: Array<{ StockID: string; prod_name: string; HotNum?: number; Tag?: Array<{ Name: string; Reason: string }> }>;
      Table?: Array<{
        Level1: { ID: string; Name: string; Stocks: Array<{ StockID: string; prod_name: string; Hot?: number; Reason?: string; IsZz?: string; IsHot?: string }> };
        Level2?: Array<{ ID: string; Name: string; Stocks: Array<{ StockID: string; prod_name: string; Hot?: number }> }>;
      }>;
    }>("lhb", "POST", { a: "InfoGet", c: "Theme", ID: id }, common),

  zhiBo: (date: string, today: string, common: Common) =>
    date === today
      ? call<{ List: LiveItem[]; Notice?: string; date?: string }>("hq", "POST", { a: "ZhiBoContent", c: "ConceptionPoint" }, common)
      : call<{ List: LiveItem[]; Notice?: string; date?: string }>(
          "his",
          "POST",
          { a: "ZhiBoContent", c: "HisConceptionPoint", Date: date },
          common,
        ),

  newHighTrend: (groupId: string, common: Common) =>
    call<{ x: string[] }>("his", "POST", { a: "GetDayNewHigh_W28", c: "StockNewHigh", GroupID: groupId }, common),

  holidays: (common: Common) =>
    call<{ List: string[] }>("his", "POST", { a: "GetHoliday", c: "YiDongKanPan" }, common),

  news: (index: number, common: Common, st = 30) =>
    call<{
      List: Array<{
        Time: string;
        Content: string;
        ID: string;
        URL: string;
        Type: number;
        StockID: string;
        StockName: string;
      }>;
    }>("lhb", "POST", { a: "AppNews", c: "UserInfo", Index: index, st }, common),
};

export type ThemeItem = {
  ID: string;
  Name: string;
  Hot?: number;
  Sort?: number;
  ZTNum?: number;
  UpNum?: number;
  New?: number;
  List?: Array<{ CID: string; Name: string; pinyin?: string }>;
};

export type Seat = {
  ID: string;
  Name: string;
  Day: string;
  StockID: string;
  Buy: string;
  Sell: string;
  PX: string;
  YouZiIcon?: number | string;
  GroupIcon?: string[];
};

export type LiveItem = {
  ID: string;
  UID: string;
  Time: number;
  Comment: string;
  Type: string;
  UserName: string;
  Image?: string;
  Stock?: Array<[string, string, number?]>;
  DisStock?: Array<[string, string]>;
  ShareData?: { ZDTJ?: string; ZDTJ_info?: Record<string, string> };
};
