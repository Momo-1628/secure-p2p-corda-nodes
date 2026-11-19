"""Renders every slide of a .pptx to PNG (1920x1080) with PowerPoint COM (LibreOffice is not installed here).
python scripts/render_slides.py <file.pptx> <out_dir> [--pdf]"""
import glob
import os
import sys

import win32com.client


def render(pptx, out_dir, pdf=False):
    pptx = os.path.abspath(pptx)
    out_dir = os.path.abspath(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    for f in glob.glob(os.path.join(out_dir, "slide_*.png")):
        os.remove(f)
    app = win32com.client.DispatchEx("PowerPoint.Application")
    try:
        pres = app.Presentations.Open(pptx, ReadOnly=True, Untitled=False, WithWindow=False)
        for i, slide in enumerate(pres.Slides, 1):
            slide.Export(os.path.join(out_dir, f"slide_{i:02d}.png"), "PNG", 1920, 1080)
        if pdf:
            pres.SaveAs(os.path.splitext(pptx)[0] + ".pdf", 32)  # ppSaveAsPDF
        n = pres.Slides.Count
        pres.Close()
    finally:
        app.Quit()
    print(f"rendered {n} slides -> {out_dir}")


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], "--pdf" in sys.argv)
