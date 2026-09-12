# -*- coding: utf-8 -*-
"""Emit dashboard/index.html with data embedded inline (self-contained, works offline)."""
import json, os, sys

BASE = r"E:\工作文件\2026-09-12-00-44-43"
sys.path.insert(0, os.path.join(BASE, "scripts"))
d = json.load(open(os.path.join(BASE, "data", "dashboard_data.json"), encoding="utf-8"))

# ---------- 微博广告共享收益（MediaShareList）----------
from share_revenue import DAKE, JENI, CUT_START, CUT_END, WARN, CUT_ACCOUNTS

# ---------- 每日收益：完整时间线（历史全量 + MediaShareList 明细）----------
# 用户 2026-09-12 明确：每日收益要把【沿革所有表格里的每日微博收入】集中展示。
#
# 数据来源：
#   ① 「日期收入24年」（file_id UsgcWyuKlKKx）—— 2023-11 ~ 2024-12，共 421 天，
#      微博收入**全部算达克鸭唐**（该表没有杰尼龟说列）。
#      ⚠️ 源表笔误：sheet「24年1-7月」里的日期写成 2023/x/x，实际是 2024 年，
#         已按 sheet 名纠正（只有「11月」「12月」两张是 2023 年）。
#   ② 「25年收入」月度表 —— 2025-01-01 ~ 2026-07-26，共 511 天，达克 / 杰尼两列。
#   ③ MediaShareList 日明细 —— 2026-07-27 ~ 2026-09-11，共 47 天。
#
# 合并规则：【后写的优先】。42/25 两张表日期不重叠；MediaShareList 覆盖月度表尾部，
# 粒度更细，以它为准。
from collections import defaultdict as _dd
from daily_weibo import DAILY as _TAB_DAILY   # {date: (dake, jeni)}，已含 24年表

_dake_all, _jeni_all = {}, {}
_src_tab = {}    # 'h24' = 日期收入24年, 'tab' = 25年收入

for _dt in sorted(_TAB_DAILY):
    _a, _b = _TAB_DAILY[_dt]
    if _a or _b:
        _dake_all[_dt] = round(_a, 2)
        _jeni_all[_dt] = round(_b, 2)
        _src_tab[_dt] = "h24" if _dt < "2025-01-01" else "tab"

_src_ms = {}
_ms_overlap = 0
for _src, _tgt in ((DAKE, _dake_all), (JENI, _jeni_all)):
    for _k, _v in _src.items():
        if _k in _tgt:
            _ms_overlap += 1
        _tgt[_k] = round(_v, 2)
        _src_ms[_k] = 1

def _build_share(src, apply_cut, srcmap=None):
    """apply_cut=False 时该账号不扣减 —— 全部按正常结算计。"""
    days, cut_days = [], []
    for dt in sorted(src):
        rec = {"date": dt, "amount": round(src[dt], 2),
               "src": ("ms" if (srcmap and srcmap.get(dt)) else "tab")}
        if apply_cut and CUT_START <= dt <= CUT_END:
            cut_days.append(rec)
        else:
            days.append(rec)
    tot = round(sum(x["amount"] for x in days), 2)
    cut = round(sum(x["amount"] for x in cut_days), 2)
    # all = 按日期排序的完整序列（days + cut_days 不保证有序，必须重排）
    _all = sorted(days + cut_days, key=lambda x: x["date"])
    return {"days": days, "cut_days": cut_days, "total": tot, "cut": cut,
            "gross": round(tot + cut, 2),
            "cut_applies": apply_cut,
            "all": [{"date": x["date"], "amount": x["amount"], "src": x["src"]} for x in _all]}

share = {
    # 第一份 = 达克鸭唐（有扣减）；第二份 = 杰尼龟说（无扣减）—— 用户 2026-09-12 确认
    "dake": _build_share(_dake_all, True, _src_ms),
    "jeni": _build_share(_jeni_all, False, _src_ms),
    "cut_start": CUT_START, "cut_end": CUT_END, "warn": WARN,
}
share["total"] = round(share["dake"]["total"] + share["jeni"]["total"], 2)
share["cut"] = round(share["dake"]["cut"] + share["jeni"]["cut"], 2)
share["gross"] = round(share["dake"]["gross"] + share["jeni"]["gross"], 2)
share["cut_days_count"] = len(share["dake"]["cut_days"])

# ---------- 每日收益：年份 / 月份 两级切换 ----------
# 数据跨 2023-11 ~ 2026-09，共 33 个月、979 天 —— 按钮组放不下，改两级：
#   年份标签（2023 / 2024 / 2025 / 2026 / 全部）→ 下面再列该年的月份。
_ym_d, _ym_j = _dd(float), _dd(float)
for _src, _tgt in ((_dake_all, _ym_d), (_jeni_all, _ym_j)):
    for _k, _v in _src.items():
        _tgt[_k[:7]] += _v

_month_keys = sorted(set(_ym_d) | set(_ym_j))
def _ym_label(ym):
    y, m = ym.split("-")
    return "%s年%d月" % (y[2:], int(m))

share["months"] = [{"key": k, "label": _ym_label(k)} for k in _month_keys]
share["latest_month"] = _month_keys[-1] if _month_keys else ""
# 全年 = 所有月份合并视图，key 用 YEAR
share["year_key"] = "YEAR"
share["year_label"] = "全部"

# 按年份分组（供两级按钮用）
_years = sorted(set(k[:4] for k in _month_keys))
share["years"] = []
for _y in _years:
    _ms_in = [m for m in _month_keys if m[:4] == _y]
    _days_in = len([1 for k in _dake_all if k[:4] == _y])
    share["years"].append({
        "key": _y, "label": _y + "年",
        "months": [{"key": m, "label": _ym_label(m)} for m in _ms_in],
        "days": _days_in,
        "amount": round(sum(_ym_d[m] for m in _ms_in), 2),
    })

share["daily_span"] = {"first": min(_dake_all), "last": max(_dake_all),
                       "days": len(_dake_all),
                       "from_table": len([1 for k in _dake_all if not _src_ms.get(k)]),
                       "from_ms": len([1 for k in _dake_all if _src_ms.get(k)]),
                       "from_24": len([1 for k in _dake_all if _src_tab.get(k) == "h24"]),
                       "overlap": _ms_overlap}


# ---------- 把「日期收入24年」(2023-11 ~ 2024-12) 前置进月度走势 ----------
# 用户 2026-09-12：月度走势也要从 2023 年 11 月开始。
# 该表列结构与主表不同 → 转换成本表同构格式：
#   微博 = dake（该表没有杰尼/微任务，也没有广告收入列）
#   其他 = 整月总收入(税后) - 微博   ← ⚠️ 不是源表某一列，必须差额算出
# ⚠️ 血泪坑（用户质询 24年9月实收只有 38813.98）：源表第 9/10 列存的是
#    【整月总收入（税后）】，写在月初那一行，是月度汇总值，**不是"其他收入"**。
#    以前把它当"其他收入"叠加，导致微博被重复计算（24年9月 24440.98+38813.98=63255 虚高）。
#    正确做法：整月总收入直接取源表值，微博作为其中一项，其他 = 总收入 - 微博。
# ⚠️ 防重复：只补主表「没有的月份」，已有的一律以主表为准。
_hist = []
_m_have = set()
for _mm in d["months"]:
    _s = _mm["month"]                      # '25年1月'
    _p = _s.replace("年", "-").replace("月", "")
    _yy, _mi = _p.split("-")
    _m_have.add("%s-%02d" % ("20" + _yy, int(_mi)))

for _m in d.get("months24", []):
    if _m["key"] in _m_have:               # 主表已有 → 跳过，避免重复
        continue
    _y, _mo = _m["key"].split("-")
    _lbl = "%s年%d月" % (_y[2:], int(_mo))
    _wb = round(_m["dake"], 2)
    _gross = round(_m.get("total", 0.0), 2)      # 整月总收入（税后）—— 权威值
    if not _gross:
        _gross = _wb
    _ot = round(max(_gross - _wb, 0.0), 2)       # 其他收入 = 总收入 - 微博
    _hist.append({
        "month": _lbl,
        "ym": _m["key"],                   # 2023-11，用于正确排序
        "weibo_dake": _wb, "weibo_jn": 0.0, "weibo_weiren": 0.0,
        "weibo_total": _wb, "weibo_days": _m["days"],
        "ad_dake": 0.0, "ad_jn": 0.0, "other": _ot,
        "total": _gross,                   # ★ 以源表整月总收入为准，不叠加
        "ad_items": [], "other_items": [],
        "calc_total": _gross,
        "historical": True,                # 标记为历史表来源（前端可标注）
    })

_hist.sort(key=lambda x: x["ym"])          # 按 YYYY-MM 排，别按中文标签
if _hist:
    d["months"] = _hist + d["months"]
    d["months_hist_count"] = len(_hist)
    print("[hist] 前置 %d 个历史月份：%s ~ %s"
          % (len(_hist), _hist[0]["month"], _hist[-1]["month"]))


# 这两份 MediaShareList 就是月度表里的「微博收入」（达克鸭唐 + 杰尼龟说 都算用户的）。
# 月度走势按原样【标黑】统计：微博 = 广告分成(达克) + 广告分成(杰尼) + 微任务 + 共享收益补充。
#
# 关键：MediaShareList 覆盖 26年7月(27日起)、8月、9月；月度表 8/9 月微博分成还是 0，
# 需要补进来。26年7月重叠（月度表是整月数、已含 27-31 日）→ 该月只补「月度表没有的部分」，
# 但用户明确月度表 7 月是整月汇总，故 7 月不补，只补 8/9 月。
from collections import defaultdict
_ms_by_month = defaultdict(float)
for _src, _apply in ((DAKE, True), (JENI, False)):
    for _k, _v in _src.items():
        _ym = _k[:7]                       # 2026-08
        _v = round(_v, 2)
        # 达克在扣减区间的收益不计入（平台删除）
        if _apply and CUT_START <= _k <= CUT_END:
            continue
        _ms_by_month[_ym] += _v

def _ym_to_label(ym):
    y, mo = ym.split("-")
    mo = int(mo)
    return ("25年%d月" % (mo - 12)) if y == "2025" else ("26年%d月" % mo)

# 哪些月份需要从 MediaShareList 补充（月度表微博分成为 0、但明细有数据的月份）
_missing = {}
_m = {x["month"]: x for x in d["months"]}
for _ym, _v in _ms_by_month.items():
    _lbl = _ym_to_label(_ym)
    if _lbl not in _m:
        continue
    _tab = _m[_lbl]["weibo_dake"] + _m[_lbl]["weibo_jn"]
    if _tab <= 0 and _v > 0:
        _missing[_lbl] = round(_v, 2)

share["monthly_supplement"] = _missing
share["supplement_total"] = round(sum(_missing.values()), 2)

# 把补充额并入月度表的微博分成，让月度走势正确显示
for _lbl, _v in _missing.items():
    _m[_lbl]["weibo_jn"] = round(_m[_lbl]["weibo_jn"] + _v, 2)
    _m[_lbl]["weibo_total"] = round(_m[_lbl]["weibo_dake"] + _m[_lbl]["weibo_jn"] + _m[_lbl]["weibo_weiren"], 2)
    _m[_lbl]["total"] = round(_m[_lbl]["weibo_total"] + _m[_lbl]["ad_dake"] + _m[_lbl]["ad_jn"] + _m[_lbl]["other"], 2)
    _m[_lbl]["supplemented"] = _v
# ---------- 「微博收入」合并视图 ----------
# 月度表里的「微博收入」= 广告分成(达克) + 广告分成(杰尼) + 微任务，余额来自 MediaShareList。
# 达克鸭唐与杰尼龟说都是用户的账号，两份表合并统计。
md = [m for m in d["months"] if m["weibo_dake"] or m["weibo_jn"] or m["weibo_weiren"]]
share["monthly_ledger"] = {
    "dake": round(sum(m["weibo_dake"] for m in md), 2),
    "jeni": round(sum(m["weibo_jn"] for m in md), 2),
    "months": len(md),
    "first": md[0]["month"] if md else "", "last": md[-1]["month"] if md else "",
    "rows": [{"month": m["month"], "dake": round(m["weibo_dake"], 2), "jeni": round(m["weibo_jn"], 2)} for m in md],
}
d["share"] = share

DATA_JS = json.dumps(d, ensure_ascii=False, separators=(",", ":"))

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>收入看板 · 达克鸭唐</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Bebas+Neue&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Noto+Serif+SC:wght@500;700;900&display=swap" rel="stylesheet">
<style>
/* ============ 设计令牌 ============ */
:root{
  --bg:#f4f1ea; --surface:#fffdf8; --surface-2:#faf7f0;
  --ink:#171512; --ink-2:#3d3830; --muted:#7d7468;
  --line:rgba(23,21,18,.13); --line-strong:rgba(23,21,18,.28);
  --accent:#c8341f;        /* 朱红 —— 唯一强调色 */
  --accent-ink:#8f2314;
  --amber:#a86412;
  --good:#2f6b46;
  --radius:3px; --radius-lg:6px;
  --sp1:4px; --sp2:8px; --sp3:16px; --sp4:24px; --sp5:40px; --sp6:64px;
  --sh1:0 1px 2px rgba(23,21,18,.05);
  --sh2:0 6px 20px rgba(23,21,18,.07);
  --sh3:0 20px 48px rgba(23,21,18,.10);
  --ease:cubic-bezier(.16,1,.3,1);
  --dur:320ms; --fast:160ms;
  --font-display:"Archivo Black","Noto Serif SC",serif;
  --font-num:"Bebas Neue","IBM Plex Mono",monospace;
  --font-body:"IBM Plex Sans","Noto Serif SC",-apple-system,"Microsoft YaHei",sans-serif;
  --font-mono:"IBM Plex Mono",ui-monospace,monospace;
}
[data-theme="dark"]{
  --bg:#141210; --surface:#1c1916; --surface-2:#221e1a;
  --ink:#f2ede4; --ink-2:#cfc7bb; --muted:#948b7e;
  --line:rgba(242,237,228,.14); --line-strong:rgba(242,237,228,.30);
  --accent:#ff5633; --accent-ink:#ff8a70;
  --amber:#e0a752; --good:#6ec08d;
  --sh1:0 1px 2px rgba(0,0,0,.4); --sh2:0 6px 20px rgba(0,0,0,.45); --sh3:0 20px 48px rgba(0,0,0,.55);
}
*{box-sizing:border-box;margin:0;padding:0}
html{scroll-behavior:smooth}
body{
  background:var(--bg); color:var(--ink); font-family:var(--font-body);
  font-size:15px; line-height:1.7; letter-spacing:.01em;
  -webkit-font-smoothing:antialiased;
}
/* 氛围层：渐变网格 + 颗粒 */
body::before{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:0;
  background:
    radial-gradient(52rem 34rem at 8% -8%, rgba(200,52,31,.13), transparent 62%),
    radial-gradient(46rem 32rem at 102% 4%, rgba(168,100,18,.10), transparent 58%);
}
body::after{
  content:""; position:fixed; inset:0; pointer-events:none; z-index:1; opacity:.035;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.wrap{position:relative; z-index:2; max-width:1360px; margin:0 auto; padding:var(--sp4) var(--sp4) var(--sp6)}
a{color:inherit}
button{font-family:inherit;cursor:pointer}

/* ============ 页头 ============ */
header.masthead{
  display:grid; grid-template-columns:1fr auto; gap:var(--sp4);
  align-items:end; padding:var(--sp5) 0 var(--sp3);
  border-bottom:2px solid var(--ink);
}
.kicker{
  font-family:var(--font-mono); font-size:11px; letter-spacing:.22em;
  text-transform:uppercase; color:var(--muted); margin-bottom:var(--sp3);
  display:flex; align-items:center; gap:var(--sp2);
}
.kicker b{color:var(--accent); font-weight:600}
h1{
  font-family:var(--font-display); font-weight:400;
  font-size:clamp(38px,6.4vw,74px); line-height:1.0; letter-spacing:-.03em;
  text-transform:uppercase;
}
h1 .zh{font-family:"Noto Serif SC",serif; font-weight:900; letter-spacing:-.02em; text-transform:none}
.masthead-r{text-align:right; font-family:var(--font-mono); font-size:12px; color:var(--muted); line-height:1.9}
.masthead-r strong{color:var(--ink); font-size:22px; font-family:var(--font-num); letter-spacing:.02em; display:block}
.toggle{
  display:inline-flex; align-items:center; gap:6px; margin-top:var(--sp2);
  background:var(--surface); border:1px solid var(--line-strong); color:var(--ink);
  padding:7px 13px; font-size:11px; letter-spacing:.1em; text-transform:uppercase;
  font-family:var(--font-mono); border-radius:var(--radius); transition:background var(--fast) var(--ease), color var(--fast);
}
.toggle:hover{background:var(--ink); color:var(--surface)}

/* ============ 分区标题 ============ */
.sec{margin-top:var(--sp6)}
.sec-h{display:flex; align-items:baseline; gap:var(--sp3); border-bottom:1px solid var(--line-strong); padding-bottom:var(--sp2); margin-bottom:var(--sp4)}
.sec-h h2{font-family:var(--font-display); font-size:clamp(19px,2.4vw,27px); font-weight:400; letter-spacing:-.01em; text-transform:uppercase}
.sec-h .n{font-family:var(--font-mono); font-size:12px; color:var(--accent); letter-spacing:.16em}
.sec-h .note{margin-left:auto; font-family:var(--font-mono); font-size:11px; color:var(--muted)}

/* ============ KPI 条 ============ */
.kpis{display:grid; grid-template-columns:repeat(6,1fr); gap:0; border:1px solid var(--line-strong); background:var(--surface); box-shadow:var(--sh2)}
.kpi{padding:var(--sp4) var(--sp3); border-right:1px solid var(--line); position:relative; overflow:hidden}
.kpi:last-child{border-right:0}
.kpi .lbl{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.16em; text-transform:uppercase; color:var(--muted); margin-bottom:var(--sp2)}
.kpi .val{font-family:var(--font-num); font-size:clamp(30px,3.6vw,46px); line-height:1.05; letter-spacing:.01em; font-variant-numeric:tabular-nums}
.kpi .val small{font-family:var(--font-body); font-size:14px; font-weight:600; color:var(--muted); margin-left:3px; letter-spacing:0}
.kpi .sub{font-family:var(--font-mono); font-size:11.5px; color:var(--muted); margin-top:6px}
.kpi.hot .val{color:var(--accent)}
.kpi.hot::after{content:""; position:absolute; left:0; top:0; width:3px; height:100%; background:var(--accent)}

/* ============ 图表 ============ */
.grid-2{display:grid; grid-template-columns:1.55fr 1fr; gap:var(--sp4)}
.panel{background:var(--surface); border:1px solid var(--line-strong); box-shadow:var(--sh1); padding:var(--sp4)}
.panel-h{display:flex; align-items:baseline; justify-content:space-between; gap:var(--sp3); margin-bottom:var(--sp4)}
.panel-h h3{font-family:var(--font-body); font-weight:700; font-size:14px; letter-spacing:.02em}
.panel-h span{font-family:var(--font-mono); font-size:11px; color:var(--muted)}
.legend{display:flex; gap:var(--sp3); flex-wrap:wrap; font-family:var(--font-mono); font-size:11px; color:var(--muted)}
.legend i{display:inline-block; width:9px; height:9px; margin-right:5px; vertical-align:middle}
svg .bar{transition:opacity var(--fast) var(--ease)}
svg .bar:hover{opacity:.72}
.axis{font-family:var(--font-mono); font-size:10px; fill:var(--muted)}
.axis-t{font-family:var(--font-mono); font-size:10.5px; fill:var(--ink-2)}
.axis-t.hist{fill:var(--muted)}
.gridline{stroke:var(--line); stroke-width:1}
.yrline{stroke:var(--line-strong); stroke-width:1; stroke-dasharray:3 3; opacity:.8}

/* ============ 共享收益 ============ */
.share-sum{display:grid; grid-template-columns:repeat(3,1fr); gap:0; border:1px solid var(--line-strong); background:var(--surface); box-shadow:var(--sh1); margin-bottom:var(--sp4)}
.share-sum > div{padding:var(--sp3) var(--sp3); border-right:1px solid var(--line)}
.share-sum > div:last-child{border-right:0}
.share-sum .lbl{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-bottom:5px}
.share-sum .v{font-family:var(--font-num); font-size:clamp(22px,2.6vw,32px); line-height:1.1; font-variant-numeric:tabular-nums}
.share-sum .d{font-family:var(--font-mono); font-size:11px; color:var(--muted); margin-top:3px}
.share-sum .cut .v{color:var(--accent)}
.share-sum .cut{background:rgba(200,52,31,.055)}
.share-sum .net .v{color:var(--good)}
.day-grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(58px,1fr)); gap:5px}
/* 全年视图：558 天，格子收紧密排 */
.day-grid.dense{grid-template-columns:repeat(auto-fill,minmax(40px,1fr)); gap:3px}
.day-grid.dense .day{padding:4px 2px}
.day-grid.dense .day .dd{font-size:9px}
.day-grid.dense .day .vv{font-size:10px; margin-top:1px}
/* 全年视图的月份分块 */
.mblock{margin-bottom:var(--sp3)}
.mblock:last-child{margin-bottom:0}
.mblock .mh{display:flex; justify-content:space-between; align-items:baseline; gap:var(--sp2);
  font-family:var(--font-mono); font-size:11px; letter-spacing:.06em; color:var(--ink-2);
  border-bottom:1px solid var(--line); padding-bottom:3px; margin-bottom:5px}
.mblock .mh .ms{color:var(--muted); font-size:10px}
/* 某时间段无数据的面板（如 2023/2024 的杰尼龟说） */
.grid-2.single{grid-template-columns:1fr}
.panel.dim{opacity:.55}
.panel.dim .day-grid{display:none}
.empty{font-family:var(--font-mono); font-size:12.5px; color:var(--muted); text-align:center;
  padding:var(--sp4) var(--sp3); line-height:1.8}
.day{border:1px solid var(--line); background:var(--surface-2); padding:5px 4px; text-align:center; position:relative; transition:transform var(--fast) var(--ease), border-color var(--fast)}
.day:hover{transform:translateY(-2px); border-color:var(--line-strong)}
.day .dd{font-family:var(--font-mono); font-size:10px; color:var(--muted); line-height:1.2}
.day .vv{font-family:var(--font-mono); font-size:11.5px; font-weight:600; font-variant-numeric:tabular-nums; margin-top:2px}
.day.iscut{background:rgba(200,52,31,.09); border-color:rgba(200,52,31,.42); border-style:dashed}
.day.iscut .vv{color:var(--accent); text-decoration:line-through; text-decoration-thickness:1px; opacity:.8}
.day.iscut .dd{color:var(--accent)}
.day.mute .vv{color:var(--muted)}
.alert{margin-top:var(--sp3); border-left:3px solid var(--accent); background:rgba(200,52,31,.07); padding:var(--sp3); font-size:13px; line-height:1.8}
.alert b{color:var(--accent)}
.key{display:inline-flex; gap:var(--sp3); flex-wrap:wrap; font-family:var(--font-mono); font-size:11px; color:var(--muted); margin-bottom:var(--sp3)}
.key i{display:inline-block; width:11px; height:11px; border:1px solid var(--line-strong); margin-right:5px; vertical-align:-1px}
.key i.cut{background:rgba(200,52,31,.18); border-color:rgba(200,52,31,.5); border-style:dashed}
.tip{border:1px solid var(--line-strong); border-left:3px solid var(--amber); background:var(--surface); padding:var(--sp3); font-size:13px; line-height:1.85; color:var(--ink-2); margin-bottom:var(--sp4)}
.tip b{color:var(--ink)}
.mtabs{display:flex; flex-direction:column; gap:var(--sp2); align-items:flex-start; margin-bottom:var(--sp3);
  border-bottom:1px solid var(--line); padding-bottom:var(--sp3)}
.yr-bar,.mtab-list{display:flex; gap:var(--sp2); flex-wrap:wrap; align-items:center}
.ytab{background:var(--surface); border:1px solid var(--line-strong); color:var(--ink-2);
  padding:7px 15px; font-size:13px; font-family:var(--font-num); letter-spacing:.03em;
  border-radius:var(--radius); transition:all var(--fast) var(--ease); min-height:36px;
  font-variant-numeric:tabular-nums; white-space:nowrap; cursor:pointer}
.ytab:hover{border-color:var(--ink); color:var(--ink)}
.ytab[aria-pressed="true"]{background:var(--ink); border-color:var(--ink); color:var(--surface)}
.ytab.all{border-left:3px double var(--line-strong)}
.mtabs .grp{font-family:var(--font-mono); font-size:10.5px; letter-spacing:.14em; text-transform:uppercase; color:var(--muted); margin-right:var(--sp1); flex:0 0 auto; min-width:34px}
.mtabs .hint{font-size:11.5px; color:var(--muted); font-family:var(--font-mono)}
.mtab{background:var(--surface); border:1px solid var(--line-strong); color:var(--ink-2);
  padding:6px 13px; font-size:12.5px; font-family:var(--font-mono); letter-spacing:.02em;
  border-radius:var(--radius); transition:all var(--fast) var(--ease); min-height:34px;
  font-variant-numeric:tabular-nums; white-space:nowrap; cursor:pointer}
.mtab[aria-pressed="true"]{background:var(--ink); border-color:var(--ink); color:var(--surface)}
.mtab .cnt{opacity:.6; font-size:10.5px; margin-left:4px}
.mtab[aria-pressed="true"] .cnt{opacity:.75}
.mtab.year{border-left:3px double var(--line-strong)}
.note-box{font-size:13px; line-height:1.9; color:var(--ink-2)}
.note-box p{margin-bottom:var(--sp2)}
.note-box ul{list-style:none; margin:var(--sp2) 0 var(--sp3)}
.note-box li{padding-left:14px; position:relative; margin-bottom:5px}
.note-box li::before{content:"·"; position:absolute; left:2px; color:var(--accent); font-weight:700}
.note-box b{color:var(--ink)}
.note-box .warn-txt{background:rgba(200,52,31,.07); border-left:2px solid var(--accent); padding:var(--sp2) var(--sp3); font-size:12.5px}

/* ============ 渠道条 ============ */
.chan-list{display:flex; flex-direction:column; gap:var(--sp3)}
.chan{display:grid; grid-template-columns:1fr auto; gap:var(--sp2) var(--sp3); align-items:center}
.chan .nm{font-size:13.5px; font-weight:600; display:flex; align-items:center; gap:7px}
.chan .nm em{font-style:normal; font-family:var(--font-mono); font-size:10px; color:var(--muted); border:1px solid var(--line); padding:1px 5px; border-radius:2px}
.chan .am{font-family:var(--font-mono); font-size:13px; font-variant-numeric:tabular-nums}
.chan .track{grid-column:1/-1; height:7px; background:var(--surface-2); border:1px solid var(--line); position:relative; overflow:hidden}
.chan .fill{height:100%; background:var(--accent); transform-origin:left; animation:grow 900ms var(--ease) both}
.chan .meta{grid-column:1/-1; font-family:var(--font-mono); font-size:10.5px; color:var(--muted)}
.chan .meta .warn{color:var(--accent); font-weight:600}
@keyframes grow{from{transform:scaleX(0)}to{transform:scaleX(1)}}

/* ============ 表格 ============ */
.tbl-wrap{overflow-x:auto; border:1px solid var(--line-strong); background:var(--surface)}
table{width:100%; border-collapse:collapse; font-size:13.5px; min-width:640px}
thead th{
  text-align:left; font-family:var(--font-mono); font-size:10.5px; letter-spacing:.13em;
  text-transform:uppercase; color:var(--muted); font-weight:500;
  padding:11px var(--sp3); border-bottom:1px solid var(--line-strong); background:var(--surface-2); white-space:nowrap;
}
tbody td{padding:10px var(--sp3); border-bottom:1px solid var(--line); vertical-align:middle}
tbody tr{transition:background var(--fast) var(--ease)}
tbody tr:hover{background:var(--surface-2)}
.num{font-family:var(--font-mono); font-variant-numeric:tabular-nums; text-align:right; white-space:nowrap}
.tag{display:inline-block; font-family:var(--font-mono); font-size:10.5px; letter-spacing:.06em; padding:2px 7px; border-radius:2px; border:1px solid currentColor; white-space:nowrap}
.tag.unpaid{color:var(--accent)}
.tag.paid{color:var(--good)}
.tag.warn{color:var(--accent); background:rgba(200,52,31,.08); border-color:transparent; font-weight:600}
.age{font-family:var(--font-mono); font-variant-numeric:tabular-nums; font-size:12px}
.age.old{color:var(--accent); font-weight:600}
.age.mid{color:var(--amber)}
.filters{display:flex; gap:var(--sp2); flex-wrap:wrap; margin-bottom:var(--sp3)}
.fbtn{
  background:var(--surface); border:1px solid var(--line-strong); color:var(--ink-2);
  padding:7px 14px; font-size:12px; letter-spacing:.04em; border-radius:var(--radius);
  transition:all var(--fast) var(--ease); min-height:36px;
}
.fbtn:hover{border-color:var(--ink); color:var(--ink)}
.fbtn[aria-pressed="true"]{background:var(--ink); border-color:var(--ink); color:var(--surface)}
.empty{padding:var(--sp5) var(--sp3); text-align:center; color:var(--muted); font-family:var(--font-mono); font-size:12px}

/* ============ 底部说明 ============ */
.foot{margin-top:var(--sp6); border-top:1px solid var(--line-strong); padding-top:var(--sp4); display:grid; grid-template-columns:1.4fr 1fr; gap:var(--sp5)}
.foot h4{font-family:var(--font-mono); font-size:11px; letter-spacing:.16em; text-transform:uppercase; color:var(--accent); margin-bottom:var(--sp2)}
.foot p,.foot li{font-size:13px; color:var(--ink-2); line-height:1.85}
.foot ul{list-style:none; display:flex; flex-direction:column; gap:5px}
.foot li::before{content:"→ "; color:var(--accent); font-family:var(--font-mono)}
code{font-family:var(--font-mono); font-size:12px; background:var(--surface-2); border:1px solid var(--line); padding:1px 5px; border-radius:2px}

/* ============ 入场编排 ============ */
.rv{opacity:0; transform:translateY(18px)}
.rv.in{opacity:1; transform:none; transition:opacity var(--dur) var(--ease), transform var(--dur) var(--ease)}
.rv:nth-child(2).in{transition-delay:70ms}
.rv:nth-child(3).in{transition-delay:140ms}
.rv:nth-child(4).in{transition-delay:210ms}
:focus-visible{outline:2px solid var(--accent); outline-offset:2px}

@media (max-width:1080px){
  .kpis{grid-template-columns:repeat(3,1fr)}
  .kpi:nth-child(3n){border-right:0}
  .kpi:nth-child(n+4){border-top:1px solid var(--line)}
  .grid-2{grid-template-columns:1fr}
  .share-sum{grid-template-columns:1fr}
  .share-sum > div{border-right:0; border-bottom:1px solid var(--line)}
  .share-sum > div:last-child{border-bottom:0}
  .foot{grid-template-columns:1fr; gap:var(--sp4)}
}
@media (max-width:640px){
  .wrap{padding:var(--sp3) var(--sp3) var(--sp6)}
  header.masthead{grid-template-columns:1fr; align-items:start; gap:var(--sp3)}
  .masthead-r{text-align:left}
  .kpis{grid-template-columns:repeat(2,1fr)}
  .kpi{border-right:1px solid var(--line)}
  .kpi:nth-child(2n){border-right:0}
  .sec{margin-top:var(--sp5)}
  .panel{padding:var(--sp3)}
  .day-grid{grid-template-columns:repeat(auto-fill,minmax(52px,1fr))}
}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important; transition:none!important}
  .rv{opacity:1; transform:none}
}
</style>
</head>
<body>
<div class="wrap">

  <header class="masthead">
    <div>
      <div class="kicker">收入看板 <b>／</b> 达克鸭唐 <b>／</b> 数据截至 <span id="stamp"></span></div>
      <h1>REVENUE<span class="zh">　账本</span></h1>
    </div>
    <div class="masthead-r">
      累计已录收入
      <strong id="grandTotal">—</strong>
      <div id="periodLine">—</div>
      <button class="toggle" id="themeBtn" aria-label="切换深色模式">◐ 深色</button>
    </div>
  </header>

  <!-- KPI -->
  <section class="sec">
    <div class="kpis" id="kpis"></div>
  </section>

  <!-- 图表 -->
  <section class="sec">
    <div class="sec-h"><span class="n">01</span><h2>月度走势</h2><span class="note" id="chartNote"></span></div>
    <div class="grid-2">
      <div class="panel rv">
        <div class="panel-h">
          <h3>每月收入构成</h3>
          <div class="legend">
            <span><i style="background:var(--ink)"></i>微博</span>
            <span><i style="background:var(--ink);opacity:.35;border:1px solid var(--ink)"></i>微博·明细补录</span>
            <span><i style="background:var(--accent)"></i>广告</span>
            <span><i style="background:var(--amber)"></i>其他</span>
            <span><i style="background:var(--amber);opacity:.75;width:3px"></i>历史月份（24年表）</span>
          </div>
        </div>
        <div id="chartMonthly"></div>
      </div>
      <div class="panel rv">
        <div class="panel-h"><h3>待收 · 按渠道</h3><span id="chanTotal"></span></div>
        <div class="chan-list" id="chanList"></div>
      </div>
    </div>
  </section>

  <!-- 微博共享收益 -->
  <section class="sec">
    <div class="sec-h"><span class="n">02</span><h2>微博收入 · 共享收益</h2><span class="note" id="shareNote"></span></div>

    <div class="tip" id="shareTip"></div>

    <div class="share-sum" id="shareSum"></div>

    <div class="mtabs" id="mTabs" role="group" aria-label="选择查看范围">
      <span class="grp">查看</span>
    </div>

    <div class="grid-2" id="grid2">
      <div class="panel rv">
        <div class="panel-h">
          <h3 id="dakeTitle">达克鸭唐 · 每日收益</h3>
          <span id="dakeTot"></span>
        </div>
        <div class="key">
          <span><i></i>正常结算</span>
          <span><i class="cut"></i>平台扣减（不给到）</span>
        </div>
        <div class="day-grid" id="dakeGrid"></div>
      </div>
      <div class="panel rv" id="jeniPanel">
        <div class="panel-h">
          <h3 id="jeniTitle">杰尼龟说 · 每日收益</h3>
          <span id="jeniTot"></span>
        </div>
        <div class="key">
          <span><i></i>全部正常结算（无扣减）</span>
        </div>
        <div class="day-grid" id="jeniGrid"></div>
        <div class="empty" id="jeniEmpty" style="display:none">该时期「杰尼龟说」账号还没有微博收入记录<br>
          <span style="font-size:11.5px">（2025 年 1 月起才有分成）</span></div>
      </div>
    </div>

    <div class="alert" id="shareAlert"></div>

    <div class="sec-h" style="margin-top:var(--sp5)"><span class="n">02b</span><h2>微博收入 · 月度构成</h2><span class="note" id="mdNote"></span></div>
    <div class="grid-2">
      <div class="panel rv">
        <div class="panel-h"><h3>各月微博分成（双账号）</h3><span>单位：元</span></div>
        <div id="chartShareMonthly"></div>
      </div>
      <div class="panel rv">
        <div class="panel-h"><h3>口径说明</h3><span>重要</span></div>
        <div class="note-box">
          <p><b>你给的两份 MediaShareList 表，就是月度表里的「微博收入」</b>，
             <b>达克鸭唐和杰尼龟说都是你的账号</b>，所以两份合并统计。</p>
          <ul>
            <li><b>月度走势</b>（上）—— 覆盖 <code>23年11月 – 26年12月</code>，
              前三段来自 <b>「日期收入24年」</b>（23/11–24/12，只有达克）、<b>「25年收入」月度表</b>（25/1 起）</li>
            <li><b>每日明细</b>（中）—— 覆盖 <code>2023-11-01 – 2026-09-11</code>，
              尾部 <code>7/27–9/11</code> 来自 MediaShareList</li>
          </ul>
          <p class="warn-txt">⚠️ 26年8月、9月的月度表<b>微博分成还是 0</b>（尚未录），
            已按明细把 <span id="suppTot"></span> 补进月度走势，在图上以<b>浅色斜纹</b>标出。</p>
          <p class="warn-txt">⚠️ 「日期收入24年」里名为 <code>24年1–7月</code> 的 sheet，
            单元格日期被写成了 <code>2023/x/x</code>，实际是 <b>2024 年</b>
            （只有 <code>11月</code>、<code>12月</code> 两张确实是 2023 年），已按 sheet 名纠正。</p>
          <p style="margin-top:var(--sp3)"><b>账号归属</b>：两份表内<b>均无账号字段</b>，按来源绑定 ——
            <b>第一份 = 达克鸭唐</b>（8/24–9/6 有平台扣减）、<b>第二份 = 杰尼龟说</b>（无扣减）。
            「日期收入24年」的微博收入<b>全部算达克鸭唐</b>。</p>
        </div>
      </div>
    </div>
  </section>

  <!-- 待收明细 -->
  <section class="sec">
    <div class="sec-h"><span class="n">03</span><h2>待收明细</h2><span class="note" id="unpaidNote"></span></div>
    <div class="filters" role="group" aria-label="筛选">
      <button class="fbtn" data-filter="unpaid" aria-pressed="true">未收</button>
      <button class="fbtn" data-filter="overdue" aria-pressed="false">超 30 天</button>
      <button class="fbtn" data-filter="paid" aria-pressed="false">已收</button>
      <button class="fbtn" data-filter="all" aria-pressed="false">全部</button>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>收入日期</th><th>项目</th><th>渠道</th>
          <th style="text-align:right">金额</th><th style="text-align:right">账龄</th>
          <th>原表月份</th><th>收款日</th><th>状态</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
  </section>

  <!-- 说明 -->
  <footer class="foot">
    <div>
      <h4>怎么看这块板</h4>
      <ul>
        <li>数据来自腾讯文档 <b>25年收入</b>（24 张月度表）与 <b>代收款跟踪表</b>，自动解析合并</li>
        <li>「累计已录收入」＝各月总收入合计，含微博分成、微任务、广告、其他四项</li>
        <li>「待收」＝代收款跟踪表中状态为未收的笔数与金额，账龄按收入日期算到今天</li>
        <li>「微博收入」＝广告分成（达克鸭唐 + 杰尼龟说，均为你的账号）＋ 微任务</li>
        <li>共享收益来自 MediaShareList 导出表，两份表<span style="color:var(--accent)">合并统计</span>；其中 <b>8/24–9/6 标红划线</b> 是达克鸭唐被平台禁言删除、<b>不会结算</b>的部分</li>
        <li>月度走势里 <b>浅色斜纹</b> 的微博柱＝月度表尚未录入、由明细补录的部分</li>
      </ul>
    </div>
    <div>
      <h4>有新收入怎么办</h4>
      <ul>
        <li>照常在腾讯文档月度表里加一行，或更新跟踪表状态</li>
        <li>然后叫我一声「刷新收入看板」，我重新抓取并更新这块板</li>
        <li>也可以直接告诉我：<code>8月10日 小米 +3500 已收</code></li>
      </ul>
    </div>
  </footer>
</div>

<script>
var DATA = __DATA__;

/* ---------- 工具 ---------- */
function fmt(n){ return Math.round(n).toLocaleString('en-US'); }
function fmt2(n){ return n.toLocaleString('en-US',{minimumFractionDigits:0,maximumFractionDigits:0}); }
function yuan(n){ return '¥' + fmt(n); }
function esc(s){ var d=document.createElement('div'); d.textContent = s==null?'':s; return d.innerHTML; }

var M = DATA.months;
var M24 = DATA.months24 || [];
var T = DATA.tracking;

/* ---------- 页头 ---------- */
// 月度走势已含 2023-11 起的全部历史月 → grand 即全量，别再叠加 months24
var grand = M.reduce(function(a,m){ return a + m.total; }, 0);
var histM = M.filter(function(m){ return m.historical; });
var histSum = histM.reduce(function(a,m){ return a + m.total; }, 0);
var h24Weibo = histM.reduce(function(a,m){ return a + m.weibo_total; }, 0);
document.getElementById('grandTotal').textContent = yuan(grand);
document.getElementById('stamp').textContent = DATA.generated_at;
var _firstAll = M[0].month;
var _activeAll = M.filter(function(m){ return m.total > 0; });
document.getElementById('periodLine').textContent =
  _firstAll + ' – ' + (_activeAll.length ? _activeAll[_activeAll.length-1].month : _firstAll)
  + ' · ' + _activeAll.length + ' 个月有进账';
var active = M.filter(function(m){ return m.total > 0; });
document.getElementById('periodLine').textContent =
  M[0].month + ' – ' + (active.length?active[active.length-1].month:M[0].month) + ' · ' + active.length + ' 个月有进账';

/* ---------- KPI ---------- */
(function(){
  var ms25 = M.filter(function(m){ return m.month.indexOf('25年')===0; });
  var ms26 = M.filter(function(m){ return m.month.indexOf('26年')===0; });
  var s25 = ms25.reduce(function(a,m){return a+m.total},0);
  var s26 = ms26.reduce(function(a,m){return a+m.total},0);
  var weibo = M.reduce(function(a,m){return a+m.weibo_total},0);
  var ad = M.reduce(function(a,m){return a+(m.ad_dake+m.ad_jn)},0);
  var best = null;
  M.forEach(function(m){ if(m.total>0 && (!best||m.total>best.total)) best=m; });

  var html = [
    {lbl:'累计已录收入', val:yuan(grand),
     sub:'23年11月起 · 含历史 ¥'+fmt(histSum), hot:false},
    {lbl:'待收未回', val:yuan(T.unpaid_total), sub:T.unpaid_count + ' 笔未结 · 最久 ' + Math.max.apply(null,T.unpaid.map(function(r){return r.days})) + ' 天', hot:true},
    {lbl:'25 年合计', val:yuan(s25), sub:'12 个月', hot:false},
    {lbl:'26 年合计', val:yuan(s26), sub:'已录月份' + (best?' · 峰值 '+best.month+' '+yuan(best.total):''), hot:false},
    {lbl:'微博分成 · 历史累计', val:yuan(h24Weibo + DATA.share.dake.gross + DATA.share.jeni.gross),
     sub:'2023-11 起 · 达克 + 杰尼 · ' + DATA.share.daily_span.days + ' 天', hot:false},
    {lbl:'平台扣减（拿不到）', val:yuan(DATA.share.cut), sub:'仅达克鸭唐 · ' + DATA.share.cut_start + ' – ' + DATA.share.cut_end, hot:true}
  ].map(function(k){
    return '<div class="kpi'+(k.hot?' hot':'')+'">'+
      '<div class="lbl">'+k.lbl+'</div>'+
      '<div class="val">'+k.val+'</div>'+
      '<div class="sub">'+k.sub+'</div></div>';
  }).join('');
  document.getElementById('kpis').innerHTML = html;
})();

/* ---------- 月度柱状图 ---------- */
(function(){
  var W = 760, rowH = 24, padL = 92, padR = 62, padT = 6, padB = 22;
  var H = padT + M.length*rowH + padB;
  var maxV = Math.max.apply(null, M.map(function(m){return m.total})) || 1;
  // 取整刻度
  var step = Math.pow(10, Math.floor(Math.log10(maxV/10)));
  var top = Math.ceil(maxV/step)*step;
  var plotW = W - padL - padR;
  var sc = function(v){ return plotW * (v/top); };

  var s = '<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="'+H+'" role="img" aria-label="每月收入构成条形图">';
  // 刻度线
  for(var g=0; g<=top; g+=top/4){
    var x = padL + sc(g);
    s += '<line class="gridline" x1="'+x.toFixed(1)+'" y1="'+padT+'" x2="'+x.toFixed(1)+'" y2="'+(padT+M.length*rowH)+'"/>';
    s += '<text class="axis" x="'+x.toFixed(1)+'" y="'+(H-6)+'" text-anchor="middle">'+(g/1000).toFixed(0)+'k</text>';
  }
  M.forEach(function(m,i){
    var y = padT + i*rowH, h = 13, yo = y + (rowH-h)/2 - 2;
    var w = sc(m.weibo_total), a = sc(m.ad_dake+m.ad_jn), o = sc(m.other);
    var dim = m.total === 0;
    var supp = m.supplemented || 0;
    // 年份分隔线：跨年时画一条淡线 + 年份标签
    var prev = i > 0 ? M[i-1] : null;
    var yOf = function(mm){ return mm.replace('年','-').replace('月','').split('-')[0]; };
    if(i === 0 || (prev && yOf(prev.month) !== yOf(m.month))){
      s += '<line class="yrline" x1="'+(padL-84)+'" y1="'+(y-1).toFixed(1)+'" x2="'+(W-padR+16)+'" y2="'+(y-1).toFixed(1)+'"/>';
    }
    // 历史月份（来自「日期收入24年」）用左侧色条标示
    if(m.historical){
      s += '<rect x="'+(padL-84)+'" y="'+y.toFixed(1)+'" width="2.5" height="'+rowH+'" fill="var(--amber)" opacity=".75"/>';
    }
    s += '<text class="axis-t'+(m.historical?' hist':'')+'" x="'+(padL-9)+'" y="'+(y+rowH/2+4)+'" text-anchor="end">'+m.month+'</text>';
    var x = padL;
    if(w>0){
      var ws = supp ? w - sc(supp) : w;   // 正常部分
      if(ws > 0.5){ s += '<rect class="bar" x="'+x.toFixed(1)+'" y="'+yo+'" width="'+ws.toFixed(1)+'" height="'+h+'" fill="var(--ink)"><title>'+m.month+' 微博 '+yuan(m.weibo_total)+'</title></rect>'; x += ws; }
      if(supp){
        var su = sc(supp);
        s += '<defs><pattern id="hatch'+i+'" width="5" height="5" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">'+
             '<rect width="5" height="5" fill="var(--ink)" opacity=".18"/>'+
             '<line x1="0" y1="0" x2="0" y2="5" stroke="var(--ink)" stroke-width="1.6" opacity=".55"/></pattern></defs>';
        s += '<rect class="bar" x="'+x.toFixed(1)+'" y="'+yo+'" width="'+Math.max(su,1.2).toFixed(1)+'" height="'+h+'" fill="url(#hatch'+i+')" stroke="var(--ink)" stroke-width=".7" stroke-opacity=".5">'+
             '<title>'+m.month+' 微博 '+yuan(m.weibo_total)+'（含明细补录 '+yuan(supp)+'）</title></rect>';
        x += su;
      }
    }
    if(a>0){ s += '<rect class="bar" x="'+x.toFixed(1)+'" y="'+yo+'" width="'+Math.max(a,1.2).toFixed(1)+'" height="'+h+'" fill="var(--accent)"><title>'+m.month+' 广告 '+yuan(m.ad_dake+m.ad_jn)+'</title></rect>'; x += a; }
    if(o>0){ s += '<rect class="bar" x="'+x.toFixed(1)+'" y="'+yo+'" width="'+Math.max(o,1.2).toFixed(1)+'" height="'+h+'" fill="var(--amber)"><title>'+m.month+' 其他 '+yuan(m.other)+'</title></rect>'; }
    if(m.total>0){
      s += '<text class="axis-t" x="'+(padL+sc(m.total)+7).toFixed(1)+'" y="'+(y+rowH/2+4)+'" style="font-size:11.5px">'+fmt(m.total)+'</text>';
    } else {
      s += '<text class="axis" x="'+(padL+4)+'" y="'+(y+rowH/2+4)+'">—</text>';
    }
  });
  s += '</svg>';
  document.getElementById('chartMonthly').innerHTML = s;
  var _h = M.filter(function(m){ return m.historical; });
  document.getElementById('chartNote').textContent =
    '单位：元 · ' + M.length + ' 个月'
    + (_h.length ? '（含 ' + _h.length + ' 个历史月，23年11月–24年12月）' : '');
})();

/* ---------- 微博共享收益 ---------- */
(function(){
  var S = DATA.share;
  if(!S){ return; }
  var cs = S.cut_start, ce = S.cut_end;

  // 汇总卡
  document.getElementById('shareSum').innerHTML = [
    {c:'net', lbl:'微博收入 · 累计（'+S.daily_span.days+'天）', v:S.gross,
     d:S.daily_span.first + ' – ' + S.daily_span.last + ' · 达克 '+yuan(S.dake.gross)+' + 杰尼 '+yuan(S.jeni.gross)},
    {c:'', lbl:'实际到手', v:S.total,
     d:'达克鸭唐 '+yuan(S.dake.total)+' + 杰尼龟说 '+yuan(S.jeni.total)},
    {c:'cut', lbl:'平台扣减 · '+cs.slice(5)+' – '+ce.slice(5), v:S.cut,
     d:'仅达克鸭唐 '+S.cut_days_count+' 天 · 禁言删除，不给到'}
  ].map(function(k){
    return '<div class="'+k.c+'"><div class="lbl">'+k.lbl+'</div><div class="v">'+yuan(k.v)+'</div><div class="d">'+k.d+'</div></div>';
  }).join('');

  function dayCell(x, multi, applies){
    var cut = applies && x.date >= cs && x.date <= ce;
    var zero = x.amount === 0;
    return '<div class="day'+(cut?' iscut':'')+(zero?' mute':'')+'" title="'+x.date+' ¥'+x.amount+'">'+
      '<div class="dd">'+(multi ? x.date.slice(5) : x.date.slice(8))+'</div>'+
      '<div class="vv">'+(zero?'—':x.amount.toFixed(0))+'</div></div>';
  }

  function grid(el, src, ym){
    var all = src.days.concat(src.cut_days).filter(function(x){
      return ym === S.year_key || x.date.slice(0,7) === ym;
    }).sort(function(a,b){ return a.date.localeCompare(b.date); });
    var applies = src.cut_applies;
    if(!all.length){
      el.innerHTML = '<div class="empty" style="grid-column:1/-1">该时间段暂无数据</div>';
      return;
    }
    if(ym === S.year_key){
      // 全年：按月分块，每块带小标题，格子收紧
      var bym = {};
      all.forEach(function(x){
        var k = x.date.slice(0,7);
        (bym[k] = bym[k] || []).push(x);
      });
      var keys = Object.keys(bym).sort(function(a,b){ return b.localeCompare(a); });
      el.className = 'day-grid';
      el.innerHTML = keys.map(function(k){
        var arr = bym[k];
        var sum = arr.reduce(function(a,x){ return a + x.amount; }, 0);
        return '<div class="mblock">'+
          '<div class="mh"><span>'+labelOf(k)+'</span>'+
          '<span class="ms">'+arr.length+'天 · '+yuan(sum)+'</span></div>'+
          '<div class="day-grid dense">'+arr.map(function(x){ return dayCell(x,false,applies); }).join('')+'</div>'+
        '</div>';
      }).join('');
    } else {
      el.className = 'day-grid';
      el.innerHTML = all.map(function(x){ return dayCell(x,false,applies); }).join('');
    }
  }

  function sumIn(src, ym){
    return src.days.concat(src.cut_days).filter(function(x){
      return ym === S.year_key || x.date.slice(0,7) === ym;
    }).reduce(function(a,x){ return a + x.amount; }, 0);
  }
  function cutIn(src, ym){
    if(!src.cut_applies) return 0;
    return src.cut_days.filter(function(x){
      return ym === S.year_key || x.date.slice(0,7) === ym;
    }).reduce(function(a,x){ return a + x.amount; }, 0);
  }

  var cur = S.latest_month;

  function render(){
    grid(document.getElementById('dakeGrid'), S.dake, cur);
    grid(document.getElementById('jeniGrid'), S.jeni, cur);
    var dt = sumIn(S.dake, cur) - cutIn(S.dake, cur), dk = cutIn(S.dake, cur);
    document.getElementById('dakeTot').textContent = '结算 ' + yuan(dt) + (dk ? ' / 扣减 ' + yuan(dk) : '');
    var jt = sumIn(S.jeni, cur);
    document.getElementById('jeniTot').textContent = '结算 ' + yuan(jt) + ' / 无扣减';
    document.getElementById('dakeTitle').textContent = '达克鸭唐 · ' + (cur===S.year_key ? '全部每日收益' : labelOf(cur) + ' 每日收益');
    document.getElementById('jeniTitle').textContent = '杰尼龟说 · ' + (cur===S.year_key ? '全部每日收益' : labelOf(cur) + ' 每日收益');
    // 2023/2024 年杰尼龟说还没开始有收入 → 自动收起该面板，避免满屏 0
    var jeniPanel = document.getElementById('jeniPanel');
    var hasJeni = jt > 0 || sumIn(S.jeni, S.year_key) > 0 && cur !== S.year_key;
    var dimJeni = (jt <= 0);
    if(jeniPanel){
      jeniPanel.classList.toggle('dim', dimJeni);
      document.getElementById('jeniEmpty').style.display = dimJeni ? 'block' : 'none';
    }
    document.getElementById('grid2').classList.toggle('single', dimJeni);
  }
  function labelOf(k){
    if(k === S.year_key) return S.year_label;
    var f = S.months.filter(function(m){ return m.key === k; })[0];
    if(f) return f.label;
    return k + '年';
  }

  // ---- 两级切换：年份 Tab（2023/2024/2025/2026/全部） + 该年的月份按钮 ----
  // 数据跨 33 个月，平铺放不下，所以先选年再看月。
  var tabs = document.getElementById('mTabs');
  var yearBar = document.createElement('div');
  yearBar.className = 'yr-bar';
  var monBar = document.createElement('div');
  monBar.className = 'mtab-list';

  var curYear = S.latest_month.slice(0, 4);

  function yrDays(y){
    var yc = S.years.filter(function(x){ return x.key === y; })[0];
    return yc ? yc.days : 0;
  }

  function buildYearBar(){
    yearBar.innerHTML = '<span class="grp">年份</span>' +
      S.years.slice().sort(function(a,b){ return b.key.localeCompare(a.key); }).map(function(y){
        return '<button class="ytab" data-y="'+y.key+'" aria-pressed="false">'
          + y.label + '<span class="cnt">'+y.days+'天</span></button>';
      }).join('') +
      '<button class="ytab all" data-y="'+S.year_key+'" aria-pressed="false">'
      + S.year_label + '<span class="cnt">'+S.daily_span.days+'天</span></button>';
  }

  function buildMonBar(){
    if(cur === S.year_key){
      monBar.innerHTML = '<span class="grp">月份</span><span class="hint">已展开全部，按月份分块显示</span>';
      return;
    }
    var yc = S.years.filter(function(x){ return x.key === cur.slice(0, 4); })[0];
    var ms = yc ? yc.months.slice().sort(function(a,b){ return b.key.localeCompare(a.key); }) : [];
    monBar.innerHTML = '<span class="grp">月份</span>' + ms.map(function(m){
      return '<button class="mtab" data-m="'+m.key+'" aria-pressed="'+(m.key===cur?'true':'false')+'">'
        + m.label + '</button>';
    }).join('') + '<button class="mtab year" data-m="'+S.year_key+'" aria-pressed="false">该年全部</button>';
  }

  function markYears(){
    yearBar.querySelectorAll('.ytab').forEach(function(b){
      var on = (cur === S.year_key) ? (b.dataset.y === S.year_key) : (b.dataset.y === cur.slice(0,4));
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
  }

  tabs.appendChild(yearBar);
  tabs.appendChild(monBar);
  buildYearBar();
  buildMonBar();

  tabs.addEventListener('click', function(e){
    var yb = e.target.closest('.ytab');
    if(yb){
      var y = yb.dataset.y;
      if(y === S.year_key){ cur = S.year_key; }
      else {
        // 切到某年：默认落在该年最近的一个月
        var yc = S.years.filter(function(x){ return x.key === y; })[0];
        var ms = yc.months.slice().sort(function(a,b){ return b.key.localeCompare(a.key); });
        cur = ms.length ? ms[0].key : S.latest_month;
      }
      buildMonBar(); markYears(); render();
      return;
    }
    var mb = e.target.closest('.mtab');
    if(!mb) return;
    cur = mb.dataset.m;
    buildMonBar(); markYears(); render();
  });

  markYears();
  render();

  document.getElementById('shareNote').textContent =
    '微博收入每日明细 ' + S.daily_span.first + ' – ' + S.daily_span.last
    + ' 共 ' + S.daily_span.days + ' 天 · ' + S.years.length + ' 个年份';
  document.getElementById('shareTip').innerHTML =
    '📌 这里是<b>微博收入的完整每日明细</b>，把沿革所有表格里的数据集中到了一起：'+
    '<b>2023年11月 – 2024年12月</b> 取自<b>「日期收入24年」</b>（'+S.daily_span.from_24+' 天，'+
    '该表微博收入<b>全部算达克鸭唐</b>）；<b>2025年1月 – 2026年7月26日</b> 取自<b>「25年收入」月度表</b>（'+
    S.daily_span.from_table+' 天，达克 + 杰尼两列）；<b>2026年7月27日 – 9月11日</b> 取自你导出的 '+
    '<b>MediaShareList 明细</b>（'+S.daily_span.from_ms+' 天）。三段天然衔接、零重叠，共 <b>'+
    S.daily_span.days+' 天</b>。默认显示最近一个月，上方可按<b>年份 → 月份</b>逐级查看。'+
    '<br><span style="color:var(--accent)">⚠️ 源表笔误已修正</span>：'+
    '「日期收入24年」里名为「24年1–7月」的几个 sheet，单元格日期被写成了 <code>2023/x/x</code>，'+
    '实际是 <b>2024 年</b>（只有「11月」「12月」两张确实是 2023 年），已按 sheet 名纠正。';
  document.getElementById('suppTot').textContent = yuan(S.supplement_total);
  document.getElementById('shareAlert').innerHTML =
    '🚫 <b>达克鸭唐</b> 在 <b>' + cs + ' 至 ' + ce + '</b>（共 '+S.cut_days_count+' 天）的共享收益 <b>' + yuan(S.cut) + '</b> 为<b>平台禁言删除，不会结算</b>，已从收入中剔除。'+
    '<b>杰尼龟说该区间无扣减</b>，全额正常结算。'+
    '源表「扣减原因」列原为空，此标注依据你的说明补记 —— 建议在源表 G 列补注，避免以后忘记。';
})();

/* ---------- 微博收入 · 月度构成 ---------- */
(function(){
  var S = DATA.share;
  var ML = S.monthly_ledger;
  if(!ML || !ML.rows.length){ return; }
  document.getElementById('mdNote').textContent =
    ML.first + ' – ' + ML.last + ' · ' + ML.months + ' 个月 · 合计 ' + yuan(ML.dake + ML.jeni);

  var rows = ML.rows;
  var W = 760, rowH = 19, padL = 74, padR = 70, padT = 4, padB = 20;
  var H = padT + rows.length*rowH + padB;
  var maxV = Math.max.apply(null, rows.map(function(r){ return Math.max(r.dake, r.jeni); })) || 1;
  var step = Math.pow(10, Math.floor(Math.log10(maxV/10)));
  var top = Math.ceil(maxV/step)*step;
  var plotW = W - padL - padR;
  var sc = function(v){ return plotW * (v/top); };
  var bh = 5.6, gap = 1.2;

  var s = '<svg viewBox="0 0 '+W+' '+H+'" width="100%" height="'+H+'" role="img" aria-label="各月广告分成条形图">';
  for(var g=0; g<=top; g+=top/4){
    var x = padL + sc(g);
    s += '<line class="gridline" x1="'+x.toFixed(1)+'" y1="'+padT+'" x2="'+x.toFixed(1)+'" y2="'+(padT+rows.length*rowH)+'"/>';
    s += '<text class="axis" x="'+x.toFixed(1)+'" y="'+(H-5)+'" text-anchor="middle">'+(g/1000).toFixed(0)+'k</text>';
  }
  rows.forEach(function(r,i){
    var y = padT + i*rowH;
    s += '<text class="axis-t" x="'+(padL-8)+'" y="'+(y+rowH/2+3.5)+'" text-anchor="end">'+r.month+'</text>';
    var y1 = y + (rowH/2) - bh - gap/2, y2 = y + (rowH/2) + gap/2;
    if(r.dake>0) s += '<rect class="bar" x="'+padL+'" y="'+y1.toFixed(1)+'" width="'+Math.max(sc(r.dake),1).toFixed(1)+'" height="'+bh+'" fill="var(--ink)"><title>'+r.month+' 达克鸭唐 ¥'+r.dake+'</title></rect>';
    if(r.jeni>0) s += '<rect class="bar" x="'+padL+'" y="'+y2.toFixed(1)+'" width="'+Math.max(sc(r.jeni),1).toFixed(1)+'" height="'+bh+'" fill="var(--accent)"><title>'+r.month+' 杰尼龟说 ¥'+r.jeni+'</title></rect>';
    var mx = Math.max(r.dake, r.jeni);
    s += '<text class="axis-t" x="'+(padL+sc(mx)+6).toFixed(1)+'" y="'+(y+rowH/2+3.5)+'" style="font-size:10.5px">'+fmt(r.dake+r.jeni)+'</text>';
  });
  s += '</svg>';
  document.getElementById('chartShareMonthly').innerHTML = s;
  document.getElementById('chartShareMonthly').insertAdjacentHTML('beforebegin',
    '<div class="legend" style="margin-bottom:var(--sp3)"><span><i style="background:var(--ink)"></i>达克鸭唐</span><span><i style="background:var(--accent)"></i>杰尼龟说</span></div>');
})();

/* ---------- 渠道待收 ---------- */
(function(){
  var cs = T.chan_summary;
  var maxA = Math.max.apply(null, cs.map(function(c){return c.amount})) || 1;
  var html = cs.map(function(c){
    var old = c.max_days >= 90 ? 'old' : (c.max_days >= 30 ? 'mid' : '');
    return '<div class="chan">'+
      '<div class="nm">'+esc(c.channel)+'<em>'+c.count+' 笔</em></div>'+
      '<div class="am">'+yuan(c.amount)+'</div>'+
      '<div class="track"><div class="fill" style="width:'+(c.amount/maxA*100).toFixed(1)+'%"></div></div>'+
      '<div class="meta">最长账龄 <span class="'+old+'">'+c.max_days+' 天</span>'+
        (c.max_days>=90?' · 建议优先催收':'')+'</div>'+
    '</div>';
  }).join('');
  document.getElementById('chanList').innerHTML = html || '<div class="empty">暂无未收款项</div>';
  document.getElementById('chanTotal').textContent = yuan(T.unpaid_total) + ' / ' + T.unpaid_count + ' 笔';
})();

/* ---------- 明细表 ---------- */
(function(){
  var tbody = document.getElementById('tbody');
  var state = 'unpaid';

  function ageClass(d){ return d>=90?'old':(d>=30?'mid':''); }

  function render(){
    var rows;
    if(state==='unpaid') rows = T.unpaid.slice();
    else if(state==='paid') rows = T.paid.slice();
    else if(state==='all') rows = T.records.slice();
    else rows = T.unpaid.filter(function(r){ return r.days>30; });

    rows.sort(function(a,b){
      if(state==='paid') return (a.paid_date||'').localeCompare(b.paid_date||'');
      return b.days - a.days;
    });

    if(!rows.length){ tbody.innerHTML = '<tr><td colspan="8" class="empty">没有符合条件的记录</td></tr>'; return; }
    tbody.innerHTML = rows.map(function(r){
      var paid = r.status==='已收';
      var tag = paid ? '<span class="tag paid">已收</span>'
                     : (r.days>30 ? '<span class="tag warn">未收</span>' : '<span class="tag unpaid">未收</span>');
      return '<tr>'+
        '<td class="num" style="text-align:left">'+esc(r.date)+'</td>'+
        '<td>'+esc(r.project)+'</td>'+
        '<td>'+esc(r.channel||'—')+'</td>'+
        '<td class="num">'+yuan(r.amount)+'</td>'+
        '<td class="num age '+ageClass(r.days)+'">'+r.days+' 天</td>'+
        '<td class="num" style="text-align:left;color:var(--muted)">'+esc(r.src_month||'—')+'</td>'+
        '<td class="num" style="text-align:left;color:var(--muted)">'+esc(r.paid_date||'—')+'</td>'+
        '<td>'+tag+'</td>'+
      '</tr>';
    }).join('');
  }

  document.querySelectorAll('.fbtn').forEach(function(b){
    b.addEventListener('click', function(){
      state = b.dataset.filter;
      document.querySelectorAll('.fbtn').forEach(function(x){ x.setAttribute('aria-pressed', x===b ? 'true':'false'); });
      render();
    });
  });

  var overdue = T.unpaid.filter(function(r){return r.days>30});
  document.getElementById('unpaidNote').textContent =
    '未收 ' + T.unpaid_count + ' 笔 ' + yuan(T.unpaid_total) +
    ' · 其中 ' + overdue.length + ' 笔已超 30 天（' + yuan(overdue.reduce(function(a,r){return a+r.amount},0)) + '）';
  render();
})();

/* ---------- 主题切换 ---------- */
(function(){
  var btn = document.getElementById('themeBtn');
  var saved = null;
  try{ saved = localStorage.getItem('lushu-theme'); }catch(e){}
  if(saved){ document.documentElement.setAttribute('data-theme', saved); }
  function sync(){ btn.textContent = document.documentElement.getAttribute('data-theme')==='dark' ? '◑ 浅色' : '◐ 深色'; }
  sync();
  btn.addEventListener('click', function(){
    var next = document.documentElement.getAttribute('data-theme')==='dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try{ localStorage.setItem('lushu-theme', next); }catch(e){}
    sync();
  });
})();

/* ---------- 入场 ---------- */
(function(){
  var els = document.querySelectorAll('.rv');
  if(!('IntersectionObserver' in window)){ els.forEach(function(e){e.classList.add('in')}); return; }
  var io = new IntersectionObserver(function(es){
    es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
  }, {threshold:.12});
  els.forEach(function(e){ io.observe(e); });
})();
</script>
</body>
</html>
"""

out = HTML.replace("__DATA__", DATA_JS)
os.makedirs(os.path.join(BASE, "dashboard"), exist_ok=True)
path = os.path.join(BASE, "dashboard", "index.html")
open(path, "w", encoding="utf-8").write(out)
print("WROTE", path, len(out), "bytes")
