"""
Docx Answer Key Exporter Module.
Generates a standalone, beautifully formatted Word document (Dap_An.docx)
containing answer keys for all generated test variants.
"""
import io
from typing import Dict, List, Any
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from backend.models import VariantPreviewData


def set_cell_background(cell: Any, fill_hex: str) -> None:
    """Sets background shading of a table cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tcPr.append(shd)


def create_answer_key_docx(
    original_filename: str,
    variants_data: Dict[str, VariantPreviewData],
    detected_answers: Dict[int, str],
) -> bytes:
    """Creates a standalone Word document containing the answer keys for all variants."""
    doc = docx.Document()

    # Set page margins to standard A4 (2cm)
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Header
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_title = p_title.add_run("BẢNG TỔNG HỢP ĐÁP ÁN CÁC MÃ ĐỀ")
    run_title.bold = True
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(16)
    run_title.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run(f"Tài liệu gốc: {original_filename}")
    run_sub.font.name = "Times New Roman"
    run_sub.font.size = Pt(12)
    run_sub.italic = True

    doc.add_paragraph()  # Spacing

    variant_codes = list(variants_data.keys())
    first_var = list(variants_data.values())[0]
    total_qs = len(first_var.question_mappings)

    # Build Table: Columns: Câu | Đề gốc | Mã 101 | Mã 102 ...
    num_cols = 2 + len(variant_codes)
    table = doc.add_table(rows=total_qs + 1, cols=num_cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    # Header Row
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Câu"
    hdr_cells[1].text = "Đề gốc"
    for v_idx, code in enumerate(variant_codes, start=2):
        hdr_cells[v_idx].text = f"Mã {code}"

    for cell in hdr_cells:
        set_cell_background(cell, "1E3A8A")
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:
                r.bold = True
                r.font.name = "Times New Roman"
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                r.font.size = Pt(11)

    # Data Rows
    for q_idx in range(1, total_qs + 1):
        row_cells = table.rows[q_idx].cells
        row_cells[0].text = f"Câu {q_idx}"
        row_cells[1].text = detected_answers.get(q_idx, "")

        for v_idx, code in enumerate(variant_codes, start=2):
            var_data = variants_data[code]
            m_item = next((m for m in var_data.question_mappings if m.new_number == q_idx), None)
            row_cells[v_idx].text = m_item.new_answer if m_item else ""

        # Formatting
        is_even = (q_idx % 2 == 0)
        for c_idx, cell in enumerate(row_cells):
            if is_even:
                set_cell_background(cell, "F8FAFC")
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                for r in p.runs:
                    r.font.name = "Times New Roman"
                    r.font.size = Pt(11)
                    if c_idx == 0:
                        r.bold = True

    # Note at bottom
    p_note = doc.add_paragraph()
    p_note.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r_note = p_note.add_run("\n* Hệ thống tự động tạo và cập nhật đáp án theo thuật toán bảo toàn định dạng.")
    r_note.font.name = "Times New Roman"
    r_note.font.size = Pt(10)
    r_note.italic = True
    r_note.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    out_buf = io.BytesIO()
    doc.save(out_buf)
    return out_buf.getvalue()
