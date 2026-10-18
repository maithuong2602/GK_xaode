"""
FastAPI Routes and Controller for Exam Shuffler Application.
"""
import io
import os
import uuid
import zipfile
from typing import Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

from backend.models import (
    DocumentAnalysisResult,
    ShuffleRequestConfig,
    VariantPreviewData,
)
from backend.parser import DocxParser
from backend.pdf_engine import PdfInspector
from backend.shuffler import DocxShuffler
from backend.excel_exporter import create_mapping_excel
from backend.docx_exporter import create_answer_key_docx
from backend.answer_manager import AnswerManager

router = APIRouter(prefix="/api")

# In-memory session cache: session_id -> SessionData
SESSION_CACHE: Dict[str, Dict[str, Any]] = {}


class ParseAnswersRequest(BaseModel):
    raw_text: str


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Uploads Word or PDF exam paper and analyzes its structure."""
    contents = await file.read()
    filename = file.filename or "uploaded_exam.docx"
    ext = os.path.splitext(filename)[1].lower()

    session_id = str(uuid.uuid4())

    if ext == ".docx":
        try:
            parser = DocxParser(contents, filename)
            analysis = parser.analyze()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không thể đọc file Word: {str(e)}")

        SESSION_CACHE[session_id] = {
            "file_bytes": contents,
            "filename": filename,
            "file_type": "docx",
            "analysis": analysis,
            "variants": {},
            "excel_bytes": None,
            "answer_docx_bytes": None,
        }

        return {
            "session_id": session_id,
            "analysis": analysis.model_dump(),
            "thumbnails": [],
        }

    elif ext == ".pdf":
        try:
            inspector = PdfInspector(contents, filename)
            analysis = inspector.inspect()
            thumbnails = inspector.render_page_thumbnails(max_pages=4)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Không thể đọc file PDF: {str(e)}")

        SESSION_CACHE[session_id] = {
            "file_bytes": contents,
            "filename": filename,
            "file_type": "pdf",
            "analysis": analysis,
            "variants": {},
            "excel_bytes": None,
            "answer_docx_bytes": None,
        }

        return {
            "session_id": session_id,
            "analysis": analysis.model_dump(),
            "thumbnails": thumbnails,
        }

    else:
        raise HTTPException(
            status_code=400,
            detail="Định dạng file không được hỗ trợ. Vui lòng tải lên file .docx hoặc .pdf."
        )


@router.post("/parse-answers")
async def parse_answers(req: ParseAnswersRequest):
    """Parses raw text pasted by teachers into a structured dictionary."""
    parsed = AnswerManager.parse_pasted_answer_string(req.raw_text)
    return {"answers": parsed, "count": len(parsed)}


@router.post("/shuffle/{session_id}")
async def shuffle_exam(session_id: str, config: ShuffleRequestConfig):
    """Generates shuffled variants, answer mappings, excel report, and answer key docx."""
    session = SESSION_CACHE.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Phiên làm việc không tồn tại hoặc đã hết hạn.")

    if session["file_type"] != "docx":
        # For PDF, if user insisted on proceeding
        if session["analysis"].is_scanned_pdf:
            raise HTTPException(
                status_code=400,
                detail="Đây là file PDF scan/ảnh, không thể xáo trực tiếp. Vui lòng sử dụng file Word (.docx)."
            )

    try:
        shuffler = DocxShuffler(session["file_bytes"], session["analysis"], config)
        variants = shuffler.generate_all_variants()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi trong quá trình xáo đề: {str(e)}")

    # Store variants
    session["variants"] = variants
    session["variants_teacher"] = shuffler.teacher_variants
    session["variants_student"] = shuffler.student_variants

    # Generate Excel and Docx answer key in background/memory
    preview_map = {code: data[1] for code, data in variants.items()}
    active_answers = dict(session["analysis"].detected_answers)
    for q_id, ans in config.custom_answers.items():
        if q_id.startswith("q_"):
            try:
                q_num = int(q_id[2:])
                active_answers[q_num] = ans
            except Exception:
                pass

    excel_bytes = create_mapping_excel(session["filename"], preview_map, active_answers)
    answer_docx_bytes = create_answer_key_docx(session["filename"], preview_map, active_answers)

    session["excel_bytes"] = excel_bytes
    session["answer_docx_bytes"] = answer_docx_bytes

    return {
        "status": "success",
        "variants": {code: prev.model_dump() for code, (_, prev) in variants.items()},
        "total_variants": len(variants),
    }


import urllib.parse
import re

def get_download_headers(filename: str) -> dict:
    """Creates standards-compliant Content-Disposition headers for all browsers."""
    ascii_safe = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    quoted_utf8 = urllib.parse.quote(filename)
    return {
        "Content-Disposition": f'attachment; filename="{ascii_safe}"; filename*=utf-8\'\'{quoted_utf8}',
        "Access-Control-Expose-Headers": "Content-Disposition",
    }


@router.get("/download/{session_id}/{variant_code}")
@router.get("/download/{session_id}/{variant_code}/{filename}")
async def download_variant(
    session_id: str,
    variant_code: str,
    filename: Optional[str] = None,
    mode: Optional[str] = "student",
):
    """Downloads a single generated variant Word document (student clean copy or teacher copy with answers & question mapping)."""
    session = SESSION_CACHE.get(session_id)
    if not session or not session.get("variants"):
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu mã đề.")

    is_teacher = mode in ["teacher", "with_answers"]
    if is_teacher and session.get("variants_teacher") and variant_code in session["variants_teacher"]:
        variant = session["variants_teacher"].get(variant_code)
    elif mode in ["student", "exam_only"] and session.get("variants_student") and variant_code in session["variants_student"]:
        variant = session["variants_student"].get(variant_code)
    else:
        variant = session["variants"].get(variant_code)

    if not variant:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy mã đề {variant_code}.")

    docx_bytes, _ = variant
    base_name = os.path.splitext(session["filename"])[0]
    suffix = "_Kem_Dap_An" if is_teacher else ""
    out_filename = filename or f"{base_name}_De_{variant_code}{suffix}.docx"
    if not out_filename.endswith(".docx"):
        out_filename += ".docx"

    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=get_download_headers(out_filename),
    )


@router.get("/download-excel/{session_id}")
@router.get("/download-excel/{session_id}/{filename}")
async def download_excel(session_id: str, filename: Optional[str] = None):
    """Downloads the Excel Mapping Matrix (Bang_Anh_Xa.xlsx)."""
    session = SESSION_CACHE.get(session_id)
    if not session or not session.get("excel_bytes"):
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu bảng ánh xạ.")

    out_filename = filename or "Bang_Anh_Xa_Va_Dap_An.xlsx"
    if not out_filename.endswith(".xlsx"):
        out_filename += ".xlsx"

    return Response(
        content=session["excel_bytes"],
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=get_download_headers(out_filename),
    )


@router.get("/download-answer-docx/{session_id}")
@router.get("/download-answer-docx/{session_id}/{filename}")
async def download_answer_docx(session_id: str, filename: Optional[str] = None):
    """Downloads the standalone Answer Key Word document (Dap_An.docx)."""
    session = SESSION_CACHE.get(session_id)
    if not session or not session.get("answer_docx_bytes"):
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu đáp án Word.")

    out_filename = filename or "Bang_Dap_An_Tong_Hop.docx"
    if not out_filename.endswith(".docx"):
        out_filename += ".docx"

    return Response(
        content=session["answer_docx_bytes"],
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=get_download_headers(out_filename),
    )


@router.get("/download-zip/{session_id}")
@router.get("/download-zip/{session_id}/{filename}")
async def download_all_zip(
    session_id: str,
    filename: Optional[str] = None,
    mode: Optional[str] = "all",
):
    """Packages generated variants, Excel matrix, and answer key into a ZIP archive."""
    session = SESSION_CACHE.get(session_id)
    if not session or not session.get("variants"):
        raise HTTPException(status_code=404, detail="Chưa có dữ liệu để nén.")

    base_name = os.path.splitext(session["filename"])[0]
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # 1. Student variant files (De_Thi_Hoc_Sinh)
        if mode in ["all", "student", "exam_only"]:
            folder = "De_Thi_Hoc_Sinh/" if mode == "all" else ""
            for code, (docx_bytes, _) in session["variants"].items():
                zip_file.writestr(f"{folder}De_{code}.docx", docx_bytes)

        # 2. Teacher variant files (De_Thi_Giao_Vien_Kem_Dap_An)
        if mode in ["all", "teacher", "with_answers"] and session.get("variants_teacher"):
            folder = "De_Thi_Giao_Vien_Kem_Dap_An/" if mode == "all" else ""
            for code, (docx_bytes, _) in session["variants_teacher"].items():
                zip_file.writestr(f"{folder}De_{code}_Kem_Dap_An.docx", docx_bytes)

        # 3. Add answer key docx (for teacher / all)
        if mode in ["all", "teacher", "with_answers"] and session.get("answer_docx_bytes"):
            zip_file.writestr("Dap_An_Tong_Hop.docx", session["answer_docx_bytes"])

        # 4. Add excel matrix
        if session.get("excel_bytes"):
            zip_file.writestr("Bang_Anh_Xa.xlsx", session["excel_bytes"])

        # 5. Add README guide for teachers
        mode_desc = (
            "Gói đầy đủ: gồm cả Đề học sinh (chỉ đề) và Đề giáo viên (kèm đáp án & đối chiếu câu gốc)"
            if mode == "all"
            else ("Gói chỉ đề thi học sinh" if mode in ["student", "exam_only"] else "Gói đề thi giáo viên kèm đáp án")
        )
        guide_text = (
            "HƯỚNG DẪN SỬ DỤNG BỘ ĐỀ THI ĐÃ XÁO\n"
            "===================================\n\n"
            f"Tài liệu gốc: {session['filename']}\n"
            f"Chế độ xuất: {mode_desc}\n"
            f"Số lượng mã đề: {len(session['variants'])}\n"
            f"Danh sách mã: {', '.join(session['variants'].keys())}\n\n"
            "Danh mục tệp đính kèm:\n"
            "- Thư mục De_Thi_Hoc_Sinh: Đề thi đã xáo sạch, không có đáp án, sẵn sàng in phát cho học sinh.\n"
            "- Thư mục De_Thi_Giao_Vien_Kem_Dap_An: Đề thi có chú thích vị trí câu gốc (ví dụ: Câu 1 [Gốc: Câu 17]) và kèm bảng đối chiếu ở cuối đề.\n"
            "- Dap_An_Tong_Hop.docx: Bảng đáp án dùng để chấm thi hoặc in ấn.\n"
            "- Bang_Anh_Xa.xlsx: Ma trận đối chiếu chi tiết giữa câu mới và câu gốc.\n\n"
            "Chúc quý Thầy Cô có một kỳ thi thành công!\n"
        )
        zip_file.writestr("Huong_Dan.txt", guide_text.encode("utf-8"))

    zip_buffer.seek(0)
    suffix = "_Hoc_Sinh" if mode in ["student", "exam_only"] else ("_Giao_Vien" if mode in ["teacher", "with_answers"] else "")
    out_filename = filename or f"{base_name}_Bo_De_Thi{suffix}.zip"
    if not out_filename.endswith(".zip"):
        out_filename += ".zip"

    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers=get_download_headers(out_filename),
    )


@router.get("/samples")
async def get_samples():
    """Lists preloaded real school exam samples available in the workspace."""
    sample_files = [
        {"name": "Tin học 7 - THCS Lê Hồng Phong (GK1)", "filename": "New_GK1 TIN 7-26-27-THUONG.docx", "type": "docx"},
        {"name": "Tin học 9 - THCS Lê Hồng Phong (GK1)", "filename": "New_GK1 TIN 9-26-27-THUONG.docx", "type": "docx"},
        {"name": "Tin học 7 (Bản PDF)", "filename": "New_GK1 TIN 7-26-27-THUONG.pdf", "type": "pdf"},
        {"name": "Tin học 9 (Bản PDF)", "filename": "New_GK1 TIN 9-26-27-THUONG.pdf", "type": "pdf"},
    ]
    return {"samples": sample_files}


@router.post("/load-sample/{filename}")
async def load_sample(filename: str):
    """Loads a preloaded sample file directly without manual upload."""
    if not os.path.exists(filename):
        raise HTTPException(status_code=404, detail="File mẫu không tồn tại.")

    with open(filename, "rb") as f:
        contents = f.read()

    ext = os.path.splitext(filename)[1].lower()
    session_id = str(uuid.uuid4())

    if ext == ".docx":
        parser = DocxParser(contents, filename)
        analysis = parser.analyze()
        SESSION_CACHE[session_id] = {
            "file_bytes": contents,
            "filename": filename,
            "file_type": "docx",
            "analysis": analysis,
            "variants": {},
            "excel_bytes": None,
            "answer_docx_bytes": None,
        }
        return {
            "session_id": session_id,
            "analysis": analysis.model_dump(),
            "thumbnails": [],
        }
    elif ext == ".pdf":
        inspector = PdfInspector(contents, filename)
        analysis = inspector.inspect()
        thumbnails = inspector.render_page_thumbnails(max_pages=4)
        SESSION_CACHE[session_id] = {
            "file_bytes": contents,
            "filename": filename,
            "file_type": "pdf",
            "analysis": analysis,
            "variants": {},
            "excel_bytes": None,
            "answer_docx_bytes": None,
        }
        return {
            "session_id": session_id,
            "analysis": analysis.model_dump(),
            "thumbnails": thumbnails,
        }
