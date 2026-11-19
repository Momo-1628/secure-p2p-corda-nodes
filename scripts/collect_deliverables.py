"""Copies the final deliverables into deliverables/ and writes links.txt.  Gagan N (24BTRBT013)"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "deliverables")
os.makedirs(D, exist_ok=True)
files = ["report/Project_Report_24BTRBT013.docx", "report/Project_Report_24BTRBT013.pdf",
         "ppt/Topic12_Secure_P2P_Corda_24BTRBT013.pptx",
         "video/Topic12_PPT_Presentation_24BTRBT013.mp4", "video/Topic12_PPT_Presentation_24BTRBT013.srt",
         "video/Topic12_Live_Demo_24BTRBT013.mp4", "video/Topic12_Live_Demo_24BTRBT013.srt"]
for f in files:
    src = os.path.join(ROOT, f)
    if os.path.exists(src):
        shutil.copy2(src, D)
        print(f"  {os.path.basename(f):<48} {os.path.getsize(src) / 1e6:7.2f} MB")
    else:
        print(f"  MISSING {f}")
url = sys.argv[1] if len(sys.argv) > 1 else ""
with open(os.path.join(D, "links.txt"), "w", encoding="utf-8") as fh:
    fh.write("Secure Peer-to-Peer Communication between Enterprise Corda Nodes - Gagan N (24BTRBT013)\n")
    fh.write(f"GitHub repository: {url or '(not pushed)'}\n")
print("  links.txt ->", url or "(not pushed)")
