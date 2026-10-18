"""
PDF Analysis and Safety Inspection Module using PyMuPDF.
Distinguishes searchable text PDFs from scanned image PDFs,
evaluates layout complexity, and generates page preview thumbnails.
"""
import io
import re
import base64
from typing import Dict, List, Tuple, Optional, Any
import pymupdf

from backend.models import (
    DocumentAnalysisResult,
    SectionData,
    QuestionBlockData,
    QuestionType,
    OptionLayoutType,
    OptionItem,
)

RE_QUESTION = re.compile(
    r'^(?:Câu|CÂU|Question|Bài)\s*([0-9]{1,3})\s*(?:\(([0-9,.]+)\s*(?:điểm|đ)\))?[\s.:)-]\s*(.*)',
    re.IGNORECASE
)
RE_SECTION = re.compile(
    r'^(?:PHẦN|Phần|PART)\s*([0-9IVXLCDM]+|[A-Z])[\s.:\-]?\s*(.*)',
    re.IGNORECASE
)
RE_OPT_LETTER = re.compile(r'^([A-D])[\s.:)-]\s*(.*)', re.IGNORECASE)


class PdfInspector:
    """Inspects PDF files for text layer, scanned pages, layout safety, and question recognition."""

    def __init__(self, pdf_bytes: bytes, filename: str = "document.pdf"):
        self.pdf_bytes = pdf_bytes
        self.filename = filename
        self.doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")

    def inspect(self) -> DocumentAnalysisResult:
        """Analyzes the PDF document and returns safety assessment and question structure."""
        num_pages = len(self.doc)
        total_text_len = 0
        total_images = 0
        pages_text: List[str] = []

        for p_idx in range(num_pages):
            page = self.doc[p_idx]
            txt = page.get_text()
            pages_text.append(txt)
            total_text_len += len(txt.strip())
            total_images += len(page.get_images())

        avg_text_per_page = total_text_len / max(1, num_pages)

        # Scanned PDF check: minimal text + presence of images
        is_scanned = (avg_text_per_page < 60) and (total_images > 0 or total_text_len == 0)

        if is_scanned:
            pdf_warning = (
                "⚠️ ĐÂY LÀ FILE PDF DẠNG QUÉT/ẢNH (SCANNED PDF).\n"
                "Tài liệu không có lớp văn bản thực tế để định vị và tráo đổi câu hỏi mà vẫn giữ nguyên bố cục. "
                "Hệ thống khuyến nghị giáo viên sử dụng file Word (.docx) gốc để đảm bảo chất lượng tài liệu cao nhất."
            )
            return DocumentAnalysisResult(
                filename=self.filename,
                file_type="pdf",
                is_scanned_pdf=True,
                pdf_warning=pdf_warning,
                total_questions=0,
                num_mc_questions=0,
                num_tf_questions=0,
                num_essay_questions=0,
                sections=[],
                questions=[],
                detected_answers={},
                has_student_answer_table=False,
                has_grading_guide=False,
                code_placeholder_found=False,
                code_placeholder_text=None,
            )

        # Parse questions from text
        sections, questions, detected_answers = self._parse_questions_from_text(pages_text)

        pdf_warning = (
            "ℹ️ LƯU Ý KHI SỬ DỤNG TỆP PDF:\n"
            "PDF là định dạng tài liệu cố định (fixed-layout). Việc xáo đề trực tiếp từ PDF có thể làm lệch vị trí dòng hoặc bảng biểu. "
            "Nếu có sẵn file Word (.docx), khuyến khích tải file Word lên để giữ trọn vẹn 100% định dạng ban đầu."
        )

        num_mc = sum(1 for q in questions if q.question_type == QuestionType.MULTIPLE_CHOICE)
        num_tf = sum(1 for q in questions if q.question_type == QuestionType.TRUE_FALSE)
        num_essay = sum(1 for q in questions if q.question_type == QuestionType.ESSAY)

        return DocumentAnalysisResult(
            filename=self.filename,
            file_type="pdf",
            is_scanned_pdf=False,
            pdf_warning=pdf_warning,
            total_questions=len(questions),
            num_mc_questions=num_mc,
            num_tf_questions=num_tf,
            num_essay_questions=num_essay,
            sections=sections,
            questions=questions,
            detected_answers=detected_answers,
            has_student_answer_table=False,
            has_grading_guide=bool(detected_answers),
            code_placeholder_found=False,
            code_placeholder_text=None,
        )

    def _parse_questions_from_text(
        self, pages_text: List[str]
    ) -> Tuple[List[SectionData], List[QuestionBlockData], Dict[int, str]]:
        full_text = "\n".join(pages_text)
        lines = [line.strip() for line in full_text.splitlines() if line.strip()]

        sections: List[SectionData] = []
        questions: List[QuestionBlockData] = []
        answers: Dict[int, str] = {}

        current_sec = SectionData(
            id=1,
            title="ĐỀ THI TỔNG HỢP",
            heading_body_idx=0,
            question_ids=[],
            shuffle_questions=True,
            shuffle_options=True,
        )
        sections.append(current_sec)

        # Iterate lines to locate sections and questions
        line_items = []
        for l_idx, line in enumerate(lines):
            sec_m = RE_SECTION.match(line)
            if sec_m:
                line_items.append((l_idx, 'section', line))
                continue
            q_m = RE_QUESTION.match(line)
            if q_m:
                q_num = int(q_m.group(1))
                line_items.append((l_idx, 'question', (q_num, line)))

        for i, (l_idx, itype, data) in enumerate(line_items):
            if itype == 'section':
                current_sec = SectionData(
                    id=len(sections) + 1,
                    title=data,
                    heading_body_idx=l_idx,
                    question_ids=[],
                    shuffle_questions='tự luận' not in data.lower(),
                    shuffle_options='đúng' not in data.lower() and 'tự luận' not in data.lower(),
                )
                sections.append(current_sec)
            elif itype == 'question':
                q_num, lead_line = data
                next_l_idx = line_items[i + 1][0] if i + 1 < len(line_items) else len(lines)
                q_lines = lines[l_idx:next_l_idx]

                # Check options in q_lines
                options: List[OptionItem] = []
                letters = ['A', 'B', 'C', 'D']
                for ql in q_lines[1:]:
                    m = RE_OPT_LETTER.match(ql)
                    if m:
                        let = m.group(1).upper()
                        options.append(OptionItem(
                            letter=let,
                            text=m.group(2).strip(),
                            full_text=ql,
                            original_index=letters.index(let) if let in letters else len(options),
                        ))

                q_type = QuestionType.MULTIPLE_CHOICE if len(options) >= 3 else QuestionType.ESSAY
                if len(options) == 0 and any(kw in lead_line.lower() for kw in ['đúng', 'sai']):
                    q_type = QuestionType.TRUE_FALSE

                q_data = QuestionBlockData(
                    id=f"q_{q_num}",
                    original_number=q_num,
                    lead_text=lead_line,
                    full_preview="\n".join(q_lines),
                    question_type=q_type,
                    option_layout=OptionLayoutType.PARAGRAPHS_4 if len(options) >= 3 else OptionLayoutType.NONE,
                    options=options,
                    correct_answer="",
                    is_locked=False,
                    shuffle_options=(q_type == QuestionType.MULTIPLE_CHOICE),
                    section_id=current_sec.id,
                    has_images=False,
                    has_tables=False,
                    has_equations=False,
                    start_body_idx=l_idx,
                    end_body_idx=next_l_idx,
                )
                questions.append(q_data)
                current_sec.question_ids.append(q_data.id)

        if len(sections) > 1 and len(sections[0].question_ids) == 0:
            sections = sections[1:]

        # Normalize section IDs
        for new_id, s in enumerate(sections, start=1):
            s.id = new_id

        return sections, questions, answers

    def render_page_thumbnails(self, max_pages: int = 4, dpi: int = 90) -> List[str]:
        """Renders page previews as base64 PNG images for visual preview in UI."""
        thumbnails = []
        for p_idx in range(min(len(self.doc), max_pages)):
            page = self.doc[p_idx]
            pix = page.get_pixmap(dpi=dpi)
            b64_data = base64.b64encode(pix.tobytes("png")).decode("ascii")
            thumbnails.append(f"data:image/png;base64,{b64_data}")
        return thumbnails
