using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Net.Sockets;
using System.Text;
using System.Text.RegularExpressions;

namespace ShunshiTdx
{
    public static class TdxApi
    {
        static readonly object Gate = new object();
        static HqClient Client;
        static string ClientHost;
        static List<Block> CacheGn;
        static List<Block> CacheZs;
        static DateTime CacheBlockUntil;
        static List<Sec> CacheSh;
        static List<Sec> CacheSz;
        static DateTime CacheListUntil;
        static readonly string[] HqHosts = new string[] {
            "180.153.18.170",
            "115.238.56.198",
            "124.71.187.122",
            "122.51.120.217"
        };

        public static string Status()
        {
            lock (Gate)
            {
                try
                {
                    EnsureHq();
                    return "{\"ok\":true,\"host\":" + JStr(ClientHost) + "}";
                }
                catch (Exception ex)
                {
                    return "{\"ok\":false,\"error\":" + JStr(UserMsg(ex)) + "}";
                }
            }
        }

        public static string Snapshot(string universe, string sort, string mode, string vipdoc)
        {
            lock (Gate)
            {
                try
                {
                    if (string.IsNullOrEmpty(universe)) universe = "all";
                    if (string.IsNullOrEmpty(sort)) sort = "change";
                    if (string.IsNullOrEmpty(mode)) mode = "hq";
                    if (mode == "local" || mode == "tdx-local")
                        return BuildLocal(universe, sort, vipdoc);
                    return BuildHq(universe, sort);
                }
                catch (Exception ex)
                {
                    return EmptySnap(universe, sort, mode == "local" || mode == "tdx-local" ? "tdx-local" : "tdx-hq", UserMsg(ex));
                }
            }
        }

        static string BuildHq(string universe, string sort)
        {
            EnsureHq();
            List<Block> concepts = DownloadBlocks("block_gn.dat", "concept");
            List<Block> industries = universe == "concept" ? new List<Block>() : DownloadBlocks("block.dat", "industry");
            EnsureLists();
            Dictionary<string, string> names = NameMap();
            List<Block> wanted = FilterBlocks(Concat(concepts, industries), universe);
            List<Sec> rankedSeeds = new List<Sec>();
            for (int i = 0; i < CacheSh.Count; i++)
            {
                Sec s = CacheSh[i];
                if (!s.Code.StartsWith("88") || s.Code.StartsWith("888") || IsNoise(s.Name)) continue;
                bool industryCode = s.Code.StartsWith("880") && s.Code.Length >= 4 && s.Code[3] >= '3' && s.Code[3] <= '9';
                bool conceptCode = s.Code.StartsWith("881") || s.Code.StartsWith("8804") || s.Code.StartsWith("8805");
                if (universe == "industry" && !industryCode) continue;
                if (universe == "concept" && !conceptCode) continue;
                if (universe != "industry" && universe != "concept" && !industryCode && !conceptCode) continue;
                rankedSeeds.Add(s);
            }
            List<Quote> seedQuotes = Quotes(ToStocks(rankedSeeds, 1));
            Dictionary<string, Quote> seedQ = IndexQuotes(seedQuotes);
            List<SeedBoard> seedBoards = new List<SeedBoard>();
            for (int i = 0; i < rankedSeeds.Count; i++)
            {
                Sec seed = rankedSeeds[i];
                Block block = MatchBlock(wanted, seed.Name);
                if (block == null) continue;
                Quote q;
                if (!seedQ.TryGetValue(seed.Code, out q) || q == null) continue;
                double? pct = ChangePct(q.Price, q.LastClose);
                if (!pct.HasValue) continue;
                SeedBoard sb = new SeedBoard();
                sb.Block = block;
                sb.Change = pct.Value;
                sb.Amount = q.Amount;
                seedBoards.Add(sb);
            }
            seedBoards.Sort(delegate(SeedBoard a, SeedBoard b)
            {
                if (sort == "amount" || sort == "inflow") return b.Amount.CompareTo(a.Amount);
                return b.Change.CompareTo(a.Change);
            });
            int take = sort == "limitUp" ? 14 : 10;
            List<Block> useBlocks = UniqueBlocks(seedBoards, take);
            if (useBlocks.Count < 6)
                useBlocks = UniqueBlocks(RankBySample(wanted, sort), take);
            return Assemble(universe, sort, "tdx-hq", useBlocks, names, Quotes(MemberAndIndex(useBlocks)), null);
        }

        static List<SeedBoard> RankBySample(List<Block> wanted, string sort)
        {
            List<string> codes = SampleCodes(wanted, 8);
            Stock[] stocks = new Stock[codes.Count];
            for (int i = 0; i < codes.Count; i++)
                stocks[i] = new Stock(MarketFromCode(codes[i]), codes[i]);
            Dictionary<string, Quote> map = IndexQuotes(Quotes(stocks));
            List<SeedBoard> seeded = new List<SeedBoard>();
            for (int i = 0; i < wanted.Count; i++)
            {
                Block block = wanted[i];
                List<Quote> qs = new List<Quote>();
                int n = Math.Min(8, block.Codes.Count);
                for (int j = 0; j < n; j++)
                {
                    Quote q;
                    if (map.TryGetValue(block.Codes[j], out q) && q != null) qs.Add(q);
                }
                BoardStat st = Stats(qs);
                if (!st.Change.HasValue) continue;
                SeedBoard sb = new SeedBoard();
                sb.Block = block;
                sb.Change = st.Change.Value;
                sb.Amount = st.Amount;
                seeded.Add(sb);
            }
            seeded.Sort(delegate(SeedBoard a, SeedBoard b)
            {
                if (sort == "amount" || sort == "inflow") return b.Amount.CompareTo(a.Amount);
                return b.Change.CompareTo(a.Change);
            });
            return seeded;
        }

        static string BuildLocal(string universe, string sort, string vipdoc)
        {
            string doc = string.IsNullOrEmpty(vipdoc) ? @"E:\new_tdx\vipdoc" : vipdoc;
            doc = doc.Replace("/", "\\").TrimEnd('\\');
            string root = Regex.Replace(doc, @"\\vipdoc$", "", RegexOptions.IgnoreCase);
            if (root == doc) root = Path.GetDirectoryName(doc);
            string hqCache = Path.Combine(root, "T0002", "hq_cache");
            if (!Directory.Exists(doc))
            {
                return EmptySnap(universe, sort, "tdx-local",
                    "找不到通达信本地库 " + doc + "。请确认 E:\\new_tdx\\vipdoc 存在。");
            }
            List<Block> blocks = new List<Block>();
            byte[] gn = ReadFile(Path.Combine(hqCache, "block_gn.dat"));
            byte[] hy = ReadFile(Path.Combine(hqCache, "block.dat"));
            byte[] zs = ReadFile(Path.Combine(hqCache, "block_zs.dat"));
            if (gn != null) blocks.AddRange(ParseBlockDat(gn, "concept"));
            if (hy != null) blocks.AddRange(ParseBlockDat(hy, "industry"));
            else if (zs != null) blocks.AddRange(ParseBlockDat(zs, "industry"));
            if (blocks.Count == 0)
            {
                return EmptySnap(universe, sort, "tdx-local",
                    "找到了 vipdoc，但板块文件不在 " + hqCache + "。请确认 T0002\\hq_cache\\block_gn.dat 存在，或改用「通达信实时」。");
            }
            List<Block> wanted = FilterBlocks(blocks, universe);
            Dictionary<string, Quote> seedMap = ReadManyDays(doc, SampleCodes(wanted, 16));
            List<SeedBoard> seeded = new List<SeedBoard>();
            for (int i = 0; i < wanted.Count; i++)
            {
                Block block = wanted[i];
                List<Quote> qs = new List<Quote>();
                int n = Math.Min(16, block.Codes.Count);
                for (int j = 0; j < n; j++)
                {
                    Quote q;
                    if (seedMap.TryGetValue(block.Codes[j], out q) && q != null) qs.Add(q);
                }
                BoardStat st = Stats(qs);
                if (!st.Change.HasValue) continue;
                SeedBoard sb = new SeedBoard();
                sb.Block = block;
                sb.Change = st.Change.Value;
                sb.Amount = st.Amount;
                seeded.Add(sb);
            }
            seeded.Sort(delegate(SeedBoard a, SeedBoard b)
            {
                if (sort == "amount" || sort == "inflow") return b.Amount.CompareTo(a.Amount);
                return b.Change.CompareTo(a.Change);
            });
            List<Block> useBlocks = UniqueBlocks(seeded, sort == "limitUp" ? 14 : 10);
            Dictionary<string, Quote> qmap = ReadManyDays(doc, ConcatCodes(MemberCodes(useBlocks), IndexCodes()));
            Dictionary<string, string> names = new Dictionary<string, string>();
            return Assemble(universe, sort, "tdx-local", useBlocks, names, ToList(qmap),
                "通达信本地用的是 vipdoc 日线（最后两根K线），不是盘中 tick。盘中请选「通达信实时」。");
        }

        static string Assemble(string universe, string sort, string source, List<Block> useBlocks,
            Dictionary<string, string> names, List<Quote> quotes, string extraError)
        {
            Dictionary<string, Quote> qmap = IndexQuotes(quotes);
            List<Enriched> enriched = new List<Enriched>();
            for (int i = 0; i < useBlocks.Count; i++)
            {
                Block block = useBlocks[i];
                List<Member> members = new List<Member>();
                for (int j = 0; j < block.Codes.Count; j++)
                {
                    string code = block.Codes[j];
                    Quote q;
                    if (!qmap.TryGetValue(code, out q) || q == null || q.Price <= 0) continue;
                    string name = names.ContainsKey(code) ? names[code] : code;
                    if (IsSt(name)) continue;
                    double? pct = ChangePct(q.Price, q.LastClose);
                    if (!pct.HasValue) continue;
                    Member m = new Member();
                    m.Code = code;
                    m.Name = name;
                    m.Market = EastmoneyMarket(code);
                    m.Price = q.Price;
                    m.Change = pct.Value;
                    m.Amount = q.Amount;
                    m.High = q.High;
                    m.LastClose = q.LastClose;
                    members.Add(m);
                }
                if (members.Count < 4) continue;
                List<Quote> mq = new List<Quote>();
                for (int j = 0; j < members.Count; j++)
                {
                    Quote q;
                    if (qmap.TryGetValue(members[j].Code, out q)) mq.Add(q);
                }
                BoardStat st = Stats(mq);
                Enriched en = new Enriched();
                en.Block = block;
                en.Members = members;
                en.Change = st.Change;
                en.Amount = st.Amount;
                en.Up = st.Up;
                en.Down = st.Down;
                en.Zt = 0;
                en.Zb = 0;
                for (int j = 0; j < members.Count; j++)
                {
                    Member m = members[j];
                    if (IsLimitUp(m.Code, m.Name, m.Price, m.LastClose)) en.Zt++;
                    else if (IsLimitHigh(m.Code, m.Name, m.High, m.LastClose)) en.Zb++;
                }
                en.Leaders = RankLeaders(members);
                enriched.Add(en);
            }
            if (sort == "limitUp")
            {
                enriched.Sort(delegate(Enriched a, Enriched b)
                {
                    int c = b.Zt.CompareTo(a.Zt);
                    if (c != 0) return c;
                    double ac = a.Change.HasValue ? a.Change.Value : 0;
                    double bc = b.Change.HasValue ? b.Change.Value : 0;
                    return bc.CompareTo(ac);
                });
            }
            int ztCount = 0, zbCount = 0;
            for (int i = 0; i < enriched.Count; i++)
            {
                ztCount += enriched[i].Zt;
                zbCount += enriched[i].Zb;
            }
            List<Enriched> top = TakeEnriched(enriched, 3);
            List<MarketLeaderEntry> marketLeaders = RankMarketLeaders(enriched);
            string note = extraError;
            if (sort == "inflow")
                note = MergeNote(note, "通达信没有主力净流入，已按成交额排序");
            return RenderSnap(universe, sort, source, qmap, top, marketLeaders, ztCount, zbCount, note);
        }

        static List<MarketLeaderEntry> RankMarketLeaders(List<Enriched> enriched)
        {
            Dictionary<string, MarketLeaderEntry> byCode = new Dictionary<string, MarketLeaderEntry>();
            for (int i = 0; i < enriched.Count; i++)
            {
                Enriched en = enriched[i];
                string sector = en.Block == null ? "" : en.Block.Name;
                for (int j = 0; j < en.Members.Count; j++)
                {
                    Member m = en.Members[j];
                    if (!IsLimitUp(m.Code, m.Name, m.Price, m.LastClose)) continue;
                    if (IsSt(m.Name)) continue;
                    if (!byCode.ContainsKey(m.Code))
                    {
                        MarketLeaderEntry entry = new MarketLeaderEntry();
                        entry.Member = m;
                        entry.Sector = sector;
                        byCode[m.Code] = entry;
                    }
                }
            }
            List<MarketLeaderEntry> list = new List<MarketLeaderEntry>(byCode.Values);
            list.Sort(delegate(MarketLeaderEntry a, MarketLeaderEntry b)
            {
                int c = b.Member.Change.CompareTo(a.Member.Change);
                if (c != 0) return c;
                return b.Member.Amount.CompareTo(a.Member.Amount);
            });
            if (list.Count > 3) list = list.GetRange(0, 3);
            return list;
        }

        static string RenderSnap(string universe, string sort, string source, Dictionary<string, Quote> qmap,
            List<Enriched> top, List<MarketLeaderEntry> marketLeaders, int ztCount, int zbCount, string error)
        {
            DateTime bj = DateTime.UtcNow.AddHours(8);
            StringBuilder sb = new StringBuilder();
            sb.Append("{\"tradeDate\":").Append(JStr(bj.ToString("yyyyMMdd")));
            sb.Append(",\"updatedAt\":").Append(JStr(DateTime.UtcNow.ToString("o")));
            sb.Append(",\"session\":").Append(JStr(SessionOf(bj)));
            sb.Append(",\"universe\":").Append(JStr(universe));
            sb.Append(",\"sort\":").Append(JStr(sort));
            sb.Append(",\"source\":").Append(JStr(source));
            sb.Append(",\"indices\":[");
            string[][] idx = new string[][] {
                new string[] { "000001", "1", "上证指数" },
                new string[] { "399001", "0", "深证成指" },
                new string[] { "399006", "0", "创业板指" },
                new string[] { "000688", "1", "科创50" }
            };
            for (int i = 0; i < idx.Length; i++)
            {
                if (i > 0) sb.Append(",");
                Quote q;
                qmap.TryGetValue(idx[i][0], out q);
                double? pct = q == null ? (double?)null : ChangePct(q.Price, q.LastClose);
                sb.Append("{\"code\":").Append(JStr(idx[i][0]));
                sb.Append(",\"name\":").Append(JStr(idx[i][2]));
                sb.Append(",\"price\":").Append(q == null ? "null" : JNum(q.Price));
                sb.Append(",\"changePercent\":").Append(JNum(pct));
                sb.Append(",\"change\":").Append(q == null ? "null" : JNum(q.Price - q.LastClose));
                sb.Append(",\"amount\":").Append(q == null ? "null" : JNum(q.Amount));
                sb.Append(",\"upCount\":null,\"downCount\":null,\"flatCount\":null}");
            }
            sb.Append("],\"ztCount\":").Append(ztCount).Append(",\"zbCount\":").Append(zbCount);
            sb.Append(",\"marketLeaders\":[");
            string[] mktRanks = new string[] { "总龙头", "龙二", "龙三" };
            for (int i = 0; i < marketLeaders.Count; i++)
            {
                if (i > 0) sb.Append(",");
                MarketLeaderEntry entry = marketLeaders[i];
                Member m = entry.Member;
                string reason = "全市场 · 通达信按涨停价判定（无先封时间）";
                if (!string.IsNullOrEmpty(entry.Sector))
                    reason = entry.Sector + " · " + reason;
                sb.Append("{\"rank\":").Append(JStr(mktRanks[i]));
                sb.Append(",\"code\":").Append(JStr(m.Code));
                sb.Append(",\"name\":").Append(JStr(m.Name));
                sb.Append(",\"market\":").Append(m.Market);
                sb.Append(",\"price\":").Append(JNum(m.Price));
                sb.Append(",\"changePercent\":").Append(JNum(m.Change));
                sb.Append(",\"amount\":").Append(JNum(m.Amount));
                sb.Append(",\"turnoverRate\":null,\"speed\":null,\"mainNetInflow\":null");
                sb.Append(",\"isLimitUp\":true,\"isBroken\":false");
                sb.Append(",\"consecutiveBoards\":1");
                sb.Append(",\"firstSealTime\":null,\"lastSealTime\":null,\"sealAmount\":null");
                sb.Append(",\"openCount\":0,\"sealKind\":null");
                sb.Append(",\"sectorName\":").Append(JStr(entry.Sector));
                sb.Append(",\"reason\":").Append(JStr(reason));
                sb.Append(",\"trend\":[]}");
            }
            sb.Append("],\"sectors\":[");
            string[] ranks = new string[] { "龙一", "龙二", "龙三" };
            for (int i = 0; i < top.Count; i++)
            {
                if (i > 0) sb.Append(",");
                Enriched en = top[i];
                sb.Append("{\"rank\":").Append(i + 1);
                sb.Append(",\"code\":").Append(JStr(en.Block.Kind + ":" + en.Block.Name));
                sb.Append(",\"name\":").Append(JStr(en.Block.Name));
                sb.Append(",\"kind\":").Append(JStr(en.Block.Kind));
                sb.Append(",\"changePercent\":").Append(JNum(en.Change));
                sb.Append(",\"amount\":").Append(JNum(en.Amount));
                sb.Append(",\"mainNetInflow\":null");
                sb.Append(",\"upCount\":").Append(en.Up);
                sb.Append(",\"downCount\":").Append(en.Down);
                sb.Append(",\"memberCount\":").Append(en.Members.Count);
                sb.Append(",\"limitUpCount\":").Append(en.Zt);
                sb.Append(",\"brokenCount\":").Append(en.Zb);
                sb.Append(",\"trend\":[],\"leaders\":[");
                for (int j = 0; j < en.Leaders.Count; j++)
                {
                    if (j > 0) sb.Append(",");
                    Member m = en.Leaders[j];
                    bool zt = IsLimitUp(m.Code, m.Name, m.Price, m.LastClose);
                    bool zb = !zt && IsLimitHigh(m.Code, m.Name, m.High, m.LastClose);
                    string reason = zt ? "通达信按涨停价判定（无先封时间）"
                        : zb ? "通达信按最高价触及涨停判定炸板"
                        : "板块内涨幅 " + (m.Change >= 0 ? "+" : "") + m.Change.ToString("0.00", CultureInfo.InvariantCulture) + "%";
                    sb.Append("{\"rank\":").Append(JStr(ranks[j]));
                    sb.Append(",\"code\":").Append(JStr(m.Code));
                    sb.Append(",\"name\":").Append(JStr(m.Name));
                    sb.Append(",\"market\":").Append(m.Market);
                    sb.Append(",\"price\":").Append(JNum(m.Price));
                    sb.Append(",\"changePercent\":").Append(JNum(m.Change));
                    sb.Append(",\"amount\":").Append(JNum(m.Amount));
                    sb.Append(",\"turnoverRate\":null,\"speed\":null,\"mainNetInflow\":null");
                    sb.Append(",\"isLimitUp\":").Append(zt ? "true" : "false");
                    sb.Append(",\"isBroken\":").Append(zb ? "true" : "false");
                    sb.Append(",\"consecutiveBoards\":").Append(zt ? "1" : "null");
                    sb.Append(",\"firstSealTime\":null,\"lastSealTime\":null,\"sealAmount\":null");
                    sb.Append(",\"openCount\":").Append(zb ? "1" : zt ? "0" : "null");
                    sb.Append(",\"sealKind\":null,\"reason\":").Append(JStr(reason));
                    sb.Append(",\"trend\":[]}");
                }
                sb.Append("]}");
            }
            sb.Append("]");
            if (!string.IsNullOrEmpty(error)) sb.Append(",\"error\":").Append(JStr(error));
            sb.Append("}");
            return sb.ToString();
        }

        static string EmptySnap(string universe, string sort, string source, string error)
        {
            DateTime bj = DateTime.UtcNow.AddHours(8);
            StringBuilder sb = new StringBuilder();
            sb.Append("{\"tradeDate\":\"\",\"updatedAt\":").Append(JStr(DateTime.UtcNow.ToString("o")));
            sb.Append(",\"session\":").Append(JStr(SessionOf(bj)));
            sb.Append(",\"universe\":").Append(JStr(universe));
            sb.Append(",\"sort\":").Append(JStr(sort));
            sb.Append(",\"source\":").Append(JStr(source));
            sb.Append(",\"indices\":[],\"ztCount\":0,\"zbCount\":0,\"marketLeaders\":[],\"sectors\":[]");
            sb.Append(",\"error\":").Append(JStr(error)).Append("}");
            return sb.ToString();
        }

        static void EnsureHq()
        {
            if (Client != null && Client.Alive) return;
            Exception last = null;
            for (int i = 0; i < HqHosts.Length; i++)
            {
                try
                {
                    HqClient c = new HqClient();
                    c.Connect(HqHosts[i], 7709);
                    List<Quote> probe = c.Quotes(new Stock[] {
                        new Stock(1, "600519"),
                        new Stock(0, "000001")
                    });
                    bool ok = false;
                    for (int k = 0; k < probe.Count; k++) if (probe[k].Price > 0) ok = true;
                    if (!ok)
                    {
                        c.Close();
                        throw new Exception("empty quotes");
                    }
                    Client = c;
                    ClientHost = HqHosts[i];
                    return;
                }
                catch (Exception ex)
                {
                    last = ex;
                }
            }
            throw last ?? new Exception("TDX_HQ_DOWN");
        }

        static void EnsureLists()
        {
            if (CacheSh != null && DateTime.UtcNow < CacheListUntil) return;
            CacheSh = Client.SecurityList(1);
            CacheSz = Client.SecurityList(0);
            CacheListUntil = DateTime.UtcNow.AddHours(6);
        }

        static Dictionary<string, string> NameMap()
        {
            Dictionary<string, string> map = new Dictionary<string, string>();
            AddNames(map, CacheSh);
            AddNames(map, CacheSz);
            return map;
        }

        static void AddNames(Dictionary<string, string> map, List<Sec> list)
        {
            if (list == null) return;
            for (int i = 0; i < list.Count; i++)
            {
                if (!string.IsNullOrEmpty(list[i].Name) && !map.ContainsKey(list[i].Code))
                    map.Add(list[i].Code, list[i].Name);
            }
        }

        static List<Block> DownloadBlocks(string fileName, string kind)
        {
            if (kind == "concept" && CacheGn != null && DateTime.UtcNow < CacheBlockUntil) return CacheGn;
            if (kind == "industry" && CacheZs != null && DateTime.UtcNow < CacheBlockUntil) return CacheZs;
            int size = Client.BlockMeta(fileName);
            if (size <= 0) return new List<Block>();
            MemoryStream ms = new MemoryStream();
            int one = 0x7530;
            for (int start = 0; start < size; start += one)
            {
                byte[] piece = Client.BlockChunk(fileName, start, size);
                int want = Math.Min(one, size - start);
                int from = piece.Length > 4 ? 4 : 0;
                int len = Math.Min(want, piece.Length - from);
                if (len > 0) ms.Write(piece, from, len);
            }
            List<Block> blocks = ParseBlockDat(ms.ToArray(), kind);
            CacheBlockUntil = DateTime.UtcNow.AddHours(1);
            if (kind == "concept") CacheGn = blocks;
            else CacheZs = blocks;
            return blocks;
        }

        static List<Quote> Quotes(Stock[] stocks)
        {
            List<Quote> all = new List<Quote>();
            int i = 0;
            while (i < stocks.Length)
            {
                int n = Math.Min(80, stocks.Length - i);
                Stock[] batch = new Stock[n];
                Array.Copy(stocks, i, batch, 0, n);
                all.AddRange(Client.Quotes(batch));
                i += n;
            }
            return all;
        }

        static Stock[] MemberAndIndex(List<Block> blocks)
        {
            Dictionary<string, Stock> map = new Dictionary<string, Stock>();
            for (int i = 0; i < blocks.Count; i++)
            {
                for (int j = 0; j < blocks[i].Codes.Count; j++)
                {
                    string code = blocks[i].Codes[j];
                    if (!map.ContainsKey(code)) map.Add(code, new Stock(MarketFromCode(code), code));
                }
            }
            AddStock(map, 1, "000001");
            AddStock(map, 0, "399001");
            AddStock(map, 0, "399006");
            AddStock(map, 1, "000688");
            Stock[] arr = new Stock[map.Count];
            map.Values.CopyTo(arr, 0);
            return arr;
        }

        static void AddStock(Dictionary<string, Stock> map, int market, string code)
        {
            if (!map.ContainsKey(code)) map.Add(code, new Stock(market, code));
        }

        static Stock[] ToStocks(List<Sec> list, int market)
        {
            Stock[] arr = new Stock[list.Count];
            for (int i = 0; i < list.Count; i++) arr[i] = new Stock(market, list[i].Code);
            return arr;
        }

        static List<Block> FilterBlocks(List<Block> blocks, string universe)
        {
            List<Block> outList = new List<Block>();
            for (int i = 0; i < blocks.Count; i++)
            {
                Block b = blocks[i];
                if (IsNoise(b.Name)) continue;
                if (universe == "concept" && b.Kind != "concept") continue;
                if (b.Codes.Count < 4) continue;
                outList.Add(b);
            }
            return outList;
        }

        static List<Block> UniqueBlocks(List<SeedBoard> seeds, int take)
        {
            List<Block> list = new List<Block>();
            Dictionary<string, bool> seen = new Dictionary<string, bool>();
            for (int i = 0; i < seeds.Count && list.Count < take; i++)
            {
                string key = seeds[i].Block.Kind + ":" + seeds[i].Block.Name;
                if (seen.ContainsKey(key)) continue;
                seen.Add(key, true);
                list.Add(seeds[i].Block);
            }
            return list;
        }

        static List<Block> TakeBlocks(List<Block> blocks, int n)
        {
            List<Block> list = new List<Block>();
            for (int i = 0; i < blocks.Count && i < n; i++) list.Add(blocks[i]);
            return list;
        }

        static List<Enriched> TakeEnriched(List<Enriched> list, int n)
        {
            List<Enriched> outList = new List<Enriched>();
            for (int i = 0; i < list.Count && i < n; i++) outList.Add(list[i]);
            return outList;
        }

        static Block MatchBlock(List<Block> blocks, string name)
        {
            string needle = (name ?? "").Trim();
            for (int i = 0; i < blocks.Count; i++)
                if (blocks[i].Name == needle) return blocks[i];
            for (int i = 0; i < blocks.Count; i++)
            {
                string n = blocks[i].Name;
                if (n.StartsWith(needle) || needle.StartsWith(n)) return blocks[i];
            }
            return null;
        }

        static List<Block> Concat(List<Block> a, List<Block> b)
        {
            List<Block> c = new List<Block>();
            c.AddRange(a);
            c.AddRange(b);
            return c;
        }

        static List<string> SampleCodes(List<Block> blocks, int per)
        {
            Dictionary<string, bool> seen = new Dictionary<string, bool>();
            List<string> codes = new List<string>();
            for (int i = 0; i < blocks.Count; i++)
            {
                int n = Math.Min(per, blocks[i].Codes.Count);
                for (int j = 0; j < n; j++)
                {
                    string code = blocks[i].Codes[j];
                    if (seen.ContainsKey(code)) continue;
                    seen.Add(code, true);
                    codes.Add(code);
                }
            }
            return codes;
        }

        static List<string> MemberCodes(List<Block> blocks)
        {
            Dictionary<string, bool> seen = new Dictionary<string, bool>();
            List<string> codes = new List<string>();
            for (int i = 0; i < blocks.Count; i++)
            {
                for (int j = 0; j < blocks[i].Codes.Count; j++)
                {
                    string code = blocks[i].Codes[j];
                    if (seen.ContainsKey(code)) continue;
                    seen.Add(code, true);
                    codes.Add(code);
                }
            }
            return codes;
        }

        static List<string> ConcatCodes(List<string> a, string[] b)
        {
            List<string> c = new List<string>(a);
            for (int i = 0; i < b.Length; i++) if (!c.Contains(b[i])) c.Add(b[i]);
            return c;
        }

        static string[] IndexCodes()
        {
            return new string[] { "000001", "399001", "399006", "000688" };
        }

        static Dictionary<string, Quote> IndexQuotes(List<Quote> quotes)
        {
            Dictionary<string, Quote> map = new Dictionary<string, Quote>();
            for (int i = 0; i < quotes.Count; i++)
            {
                if (!map.ContainsKey(quotes[i].Code)) map.Add(quotes[i].Code, quotes[i]);
            }
            return map;
        }

        static List<Quote> ToList(Dictionary<string, Quote> map)
        {
            List<Quote> list = new List<Quote>();
            foreach (KeyValuePair<string, Quote> kv in map) list.Add(kv.Value);
            return list;
        }

        static Dictionary<string, Quote> ReadManyDays(string vipdoc, List<string> codes)
        {
            Dictionary<string, Quote> map = new Dictionary<string, Quote>();
            for (int i = 0; i < codes.Count; i++)
            {
                Quote q = ReadDay(vipdoc, codes[i]);
                if (q != null && !map.ContainsKey(q.Code)) map.Add(q.Code, q);
            }
            return map;
        }

        static Quote ReadDay(string vipdoc, string code)
        {
            int market = MarketFromCode(code);
            string dir = market == 1 ? "sh" : market == 2 ? "bj" : "sz";
            string file = Path.Combine(vipdoc, dir, "lday", dir + code + ".day");
            if (!File.Exists(file)) return null;
            FileInfo fi = new FileInfo(file);
            if (fi.Length < 32) return null;
            int take = fi.Length >= 64 ? 64 : 32;
            byte[] buf = new byte[take];
            FileStream fs = new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
            try
            {
                fs.Seek(-take, SeekOrigin.End);
                int n = fs.Read(buf, 0, take);
                if (n < 32) return null;
                if (n < take)
                {
                    byte[] slim = new byte[n];
                    Array.Copy(buf, slim, n);
                    buf = slim;
                }
            }
            finally { fs.Close(); }
            int bars = buf.Length / 32;
            int last = (bars - 1) * 32;
            int prev = bars >= 2 ? (bars - 2) * 32 : last;
            Quote q = new Quote();
            q.Market = market;
            q.Code = code;
            q.Price = TdxPrice(BitConverter.ToInt32(buf, last + 16));
            q.LastClose = TdxPrice(BitConverter.ToInt32(buf, prev + 16));
            q.Open = TdxPrice(BitConverter.ToInt32(buf, last + 4));
            q.High = TdxPrice(BitConverter.ToInt32(buf, last + 8));
            q.Low = TdxPrice(BitConverter.ToInt32(buf, last + 12));
            q.Amount = BitConverter.ToSingle(buf, last + 20);
            q.Volume = BitConverter.ToInt32(buf, last + 24);
            return q;
        }

        static byte[] ReadFile(string path)
        {
            try
            {
                if (!File.Exists(path)) return null;
                return File.ReadAllBytes(path);
            }
            catch { return null; }
        }

        static List<Block> ParseBlockDat(byte[] buffer, string kind)
        {
            List<Block> blocks = new List<Block>();
            if (buffer == null || buffer.Length < 386) return blocks;
            int pos = 384;
            int num = BitConverter.ToUInt16(buffer, pos);
            pos += 2;
            Encoding gbk = Encoding.GetEncoding(936);
            for (int i = 0; i < num; i++)
            {
                if (pos + 13 > buffer.Length) break;
                string name = gbk.GetString(buffer, pos, 9).TrimEnd('\0', ' ', '\r', '\n');
                pos += 9;
                int stockCount = BitConverter.ToUInt16(buffer, pos);
                pos += 4;
                int begin = pos;
                List<string> codes = new List<string>();
                int n = Math.Min(stockCount, 400);
                for (int j = 0; j < n; j++)
                {
                    if (pos + 7 > buffer.Length) break;
                    string code = Encoding.ASCII.GetString(buffer, pos, 6).TrimEnd('\0', ' ');
                    pos += 7;
                    if (code.Length == 6) codes.Add(code);
                }
                pos = begin + 2800;
                if (!string.IsNullOrEmpty(name) && codes.Count > 0)
                {
                    Block b = new Block();
                    b.Name = name;
                    b.Kind = kind;
                    b.Codes = codes;
                    blocks.Add(b);
                }
            }
            return blocks;
        }

        static BoardStat Stats(List<Quote> quotes)
        {
            BoardStat st = new BoardStat();
            double sum = 0;
            int n = 0;
            for (int i = 0; i < quotes.Count; i++)
            {
                st.Amount += quotes[i].Amount;
                double? pct = ChangePct(quotes[i].Price, quotes[i].LastClose);
                if (!pct.HasValue) continue;
                sum += pct.Value;
                n++;
                if (pct.Value > 0) st.Up++;
                else if (pct.Value < 0) st.Down++;
            }
            if (n > 0) st.Change = sum / n;
            return st;
        }

        static List<Member> RankLeaders(List<Member> members)
        {
            List<Member> copy = new List<Member>(members);
            copy.Sort(delegate(Member a, Member b)
            {
                bool az = IsLimitUp(a.Code, a.Name, a.Price, a.LastClose);
                bool bz = IsLimitUp(b.Code, b.Name, b.Price, b.LastClose);
                if (az != bz) return az ? -1 : 1;
                int c = b.Change.CompareTo(a.Change);
                if (c != 0) return c;
                return b.Amount.CompareTo(a.Amount);
            });
            List<Member> top = new List<Member>();
            for (int i = 0; i < copy.Count && i < 3; i++) top.Add(copy[i]);
            return top;
        }

        static int MarketFromCode(string code)
        {
            if (code.StartsWith("88") || code.StartsWith("6")) return 1;
            if (code.StartsWith("4") || code.StartsWith("8") || code.StartsWith("92")) return 2;
            return 0;
        }

        static int EastmoneyMarket(string code)
        {
            return MarketFromCode(code) == 1 ? 1 : 0;
        }

        static double TdxPrice(int raw)
        {
            if (raw == 0) return 0;
            if (Math.Abs(raw) >= 1000000) return raw / 1000.0;
            return raw / 100.0;
        }

        static double? ChangePct(double price, double last)
        {
            if (last == 0) return null;
            return (price - last) / last * 100.0;
        }

        static int LimitCap(string code, string name)
        {
            if (IsSt(name)) return 5;
            if (code.StartsWith("300") || code.StartsWith("301") || code.StartsWith("688") || code.StartsWith("689")) return 20;
            if (Regex.IsMatch(code, @"^[48]\d{5}$")) return 30;
            return 10;
        }

        static bool IsLimitUp(string code, string name, double price, double last)
        {
            double? pct = ChangePct(price, last);
            if (!pct.HasValue) return false;
            return pct.Value >= LimitCap(code, name) - 0.2;
        }

        static bool IsLimitHigh(string code, string name, double high, double last)
        {
            double? pct = ChangePct(high, last);
            if (!pct.HasValue) return false;
            return pct.Value >= LimitCap(code, name) - 0.2;
        }

        static bool IsSt(string name)
        {
            string n = (name ?? "").Replace(" ", "");
            return n.IndexOf("ST", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        static bool IsNoise(string name)
        {
            if (string.IsNullOrEmpty(name)) return true;
            string[] keys = new string[] {
                "昨日","前日","连板","涨停","跌停","破板","炸板","打板","首板","二板","三板",
                "历史新高","历史新低","近期新高","近期新低","近期解禁","公告","ST股","次新股",
                "沪股通","深股通","融资融券","转融通","高开低走","低开高走","高换手","成交活跃",
                "含一字","题材股","热股","多板","东方财富","通达信","总市值","流通市值","活筹市值",
                "平均股价","新标准券","涨跌家","上证","深证","中证","沪深","创业板指",
                "科创50","科创100","北证50","综指","成指","全指","MSCI","富时",
                "含H股","含B股","含GDR","含可转债","即将解禁","近已解禁","精选指数"
            };
            for (int i = 0; i < keys.Length; i++) if (name.IndexOf(keys[i]) >= 0) return true;
            return false;
        }

        static string SessionOf(DateTime bj)
        {
            if (bj.DayOfWeek == DayOfWeek.Saturday || bj.DayOfWeek == DayOfWeek.Sunday) return "weekend";
            int mins = bj.Hour * 60 + bj.Minute;
            if (mins < 9 * 60 + 15) return "pre";
            if (mins < 9 * 60 + 25) return "auction";
            if (mins < 11 * 60 + 30) return "morning";
            if (mins < 13 * 60) return "lunch";
            if (mins < 15 * 60 + 5) return "afternoon";
            return "closed";
        }

        static string UserMsg(Exception ex)
        {
            string m = ex == null ? "" : ex.Message;
            if (m == "TDX_HQ_DOWN" || m == "empty quotes") return "通达信实时行情服务器都连不上";
            if (m == "TDX_TIMEOUT") return "通达信行情读取超时";
            if (m == "TDX_CLOSED") return "通达信行情连接断开";
            if (string.IsNullOrEmpty(m)) return "通达信行情暂时不可用";
            return m;
        }

        static string JStr(string s)
        {
            if (s == null) return "null";
            StringBuilder sb = new StringBuilder("\"");
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                if (c == '\\' || c == '"') sb.Append('\\').Append(c);
                else if (c == '\n') sb.Append("\\n");
                else if (c == '\r') sb.Append("\\r");
                else sb.Append(c);
            }
            sb.Append("\"");
            return sb.ToString();
        }

        static string JNum(Nullable<double> v)
        {
            if (!v.HasValue) return "null";
            if (double.IsNaN(v.Value) || double.IsInfinity(v.Value)) return "null";
            return v.Value.ToString("0.####", CultureInfo.InvariantCulture);
        }

        static string MergeNote(string a, string b)
        {
            if (string.IsNullOrEmpty(a)) return b;
            if (string.IsNullOrEmpty(b)) return a;
            return a + "；" + b;
        }
    }

    sealed class HqClient
    {
        TcpClient tcp;
        NetworkStream stream;
        byte[] leftover = new byte[0];

        public bool Alive
        {
            get { return tcp != null && tcp.Connected; }
        }

        public void Connect(string host, int port)
        {
            tcp = new TcpClient();
            tcp.NoDelay = true;
            tcp.ReceiveTimeout = 20000;
            tcp.SendTimeout = 15000;
            IAsyncResult ar = tcp.BeginConnect(host, port, null, null);
            if (!ar.AsyncWaitHandle.WaitOne(5000, false))
            {
                try { tcp.Close(); } catch {}
                throw new Exception("timeout");
            }
            tcp.EndConnect(ar);
            stream = tcp.GetStream();
            leftover = new byte[0];
            Recv(Hex("0c0218930001030003000d0001"));
            Recv(Hex("0c0218940001030003000d0002"));
            Recv(Hex("0c031899000120002000db0fd5d0c9ccd6a4a8af0000008fc22540130000d500c9ccbdf0d7ea00000002"));
        }

        public void Close()
        {
            try { if (stream != null) stream.Close(); } catch {}
            try { if (tcp != null) tcp.Close(); } catch {}
            tcp = null;
            stream = null;
        }

        public List<Quote> Quotes(Stock[] stocks)
        {
            byte[] body = Recv(BuildQuotes(stocks));
            return ParseQuotes(body);
        }

        public List<Sec> SecurityList(int market)
        {
            List<Sec> list = new List<Sec>();
            for (int start = 0; start < 12000; start += 1000)
            {
                byte[] pkg = new byte[16];
                Buffer.BlockCopy(Hex("0c0118640101060006005004"), 0, pkg, 0, 12);
                WriteU16(pkg, 12, (ushort)market);
                WriteU16(pkg, 14, (ushort)start);
                byte[] body = Recv(pkg);
                List<Sec> page = ParseSecList(body, market);
                list.AddRange(page);
                if (page.Count < 1000) break;
            }
            return list;
        }

        public int BlockMeta(string fileName)
        {
            byte[] pkg = new byte[52];
            Buffer.BlockCopy(Hex("0c39186900012a002a00c502"), 0, pkg, 0, 12);
            byte[] name = Encoding.ASCII.GetBytes(fileName);
            Buffer.BlockCopy(name, 0, pkg, 12, Math.Min(name.Length, 40));
            byte[] body = Recv(pkg);
            if (body.Length < 4) return 0;
            return BitConverter.ToInt32(body, 0);
        }

        public byte[] BlockChunk(string fileName, int start, int size)
        {
            byte[] pkg = new byte[120];
            Buffer.BlockCopy(Hex("0c37186a00016e006e00b906"), 0, pkg, 0, 12);
            WriteU32(pkg, 12, (uint)start);
            WriteU32(pkg, 16, (uint)size);
            byte[] name = Encoding.ASCII.GetBytes(fileName);
            Buffer.BlockCopy(name, 0, pkg, 20, Math.Min(name.Length, 100));
            return Recv(pkg);
        }

        byte[] Recv(byte[] pkg)
        {
            stream.Write(pkg, 0, pkg.Length);
            byte[] head = Take(16, 20000);
            int zip = BitConverter.ToUInt16(head, 12);
            int unzip = BitConverter.ToUInt16(head, 14);
            byte[] body = zip > 0 ? Take(zip, 20000) : new byte[0];
            if (zip != unzip) return Inflate(body);
            return body;
        }

        byte[] Take(int n, int timeoutMs)
        {
            DateTime dead = DateTime.UtcNow.AddMilliseconds(timeoutMs);
            while (leftover.Length < n)
            {
                int remain = (int)(dead - DateTime.UtcNow).TotalMilliseconds;
                if (remain <= 0) throw new Exception("TDX_TIMEOUT");
                stream.ReadTimeout = Math.Max(remain, 1);
                byte[] buf = new byte[8192];
                int got;
                try { got = stream.Read(buf, 0, buf.Length); }
                catch (IOException) { throw new Exception("TDX_TIMEOUT"); }
                if (got <= 0) throw new Exception("TDX_CLOSED");
                byte[] next = new byte[leftover.Length + got];
                Buffer.BlockCopy(leftover, 0, next, 0, leftover.Length);
                Buffer.BlockCopy(buf, 0, next, leftover.Length, got);
                leftover = next;
            }
            byte[] outb = new byte[n];
            Buffer.BlockCopy(leftover, 0, outb, 0, n);
            byte[] rest = new byte[leftover.Length - n];
            if (rest.Length > 0) Buffer.BlockCopy(leftover, n, rest, 0, rest.Length);
            leftover = rest;
            return outb;
        }

        static byte[] Inflate(byte[] zlib)
        {
            if (zlib == null || zlib.Length < 2) return zlib ?? new byte[0];
            MemoryStream input = new MemoryStream(zlib, 2, Math.Max(0, zlib.Length - 2));
            DeflateStream ds = new DeflateStream(input, CompressionMode.Decompress);
            MemoryStream output = new MemoryStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = ds.Read(buf, 0, buf.Length)) > 0) output.Write(buf, 0, n);
            ds.Close();
            return output.ToArray();
        }

        static byte[] BuildQuotes(Stock[] stocks)
        {
            int stockLen = stocks.Length;
            int pkgdatalen = stockLen * 7 + 12;
            byte[] header = new byte[22];
            WriteU16(header, 0, 0x10c);
            WriteU32(header, 2, 0x02006320);
            WriteU16(header, 6, (ushort)pkgdatalen);
            WriteU16(header, 8, (ushort)pkgdatalen);
            WriteU32(header, 10, 0x5053e);
            WriteU32(header, 14, 0);
            WriteU16(header, 18, 0);
            WriteU16(header, 20, (ushort)stockLen);
            byte[] pkg = new byte[22 + stockLen * 7];
            Buffer.BlockCopy(header, 0, pkg, 0, 22);
            for (int i = 0; i < stockLen; i++)
            {
                int o = 22 + i * 7;
                pkg[o] = (byte)stocks[i].Market;
                byte[] c = Encoding.ASCII.GetBytes(stocks[i].Code.PadRight(6, '\0').Substring(0, 6));
                Buffer.BlockCopy(c, 0, pkg, o + 1, 6);
            }
            return pkg;
        }

        static List<Quote> ParseQuotes(byte[] body)
        {
            List<Quote> quotes = new List<Quote>();
            if (body == null || body.Length < 4) return quotes;
            int pos = 2;
            int num = BitConverter.ToUInt16(body, pos);
            pos += 2;
            for (int i = 0; i < num; i++)
            {
                if (pos + 9 > body.Length) break;
                int market = body[pos];
                string code = Encoding.ASCII.GetString(body, pos + 1, 6).TrimEnd('\0', ' ');
                pos += 9;
                int price = GetPrice(body, ref pos);
                int lastCloseDiff = GetPrice(body, ref pos);
                int openDiff = GetPrice(body, ref pos);
                int highDiff = GetPrice(body, ref pos);
                int lowDiff = GetPrice(body, ref pos);
                GetPrice(body, ref pos);
                GetPrice(body, ref pos);
                int volume = GetPrice(body, ref pos);
                GetPrice(body, ref pos);
                if (pos + 4 > body.Length) break;
                double amount = GetVolume(BitConverter.ToUInt32(body, pos));
                pos += 4;
                for (int skip = 0; skip < 24; skip++) GetPrice(body, ref pos);
                pos += 2;
                for (int skip = 0; skip < 4; skip++) GetPrice(body, ref pos);
                pos += 4;
                Quote q = new Quote();
                q.Market = market;
                q.Code = code;
                q.Price = (price) / 100.0;
                q.LastClose = (price + lastCloseDiff) / 100.0;
                q.Open = (price + openDiff) / 100.0;
                q.High = (price + highDiff) / 100.0;
                q.Low = (price + lowDiff) / 100.0;
                q.Amount = amount;
                q.Volume = volume;
                quotes.Add(q);
            }
            return quotes;
        }

        static List<Sec> ParseSecList(byte[] body, int market)
        {
            List<Sec> list = new List<Sec>();
            if (body == null || body.Length < 2) return list;
            int num = BitConverter.ToUInt16(body, 0);
            int pos = 2;
            Encoding gbk = Encoding.GetEncoding(936);
            for (int i = 0; i < num; i++)
            {
                if (pos + 29 > body.Length) break;
                string code = Encoding.ASCII.GetString(body, pos, 6).TrimEnd('\0', ' ');
                string name = gbk.GetString(body, pos + 8, 8).TrimEnd('\0', ' ', '\r', '\n');
                pos += 29;
                if (!string.IsNullOrEmpty(code))
                {
                    Sec s = new Sec();
                    s.Market = market;
                    s.Code = code;
                    s.Name = name;
                    list.Add(s);
                }
            }
            return list;
        }

        static int GetPrice(byte[] data, ref int pos)
        {
            if (pos >= data.Length) return 0;
            int posByte = 6;
            int bdata = data[pos];
            int intdata = bdata & 0x3f;
            bool sign = (bdata & 0x40) != 0;
            if ((bdata & 0x80) != 0)
            {
                while (true)
                {
                    pos++;
                    if (pos >= data.Length) break;
                    bdata = data[pos];
                    intdata += (bdata & 0x7f) << posByte;
                    posByte += 7;
                    if ((bdata & 0x80) == 0) break;
                }
            }
            pos++;
            return sign ? -intdata : intdata;
        }

        static double GetVolume(uint ivol)
        {
            uint logpoint = ivol >> 24;
            uint hleax = (ivol >> 16) & 0xff;
            uint lheax = (ivol >> 8) & 0xff;
            uint lleax = ivol & 0xff;
            int dwEcx = (int)(logpoint * 2 - 0x7f);
            int dwEdx = (int)(logpoint * 2 - 0x86);
            int dwEsi = (int)(logpoint * 2 - 0x8e);
            int dwEax = (int)(logpoint * 2 - 0x96);
            double dblXmm6 = Math.Pow(2, Math.Abs(dwEcx));
            if (dwEcx < 0) dblXmm6 = 1.0 / dblXmm6;
            double dblXmm4;
            if (hleax > 0x80) dblXmm4 = Math.Pow(2, dwEdx) * 128 + (hleax & 0x7f) * Math.Pow(2, dwEdx + 1);
            else if (dwEdx >= 0) dblXmm4 = Math.Pow(2, dwEdx) * hleax;
            else dblXmm4 = (1.0 / Math.Pow(2, dwEdx)) * hleax;
            double dblXmm3 = Math.Pow(2, dwEsi) * lheax;
            double dblXmm1 = Math.Pow(2, dwEax) * lleax;
            if ((hleax & 0x80) != 0)
            {
                dblXmm3 *= 2;
                dblXmm1 *= 2;
            }
            return dblXmm6 + dblXmm4 + dblXmm3 + dblXmm1;
        }

        static byte[] Hex(string hex)
        {
            byte[] r = new byte[hex.Length / 2];
            for (int i = 0; i < r.Length; i++)
                r[i] = Convert.ToByte(hex.Substring(i * 2, 2), 16);
            return r;
        }

        static void WriteU16(byte[] buf, int o, ushort v)
        {
            buf[o] = (byte)(v & 0xff);
            buf[o + 1] = (byte)(v >> 8);
        }

        static void WriteU32(byte[] buf, int o, uint v)
        {
            buf[o] = (byte)(v & 0xff);
            buf[o + 1] = (byte)((v >> 8) & 0xff);
            buf[o + 2] = (byte)((v >> 16) & 0xff);
            buf[o + 3] = (byte)((v >> 24) & 0xff);
        }
    }

    sealed class Stock
    {
        public int Market;
        public string Code;
        public Stock(int market, string code) { Market = market; Code = code; }
    }

    sealed class Quote
    {
        public int Market;
        public string Code;
        public double Price;
        public double LastClose;
        public double Open;
        public double High;
        public double Low;
        public double Amount;
        public double Volume;
    }

    sealed class Sec
    {
        public int Market;
        public string Code;
        public string Name;
    }

    sealed class Block
    {
        public string Name;
        public string Kind;
        public List<string> Codes;
    }

    sealed class SeedBoard
    {
        public Block Block;
        public double Change;
        public double Amount;
    }

    sealed class BoardStat
    {
        public Nullable<double> Change;
        public double Amount;
        public int Up;
        public int Down;
    }

    sealed class MarketLeaderEntry
    {
        public Member Member;
        public string Sector;
    }

    sealed class Member
    {
        public string Code;
        public string Name;
        public int Market;
        public double Price;
        public double Change;
        public double Amount;
        public double High;
        public double LastClose;
    }

    sealed class Enriched
    {
        public Block Block;
        public List<Member> Members;
        public List<Member> Leaders;
        public Nullable<double> Change;
        public double Amount;
        public int Up;
        public int Down;
        public int Zt;
        public int Zb;
    }
}
