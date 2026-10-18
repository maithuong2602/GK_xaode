"""
Pydantic models and data structures for the Exam Shuffler Engine.
"""
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"  # Loại 1 - Trắc nghiệm 4 lựa chọn (A, B, C, D)
    TRUE_FALSE = "TRUE_FALSE"            # Loại 2 - Đúng / Sai (ý a, b, c, d hoặc câu nhận định)
    ESSAY = "ESSAY"                      # Loại 3 - Tự luận


class OptionLayoutType(str, Enum):
    PARAGRAPHS_4 = "PARAGRAPHS_4"        # 4 đoạn văn riêng biệt (A., B., C., D.)
    TABLE_2X2 = "TABLE_2X2"              # Bảng 2 hàng x 2 cột
    TABLE_1X4 = "TABLE_1X4"              # Bảng 1 hàng x 4 cột
    TABLE_4X1 = "TABLE_4X1"              # Bảng 4 hàng x 1 cột
    NONE = "NONE"                        # Không có phương án (Tự luận hoặc Đúng/Sai dạng câu)


class OptionItem(BaseModel):
    letter: str                          # 'A', 'B', 'C', 'D' hoặc 'a', 'b', 'c', 'd'
    text: str                            # Nội dung phương án không kèm nhãn
    full_text: str                       # Toàn văn phương án kèm nhãn
    original_index: int                  # 0, 1, 2, 3


class QuestionBlockData(BaseModel):
    id: str                              # Mã định danh (vd: 'q_1', 'q_2')
    original_number: int                 # Số thứ tự gốc (vd: 1, 2... 30)
    lead_text: str                       # Nội dung dòng dẫn câu hỏi
    full_preview: str                    # Nội dung text đầy đủ để preview
    question_type: QuestionType          # MULTIPLE_CHOICE | TRUE_FALSE | ESSAY
    option_layout: OptionLayoutType      # Kiểu bố trí phương án
    options: List[OptionItem] = []       # Danh sách phương án
    correct_answer: str = ""             # Đáp án đúng ('A', 'B', 'C', 'D', 'Đúng', 'Sai')
    is_locked: bool = False              # Khóa vị trí (không xáo)
    shuffle_options: bool = True         # Có cho phép xáo phương án của câu này không
    section_id: int = 1                  # ID của Phần chứa câu này (1: Phần I, 2: Phần II...)
    has_images: bool = False             # Có hình ảnh minh họa
    has_tables: bool = False             # Có bảng dữ liệu/minh họa
    has_equations: bool = False          # Có công thức toán học
    start_body_idx: int = 0              # Vị trí bắt đầu trong body XML
    end_body_idx: int = 0                # Vị trí kết thúc trong body XML


class SectionData(BaseModel):
    id: int                              # 1, 2, 3...
    title: str                           # Ví dụ: "PHẦN 1. TRẮC NGHIỆM (7,0 điểm)"
    heading_body_idx: int                # Vị trí phần tử tiêu đề trong body
    question_ids: List[str] = []         # Danh sách ID câu hỏi thuộc phần này
    shuffle_questions: bool = True       # Cho phép xáo thứ tự câu trong phần này
    shuffle_options: bool = True         # Cho phép xáo phương án trong phần này


class DocumentAnalysisResult(BaseModel):
    filename: str
    file_type: str                       # 'docx' hoặc 'pdf'
    is_scanned_pdf: bool = False         # Nếu là PDF scan ảnh
    pdf_warning: Optional[str] = None    # Cảnh báo an toàn định dạng PDF
    total_questions: int = 0
    num_mc_questions: int = 0
    num_tf_questions: int = 0
    num_essay_questions: int = 0
    sections: List[SectionData] = []
    questions: List[QuestionBlockData] = []
    detected_answers: Dict[int, str] = {}
    has_student_answer_table: bool = False
    has_grading_guide: bool = False
    code_placeholder_found: bool = False
    code_placeholder_text: Optional[str] = None
    exam_end_body_idx: int = 0


class SectionConfig(BaseModel):
    shuffle_questions: bool = True
    shuffle_options: bool = True


class ShuffleRequestConfig(BaseModel):
    num_variants: int = Field(default=4, ge=1, le=20)
    start_code: int = Field(default=101, ge=1, le=9999)
    custom_codes: Optional[List[str]] = None
    seed: Optional[int] = None
    section_configs: Dict[int, SectionConfig] = {}
    locked_question_ids: List[str] = []
    custom_answers: Dict[str, str] = {}   # question_id -> new correct answer
    question_type_overrides: Dict[str, QuestionType] = {}
    code_placement: str = "header_banner" # 'header_banner', 'replace_existing', 'top_center', 'none'
    keep_with_next: bool = False         # Mặc định tắt để dàn trang tự nhiên, tránh khoảng trắng thừa cuối trang
    include_answers_in_exam: bool = False # Mặc định xuất bản học sinh hoặc bản kèm đáp án


class MappingItem(BaseModel):
    new_number: int
    original_number: int
    original_answer: str
    new_answer: str
    lead_preview: str
    question_type: str


class IntegrityReport(BaseModel):
    is_valid: bool
    total_original_questions: int
    total_variant_questions: int
    no_missing_questions: bool
    no_duplicate_questions: bool
    no_missing_options: bool
    answers_verified: bool
    messages: List[str] = []
    warnings: List[str] = []


class VariantPreviewData(BaseModel):
    variant_code: str
    seed: int
    question_mappings: List[MappingItem]
    integrity: IntegrityReport
    questions_preview: List[Dict[str, Any]]
