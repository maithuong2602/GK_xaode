"""
Excel Exporter Module using openpyxl.
Generates comprehensive mapping matrices and answer key tables for teachers.
"""
import io
from typing import Dict, List, Tuple, Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from backend.models import VariantPreviewData


def create_mapping_excel(
    original_filename: str,
    variants_data: Dict[str, VariantPreviewData],
    detected_answers: Dict[int, str],
) -> bytes:
    """Creates a beautifully styled Excel workbook containing the Answer Key Matrix,
    Question Mapping Matrix, and Detailed Per-Variant Sheets."""
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="1E293B")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=11)

    primary_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid") # Deep Indigo
    secondary_fill = PatternFill(start_color="0284C7", end_color="0284C7", fill_type="solid") # Ocean Blue
    accent_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1'),
    )

    center_align = Alignment(horizontal='center', vertical='center')
    left_align = Alignment(horizontal='left', vertical='center')

    variant_codes = list(variants_data.keys())
    first_var = list(variants_data.values())[0]
    total_qs = len(first_var.question_mappings)

    # ================= SHEET 1: MA TRẬN ĐÁP ÁN (ANSWER KEY MATRIX) =================
    ws_ans = wb.create_sheet(title="Ma Trận Đáp Án")
    ws_ans.views.sheetView[0].showGridLines = True

    # Title
    ws_ans.merge_cells("A1:G1")
    ws_ans["A1"] = f"BẢNG TỔNG HỢP ĐÁP ÁN CÁC MÃ ĐỀ - {original_filename}"
    ws_ans["A1"].font = title_font
    ws_ans["A1"].alignment = left_align
    ws_ans.row_dimensions[1].height = 30

    # Headers
    headers = ["Câu"] + ["Đề Gốc"] + [f"Mã {code}" for code in variant_codes]
    for col_idx, h in enumerate(headers, start=1):
        cell = ws_ans.cell(row=3, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = primary_fill
        cell.alignment = center_align
        cell.border = thin_border
    ws_ans.row_dimensions[3].height = 25

    # Rows: 1..total_qs
    for q_num in range(1, total_qs + 1):
        row_idx = 3 + q_num
        row_cells = [ws_ans.cell(row=row_idx, column=1, value=f"Câu {q_num}")]
        row_cells[0].font = bold_font
        row_cells[0].alignment = center_align
        row_cells[0].border = thin_border

        # Orig answer
        orig_ans = detected_answers.get(q_num, "")
        c_orig = ws_ans.cell(row=row_idx, column=2, value=orig_ans)
        c_orig.font = bold_font
        c_orig.alignment = center_align
        c_orig.border = thin_border

        # Variant answers for new question q_num
        for v_idx, code in enumerate(variant_codes, start=3):
            var_data = variants_data[code]
            # Find mapping for new_number == q_num
            m_item = next((m for m in var_data.question_mappings if m.new_number == q_num), None)
            new_ans = m_item.new_answer if m_item else ""
            c_var = ws_ans.cell(row=row_idx, column=v_idx, value=new_ans)
            c_var.font = bold_font
            c_var.alignment = center_align
            c_var.border = thin_border
            if row_idx % 2 == 1:
                c_var.fill = accent_fill

        ws_ans.row_dimensions[row_idx].height = 20

    # Auto column width
    for col in ws_ans.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_ans.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # ================= SHEET 2: BẢNG ÁNH XẠ CÂU HỎI (MAPPING) =================
    ws_map = wb.create_sheet(title="Ánh Xạ Câu Hỏi")
    ws_map.views.sheetView[0].showGridLines = True

    ws_map.merge_cells("A1:G1")
    ws_map["A1"] = f"BẢNG ÁNH XẠ CÂU HỎI (CÂU MỚI -> CÂU GỐC) - {original_filename}"
    ws_map["A1"].font = title_font
    ws_map["A1"].alignment = left_align
    ws_map.row_dimensions[1].height = 30

    map_headers = ["Câu Mới"] + [f"Mã {code} (Câu gốc)" for code in variant_codes]
    for col_idx, h in enumerate(map_headers, start=1):
        cell = ws_map.cell(row=3, column=col_idx, value=h)
        cell.font = header_font
        cell.fill = secondary_fill
        cell.alignment = center_align
        cell.border = thin_border
    ws_map.row_dimensions[3].height = 25

    for q_num in range(1, total_qs + 1):
        row_idx = 3 + q_num
        c_lbl = ws_map.cell(row=row_idx, column=1, value=f"Câu {q_num}")
        c_lbl.font = bold_font
        c_lbl.alignment = center_align
        c_lbl.border = thin_border

        for v_idx, code in enumerate(variant_codes, start=2):
            var_data = variants_data[code]
            m_item = next((m for m in var_data.question_mappings if m.new_number == q_num), None)
            orig_n = f"Câu {m_item.original_number}" if m_item else ""
            c_val = ws_map.cell(row=row_idx, column=v_idx, value=orig_n)
            c_val.font = regular_font
            c_val.alignment = center_align
            c_val.border = thin_border
            if row_idx % 2 == 1:
                c_val.fill = accent_fill

        ws_map.row_dimensions[row_idx].height = 20

    for col in ws_map.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws_map.column_dimensions[col_letter].width = max(max_len + 4, 15)

    # Save to buffer
    out_buf = io.BytesIO()
    wb.save(out_buf)
    return out_buf.getvalue()
