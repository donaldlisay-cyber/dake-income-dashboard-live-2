# -*- coding: utf-8 -*-
"""从 data/raw_income.json 抽出【每天登记的微博广告分成】，生成 scripts/daily_weibo.py。

两个数据源，列结构不同：

A) 「25年收入」（key 不以 '@24:' 开头）
   第 1 列 = 达克鸭唐，第 2 列 = 杰尼龟说   （2025-01 ~ 2026-12）

B) 「日期收入24年」（key 以 '@24:' 开头）
   第 1 列 = 达克鸭唐，**没有杰尼龟说这一列**
   （2023 全年 + 2024年8-12月）
   ⚠️ sheet 名与内容年份对不上：名为「24年1-7月」的其实是 2023 年数据，
      解析一律以单元格里的日期为准，不看 sheet 名。

用户口径（2026-09-12）：「日期收入24年」里的微博收入**都是达克鸭唐的**。
"""
import csv, io, json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw_income.json")
OUT = os.path.join(BASE, "scripts", "daily_weibo.py")

DATE_RE = re.compile(r"^(\d{4})/(\d{1,2})/(\d{1,2})$")
NUM_RE = re.compile(r"^-?\d+(\.\d+)?$")


def _num(row, i):
    v = (row[i] if len(row) > i else "").strip()
    return float(v) if NUM_RE.match(v) else 0.0


def main():
    with io.open(RAW, encoding="utf-8") as f:
        raw = json.load(f)

    daily = {}      # date -> (dake, jeni)
    from_src = {"25年收入": set(), "日期收入24年": set()}

    # 「日期收入24年」的 sheet 名 → 该 sheet 应有的年份。
    # 用户 2026-09-12 明确：只有「11月」「12月」两张是 2023 年，
    # 其余 sheet 就是 2024 年 1-12 月。
    # ⚠️ 源表笔误：sheet「24年1-7月」里的日期被写成了 2023/x/x（实为 2024），
    #    这里按 sheet 名强制纠正年份；「24年8-12月」源表本来就写的 2024。
    SHEET_YEAR_24 = {}
    for _i in range(1, 13):
        SHEET_YEAR_24["@24:24年%d月" % _i] = "2024"
    SHEET_YEAR_24["@24:23年11月"] = "2023"
    SHEET_YEAR_24["@24:23年12月"] = "2023"

    for sheet in raw:
        if sheet.startswith("__"):
            continue
        is24 = sheet.startswith("@24:")
        label = "日期收入24年" if is24 else "25年收入"
        force_year = SHEET_YEAR_24.get(sheet) if is24 else None
        for row in csv.reader(io.StringIO(raw[sheet])):
            if not row:
                continue
            m = DATE_RE.match((row[0] or "").strip())
            if not m:
                continue
            y, mo, dd = m.group(1), int(m.group(2)), int(m.group(3))
            if force_year and y != force_year:
                y = force_year          # 纠正源表年份笔误
            dt = "%s-%02d-%02d" % (y, mo, dd)
            a = _num(row, 1)
            b = 0.0 if is24 else _num(row, 2)      # 24年表没有杰尼龟说
            if not (a or b):
                continue
            if dt in daily:
                # 同一天被两张表登记时，保留金额更完整的那份
                pa, pb = daily[dt]
                if abs(a) + abs(b) >= abs(pa) + abs(pb):
                    daily[dt] = (round(a, 2), round(b, 2))
                    from_src[label].add(dt)
            else:
                daily[dt] = (round(a, 2), round(b, 2))
                from_src[label].add(dt)

    lines = [
        "# -*- coding: utf-8 -*-",
        '"""每天登记的微博广告分成。',
        "",
        "由 scripts/fetch_daily_weibo.py 从 data/raw_income.json 生成，勿手改。",
        "来源：「25年收入」月度表（2025-01起） + 「日期收入24年」（2023 全年 + 2024年8-12月）。",
        "格式：{ 'YYYY-MM-DD': (达克鸭唐, 杰尼龟说) }",
        '"""',
        "",
        "DAILY = {",
    ]
    for k in sorted(daily):
        lines.append("    '%s': (%.2f, %.2f)," % (k, daily[k][0], daily[k][1]))
    lines.append("}")
    lines.append("")

    with io.open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    td = sum(v[0] for v in daily.values())
    tj = sum(v[1] for v in daily.values())
    print("[daily] %d 天  %s ~ %s" % (len(daily), min(daily), max(daily)))
    print("[daily] 来源：25年收入 %d 天 / 日期收入24年 %d 天"
          % (len(from_src["25年收入"]), len(from_src["日期收入24年"])))
    print("[daily] 达克鸭唐 %.2f  杰尼龟说 %.2f" % (td, tj))
    print("[daily] -> %s" % OUT)


if __name__ == "__main__":
    main()
