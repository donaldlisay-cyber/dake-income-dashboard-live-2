# -*- coding: utf-8 -*-
"""Parse raw_income.json -> structured dashboard_data.json"""
import json, os, csv, io, re

BASE = r"E:\工作文件\2026-09-12-00-44-43"
raw = json.load(open(os.path.join(BASE, "data", "raw_income.json"), encoding="utf-8"))

def num(s):
    if s is None: return 0.0
    s = str(s).strip().replace(",", "").replace("¥", "").replace("￥", "")
    if not s or s in ("-", "—", "未收", "已收"): return 0.0
    try: return float(s)
    except: return 0.0

def rows_of(csv_text):
    return list(csv.reader(io.StringIO(csv_text)))

months = []
months24 = []          # 「日期收入24年」—— 列结构与主表不同，单独解析
for key, raw_csv in raw.items():
    if key == "__tracking__":
        continue
    rows = rows_of(raw_csv)
    if not rows:
        continue

    # ---------- 「日期收入24年」：第 0=日期 1=微博广告分成(达克) 2=V+ 3=创作激励 4=微任务
    #            5=米哈游 6=公益/芒果 7=娱乐/话题 8=支付宝红包/工资
    #            9=【整月总收入（税后）】 10=总收入（税后） 11=实收 12=待收
    # ⚠️ 关键坑（2026-09-12 用户质询 24年9月实收只有 38813.98）：
    #    第 9 列**只在月初那一行**填一次，填的是【整月总收入（税后）】，
    #    不是"其他收入"！它与微博明细重复。第 10 列是同一笔"总收入（税后）"。
    #    → 月度总收入取 第10列 or 第9列（兜底），**绝不再叠加微博明细**。
    # 用户 2026-09-12：这里的微博收入都是达克鸭唐的，没有杰尼龟说。
    # ⚠️ sheet 名 → 应有年份（源表笔误：名为「24年1-7月」的日期被写成 2023/x/x，实为 2024）。
    if key.startswith("@24:"):
        _n = key[4:]
        _mm = re.match(r"24年(\d+)月", _n)
        force_year = "2024" if _mm else "2023"     # 「11月」「12月」= 2023，其余 = 2024
        m = {"month": _n, "sheet": key, "weibo_dake": 0.0, "weibo_jn": 0.0,
             "weibo_weiren": 0.0, "weibo_total": 0.0, "weibo_days": 0,
             "other": 0.0, "total": 0.0, "gross": 0.0, "actual": 0.0,
             "ad_items": [], "other_items": [], "actual_years": [], "daily": {}}
        _month_gross = 0.0          # 第 9/10 列 —— 整月总收入（税后）
        for r in rows:
            if not r:
                continue
            def g(i): return r[i].strip() if len(r) > i else ""
            c0 = g(0)
            if re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", c0):
                y, mo, dd = c0.split("/")
                if y != force_year:
                    y = force_year
                    c0 = "%s/%s/%s" % (y, mo, dd)
                wd = num(g(1))
                m["weibo_dake"] += wd
                if wd:
                    m["weibo_days"] += 1
                m["daily"][c0] = wd
                if y not in m["actual_years"]:
                    m["actual_years"].append(y)
                # 收入列只用来兜底整月总收入（不累加进"其他收入"）
                _gr = num(g(10)) or num(g(9))
                if _gr:
                    _month_gross = max(_month_gross, _gr)
                _ac = num(g(11))
                if _ac:
                    m["actual"] = max(m["actual"], _ac)
            elif c0 in ("合计", "总计"):
                _sum_total = num(g(10)) or num(g(11))
                if _sum_total:
                    _month_gross = _month_gross or _sum_total
        m["gross"] = round(_month_gross, 2)
        m["total"] = round(_month_gross, 2)          # ★总收入即整月收入，不叠加
        m["other"] = 0.0                             # 明细口径下不再单列"其他收入"
        m["weibo_total"] = m["weibo_dake"] + m["weibo_jn"] + m["weibo_weiren"]
        m["calc_total"] = m["total"]
        months24.append(m)
        continue

    m = {"month": key, "weibo_dake": 0.0, "weibo_jn": 0.0, "weibo_weiren": 0.0,
         "ad_dake": 0.0, "ad_jn": 0.0, "other": 0.0, "total": 0.0,
         "ad_items": [], "weibo_days": 0, "weibo_total": 0.0, "other_items": []}
    for r in rows:
        if not r: continue
        c0 = (r[0] or "").strip()
        def g(i):
            return r[i].strip() if len(r) > i else ""
        # data rows: first col is a date like 2025/1/1
        if re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", c0):
            wd, wj = num(g(1)), num(g(2))
            wr = num(g(3))
            m["weibo_dake"] += wd; m["weibo_jn"] += wj; m["weibo_weiren"] += wr
            if wd or wj: m["weibo_days"] += 1
            ad_d, ad_j = num(g(6)), num(g(7))
            m["ad_dake"] += ad_d; m["ad_jn"] += ad_j
            if ad_d:
                m["ad_items"].append({"date": c0, "amount": ad_d, "note": g(8), "channel": g(9)})
            if ad_j:
                m["ad_items"].append({"date": c0, "amount": ad_j, "note": g(8) or "杰尼龟说", "channel": g(9)})
            ot = num(g(10))
            m["other"] += ot
            if ot:
                m["other_items"].append({"date": c0, "amount": ot, "note": g(8), "channel": g(9)})
        elif c0 == "合计":
            m["total"] = num(g(11)) or num(g(12))
    # recompute total if missing
    calc = m["weibo_dake"] + m["weibo_jn"] + m["weibo_weiren"] + m["ad_dake"] + m["ad_jn"] + m["other"]
    m["calc_total"] = calc
    if not m["total"]:
        m["total"] = calc
    m["weibo_total"] = m["weibo_dake"] + m["weibo_jn"] + m["weibo_weiren"]
    months.append(m)

# ---- 合并「日期收入24年」：按【内容里的真实自然月】归并 ----
# sheet 名有误导（「24年1月」装的是 2023/1），一律按 daily 的日期归月。
from collections import OrderedDict as _OD

def _ym_of(datestr):
    """'2023/1/5' 或 '2023-01-05' -> '2023-01'"""
    y, mo = datestr.split("/")[0], datestr.split("/")[1]
    return "%s-%02d" % (y, int(mo))

_ms = _OD()
for m in months24:
    for d, v in m["daily"].items():
        ym = _ym_of(d)
        e = _ms.setdefault(ym, {"key": ym, "dake": 0.0, "days": 0, "other": 0.0,
                                "total": 0.0, "sheets": []})
        e["dake"] += v
        if v:
            e["days"] += 1
        if m["sheet"] not in e["sheets"]:
            e["sheets"].append(m["sheet"])
    # 整月总收入（税后）—— 按 daily 的真实自然月归属，直接覆盖该月 total
    _yms = set(_ym_of(d) for d in m["daily"])
    if len(_yms) == 1:
        ym = _yms.pop()
        e = _ms.setdefault(ym, {"key": ym, "dake": 0.0, "days": 0, "other": 0.0,
                                "total": 0.0, "sheets": []})
        if m["total"]:
            e["total"] = m["total"]

months24_merged = sorted(_ms.values(), key=lambda x: x["key"])

# ---- parse tracking sheet ----
track_rows = rows_of(raw["__tracking__"])
records = []
chan = ""
for r in track_rows:
    if not r: continue
    def g(i): return (r[i].strip() if len(r) > i else "")
    c0 = g(0)
    if c0.startswith("▸"):
        chan = c0[1:].strip()
        continue
    if re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", g(1)):
        amt = num(g(4))
        status = g(8)
        records.append({
            "date": g(1), "project": g(2), "channel": g(3) or chan,
            "amount": amt, "days_raw": g(5), "src_month": g(6),
            "paid_date": g(7), "status": status or "未收",
        })

# dedupe: same (date, project, amount) appearing twice keeps first, prefer 已收
seen = {}
for rec in records:
    k = (rec["date"], rec["project"], rec["amount"])
    if k in seen:
        if rec["status"] == "已收" and seen[k]["status"] != "已收":
            seen[k] = rec
    else:
        seen[k] = rec
records = list(seen.values())

def days_num(s):
    m = re.search(r"(\d+)", s or "")
    return int(m.group(1)) if m else 0

for rec in records:
    rec["days"] = days_num(rec["days_raw"])

unpaid = [r for r in records if r["status"] != "已收"]
paid = [r for r in records if r["status"] == "已收"]

# channel grouping for unpaid
by_chan = {}
for r in unpaid:
    by_chan.setdefault(r["channel"] or "(无)", []).append(r)

chan_summary = []
for ch, items in sorted(by_chan.items(), key=lambda kv: -sum(i["amount"] for i in kv[1])):
    amt = sum(i["amount"] for i in items)
    mx = max((i["days"] for i in items), default=0)
    chan_summary.append({"channel": ch, "amount": amt, "count": len(items), "max_days": mx})

data = {
    "months": months,
    "months24": months24_merged,
    "tracking": {
        "records": records,
        "unpaid": unpaid,
        "paid": paid,
        "chan_summary": chan_summary,
        "unpaid_total": sum(r["amount"] for r in unpaid),
        "paid_total": sum(r["amount"] for r in paid),
        "all_total": sum(r["amount"] for r in records),
        "unpaid_count": len(unpaid),
        "paid_count": len(paid),
        "all_count": len(records),
    },
    "generated_at": "2026-09-12",
}

os.makedirs(os.path.join(BASE, "data"), exist_ok=True)
json.dump(data, open(os.path.join(BASE, "data", "dashboard_data.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("=== 月度 ===")
for m in months:
    print(f"{m['month']:>8}  微博{m['weibo_total']:>10,.0f}  广告{m['ad_dake']+m['ad_jn']:>9,.0f}  其他{m['other']:>8,.0f}  合计{m['total']:>10,.0f}")
ys = sum(m["total"] for m in months if m["month"].startswith("25"))
ys2 = sum(m["total"] for m in months if m["month"].startswith("26") and m["month"] != "26年12月")
print(f"\n25年合计(已录) {ys:,.0f}   26年合计 {ys2:,.0f}")
print("\n=== 日期收入24年（按内容真实月份归并）===")
for m in months24_merged:
    print(f"  {m['key']}  微博{m['dake']:>10,.2f}  {m['days']:>2}天  "
          f"整月总收入{m['total']:>10,.2f}  来源sheet={m['sheets']}")
print(f"  合计微博 {sum(m['dake'] for m in months24_merged):,.2f}  "
      f"整月总收入合计 {sum(m['total'] for m in months24_merged):,.2f}  "
      f"共 {sum(m['days'] for m in months24_merged)} 天")
print("\n=== 渠道未收 ===")
for c in chan_summary:
    print(f"  {c['channel']:<12} {c['amount']:>9,.0f}  {c['count']}笔  最长{c['max_days']}天")
t = data["tracking"]
print(f"\n未收 {t['unpaid_count']}笔 ¥{t['unpaid_total']:,.0f} | 已收 {t['paid_count']}笔 ¥{t['paid_total']:,.0f} | 全部 {t['all_count']}笔 ¥{t['all_total']:,.0f}")
