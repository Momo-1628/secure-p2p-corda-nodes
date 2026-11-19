"""Shows a sample of the demo console layout for a few seconds (used by record_demo.py test)."""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import demo_script as d  # noqa: E402

d.setup_console()
time.sleep(1.5)
d.clear()
w = min(d.cols(), 160) - 1
print(d.BANNER_BG + d.BOLD + " STEP 7/12 ▸ Sending encrypted messages EnterpriseA -> EnterpriseB ".ljust(w) + d.RESET)
print(f"columns = {d.cols()}")
print("+---+-------------+-------------+-------------------------------+-----------------+-----------------------------------------+---------+")
print("| 1 | EnterpriseA | EnterpriseB | PO-2026-0412 Purchase details | 3C162F73C2EA... | PO+MEP55KgqqFTzKbE+5PS9uKWy8Db1OzsKE... | 13407   |")
for i in range(30):
    print(d.colour(f"line {i:02d}  PASS  sample output"))
time.sleep(6)
