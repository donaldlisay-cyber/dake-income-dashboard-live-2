# -*- coding: utf-8 -*-
"""
刷新收入看板 —— 一条命令重新抓取腾讯文档并重建看板。

用法（在项目根目录执行）：
    python scripts/update_dashboard.py

它会依次：
  1. fetch_income.py       从腾讯文档抓 24 张月度表 + 代收款跟踪表
  2. parse_income.py       解析成结构化数据
  3. fetch_daily_weibo.py  从月度表抽出「每日微博广告分成」-> scripts/daily_weibo.py
  4. build_dashboard.py    生成 dashboard/index.html

在腾讯文档里加了新收入/改了收款状态后，跑这一条就够了。

只更新了 MediaShareList 明细（没动腾讯文档）时，直接跑 build_dashboard.py 即可。
"""
import subprocess, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
STEPS = ["fetch_income.py", "parse_income.py", "fetch_daily_weibo.py", "build_dashboard.py"]

def main():
    for s in STEPS:
        path = os.path.join(BASE, "scripts", s)
        print(f"\n>>> {s}")
        r = subprocess.run([PY, path], cwd=BASE, capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("!! 失败")
            print(r.stdout[-2000:])
            print(r.stderr[-2000:])
            sys.exit(1)
        tail = [l for l in (r.stdout or "").strip().split("\n") if l.strip()][-6:]
        print("\n".join("    " + l for l in tail))
    print("\n✅ 看板已刷新 -> dashboard/index.html")

if __name__ == "__main__":
    main()
