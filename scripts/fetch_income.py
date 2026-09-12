# -*- coding: utf-8 -*-
"""Fetch all 24 monthly sheets + tracking sheet from Tencent Docs, dump to JSON."""
import json, subprocess, sys, csv, io, os

SKILL = r"C:\Users\DACK\.workbuddy\plugins\cache\workbuddy-builtin\tencent-docs-plugin\5.5.6-wb.38337834.g5f969292.h4918b5ced607\skills\tencent-docs"
PY = r"C:\Users\DACK\.workbuddy\binaries\python\versions\3.13.12\python.exe"
OUT = r"E:\工作文件\2026-09-12-00-44-43\data"
os.makedirs(OUT, exist_ok=True)

MONTHS = [
    ("25年1月","BB08J2"),("25年2月","wakoc5"),("25年3月","iqxb0f"),("25年4月","ti15k1"),
    ("25年5月","kebgwb"),("25年6月","3m6r1i"),("25年7月","1qugd8"),("25年8月","7dctcw"),
    ("25年9月","q1cnh5"),("25年10月","pkh9zu"),("25年11月","3i5mrb"),("25年12月","ejd1o1"),
    ("26年1月","seoq30"),("26年2月","5cz7pj"),("26年3月","yoxw1o"),("26年4月","6zzlu5"),
    ("26年5月","dijj3o"),("26年6月","hdkmqz"),("26年7月","Q52EKt"),("26年8月","2ownak"),
    ("26年9月","cvl2cb"),("26年10月","8ZT0G2"),("26年11月","P2GtGd"),("26年12月","GXBCRa"),
]

# 「日期收入24年」file_id UsgcWyuKlKKx —— 2023 全年 + 2024年8-12月。
# ⚠️ 表名有误导：sheet 名「24年1-7月」里装的是【2023年】的数据。
# 各 sheet 的实际日期以内容为准，解析时按内容走，别看名字。
# 该表列结构与 25年收入 不同：第 1 列就是微博广告分成（只有达克鸭唐一人，无杰尼龟说）。
MONTHS24 = [
    ("24年1月","oxy1f3"),("24年2月","zxrxev"),("24年3月","8p3lul"),("24年4月","5shbw5"),
    ("24年5月","1nbyzq"),("24年6月","jjm036"),("24年7月","e2h9ex"),("24年8月","1qqwqk"),
    ("24年9月","2ptnaf"),("24年10月","mjjwss"),("24年11月","7tqn44"),("24年12月","ebflwx"),
    ("23年11月","l88kex"),("23年12月","BB08J2"),
]

def call(sheet_id, file_id="UhJIpvQQIykx", end_row=70, end_col=14):
    args = json.dumps({"file_id": file_id, "sheet_id": sheet_id,
                       "start_row": 0, "start_col": 0,
                       "end_row": end_row, "end_col": end_col,
                       "return_csv": True, "include_formula": False})
    r = subprocess.run([PY, "tencentdocs.py", "tdoc_call", "sheet-mcp", "get_cell_data", args],
                       cwd=SKILL, capture_output=True, text=True, encoding="utf-8")
    try:
        j = json.loads(r.stdout)
        txt = j["result"]["content"][0]["text"]
        return json.loads(txt).get("csv_data", "")
    except Exception as e:
        return "ERR:" + str(e) + "|" + r.stdout[:300]

out = {}
for name, sid in MONTHS:
    raw = call(sid)
    out[name] = raw
    print(name, "OK" if not raw.startswith("ERR") else raw[:200], flush=True)

# 「日期收入24年」（2023 + 2024下半年）—— 行数较多，多取一些
for name, sid in MONTHS24:
    raw = call(sid, file_id="UsgcWyuKlKKx", end_row=130)
    out["@24:" + name] = raw
    print("24年表", name, "OK" if not raw.startswith("ERR") else raw[:200], flush=True)

# tracking sheet
track = call("BB08J2", file_id="UgcELoEQSrgj", end_row=115)
out["__tracking__"] = track
print("tracking OK" if not track.startswith("ERR") else track[:200])

with open(os.path.join(OUT, "raw_income.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("DONE ->", os.path.join(OUT, "raw_income.json"))
