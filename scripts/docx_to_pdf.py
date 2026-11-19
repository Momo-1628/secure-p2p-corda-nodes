"""Updates fields/TOC in a .docx with Microsoft Word (COM), saves it and exports a PDF; optional page previews.
python scripts/docx_to_pdf.py <file.docx> [preview_dir]"""
import os
import sys

import win32com.client


def convert(docx, preview_dir=None):
    docx = os.path.abspath(docx)
    pdf = os.path.splitext(docx)[0] + ".pdf"
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        d = word.Documents.Open(docx)
        d.Fields.Update()
        for toc in d.TablesOfContents:
            toc.Update()
        d.Save()
        d.ExportAsFixedFormat(pdf, 17)  # wdExportFormatPDF
        pages = d.ComputeStatistics(2)  # wdStatisticPages
        d.Close(False)
    finally:
        word.Quit()
    print(f"pdf: {pdf}  pages: {pages}")
    if preview_dir:
        import fitz
        os.makedirs(preview_dir, exist_ok=True)
        for i, page in enumerate(fitz.open(pdf)):
            page.get_pixmap(dpi=60).save(os.path.join(preview_dir, f"page-{i + 1:02d}.png"))
    return pdf


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
