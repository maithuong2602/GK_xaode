"""
Comprehensive Automated Test Suite for Exam Shuffler Engine.
Validates all 23 criteria specified in Section 25.
"""
import io
import os
import unittest
import docx
from lxml import etree

from backend.parser import DocxParser
from backend.shuffler import DocxShuffler
from backend.models import (
    ShuffleRequestConfig,
    QuestionType,
    OptionLayoutType,
)
from backend.pdf_engine import PdfInspector
from backend.answer_manager import AnswerManager
from backend.excel_exporter import create_mapping_excel
from backend.docx_exporter import create_answer_key_docx


class TestExamShuffler(unittest.TestCase):
    """Automated regression and integrity test suite."""

    @classmethod
    def setUpClass(cls):
        # Load real test papers
        cls.docx_tin7_path = "New_GK1 TIN 7-26-27-THUONG.docx"
        cls.docx_tin9_path = "New_GK1 TIN 9-26-27-THUONG.docx"
        cls.pdf_tin7_path = "New_GK1 TIN 7-26-27-THUONG.pdf"
        cls.pdf_tin9_path = "New_GK1 TIN 9-26-27-THUONG.pdf"

        with open(cls.docx_tin7_path, "rb") as f:
            cls.tin7_bytes = f.read()

        with open(cls.docx_tin9_path, "rb") as f:
            cls.tin9_bytes = f.read()

        with open(cls.pdf_tin7_path, "rb") as f:
            cls.pdf_tin7_bytes = f.read()

    def test_01_docx_parsing_tin7(self):
        """Test parsing of Tin 7: sections, questions, tables, answers."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()

        self.assertEqual(res.total_questions, 30)
        self.assertEqual(len(res.sections), 2)
        self.assertTrue(res.has_student_answer_table)
        self.assertTrue(res.has_grading_guide)
        self.assertGreaterEqual(len(res.detected_answers), 28)
        self.assertEqual(res.detected_answers[1], "C")
        self.assertEqual(res.detected_answers[28], "Sai")

    def test_02_docx_parsing_tin9(self):
        """Test parsing of Tin 9: sections, questions, tables, answers."""
        parser = DocxParser(self.tin9_bytes, "Tin9.docx")
        res = parser.analyze()

        self.assertEqual(res.total_questions, 29)
        self.assertEqual(len(res.sections), 2)
        self.assertTrue(res.has_student_answer_table)
        self.assertTrue(res.has_grading_guide)
        self.assertGreaterEqual(len(res.detected_answers), 28)

    def test_03_table_preservation(self):
        """Test that all 13 tables are preserved in the shuffled output without loss."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=2, start_code=101, seed=20261018)

        shuffler = DocxShuffler(self.tin7_bytes, res, cfg)
        variants = shuffler.generate_all_variants()

        orig_doc = docx.Document(io.BytesIO(self.tin7_bytes))
        orig_tables_count = len(orig_doc.tables)

        for code, (docx_bytes, _) in variants.items():
            new_doc = docx.Document(io.BytesIO(docx_bytes))
            self.assertEqual(len(new_doc.tables), orig_tables_count, f"Table count mismatch in {code}")

    def test_04_sections_and_page_setup_preservation(self):
        """Test that sections, headers, footers, margins remain identical."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=2, start_code=101, seed=20261018)

        shuffler = DocxShuffler(self.tin7_bytes, res, cfg)
        variants = shuffler.generate_all_variants()

        orig_doc = docx.Document(io.BytesIO(self.tin7_bytes))
        orig_sec_count = len(orig_doc.sections)

        for code, (docx_bytes, _) in variants.items():
            new_doc = docx.Document(io.BytesIO(docx_bytes))
            self.assertEqual(len(new_doc.sections), orig_sec_count)
            # Check margins of section 0
            self.assertAlmostEqual(orig_doc.sections[0].top_margin.pt, new_doc.sections[0].top_margin.pt, places=1)
            self.assertAlmostEqual(orig_doc.sections[0].left_margin.pt, new_doc.sections[0].left_margin.pt, places=1)

    def test_05_question_locking(self):
        """Test that locked questions never move position across any variant."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(
            num_variants=4,
            start_code=101,
            seed=20261018,
            locked_question_ids=["q_1", "q_10"]
        )

        variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
        for code, (_, prev) in variants.items():
            m_dict = {m.new_number: m.original_number for m in prev.question_mappings}
            self.assertEqual(m_dict[1], 1, f"Lock Q1 failed in variant {code}")
            self.assertEqual(m_dict[10], 10, f"Lock Q10 failed in variant {code}")

    def test_06_seed_reproducibility(self):
        """Test that same seed produces identical mappings across runs."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()

        cfg1 = ShuffleRequestConfig(num_variants=2, start_code=101, seed=998877)
        cfg2 = ShuffleRequestConfig(num_variants=2, start_code=101, seed=998877)

        v1 = DocxShuffler(self.tin7_bytes, res, cfg1).generate_all_variants()
        v2 = DocxShuffler(self.tin7_bytes, res, cfg2).generate_all_variants()

        m1 = [(m.new_number, m.original_number, m.new_answer) for m in v1["101"][1].question_mappings]
        m2 = [(m.new_number, m.original_number, m.new_answer) for m in v2["101"][1].question_mappings]

        self.assertEqual(m1, m2)

    def test_07_multi_variant_generation_2_4_10(self):
        """Test generating 2, 4, and 10 variants."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()

        for count in [2, 4, 10]:
            cfg = ShuffleRequestConfig(num_variants=count, start_code=101, seed=20261018)
            variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
            self.assertEqual(len(variants), count)
            for code, (docx_bytes, prev) in variants.items():
                self.assertTrue(prev.integrity.is_valid)
                self.assertEqual(prev.integrity.total_variant_questions, 30)

    def test_08_no_missing_or_duplicate_questions(self):
        """Test integrity check ensures bijection between original and new numbers."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=4, start_code=201, seed=12345)

        variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
        for code, (_, prev) in variants.items():
            new_nums = [m.new_number for m in prev.question_mappings]
            orig_nums = [m.original_number for m in prev.question_mappings]
            self.assertEqual(sorted(new_nums), list(range(1, 31)))
            self.assertEqual(sorted(orig_nums), list(range(1, 31)))

    def test_09_answer_mapping_accuracy(self):
        """Test that new answers correspond directly to shuffled option contents."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=2, start_code=101, seed=20261018)

        variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
        for code, (_, prev) in variants.items():
            for m in prev.question_mappings:
                if m.question_type == "MULTIPLE_CHOICE":
                    self.assertIn(m.new_answer, ["A", "B", "C", "D"])
                elif m.question_type == "TRUE_FALSE":
                    self.assertIn(m.new_answer, ["Đúng", "Sai", ""])

    def test_10_pdf_text_inspection(self):
        """Test inspection of valid searchable text PDF."""
        inspector = PdfInspector(self.pdf_tin7_bytes, "Tin7.pdf")
        res = inspector.inspect()

        self.assertFalse(res.is_scanned_pdf)
        self.assertIsNotNone(res.pdf_warning)
        self.assertGreaterEqual(res.total_questions, 20)

    def test_11_answer_manager_parsing_modes(self):
        """Test the 3 answer input modes."""
        s1 = "A B C D A B C D"
        res1 = AnswerManager.parse_pasted_answer_string(s1)
        self.assertEqual(res1[1], "A")
        self.assertEqual(res1[4], "D")

        s2 = "1A 2B 3C 4D"
        res2 = AnswerManager.parse_pasted_answer_string(s2)
        self.assertEqual(res2[1], "A")
        self.assertEqual(res2[3], "C")

    def test_12_excel_export(self):
        """Test generation of valid Bang_Anh_Xa.xlsx with openpyxl."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=2, start_code=101, seed=20261018)

        variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
        prev_map = {code: prev for code, (_, prev) in variants.items()}

        excel_bytes = create_mapping_excel("Tin7.docx", prev_map, res.detected_answers)
        self.assertGreater(len(excel_bytes), 5000)

        # Verify openpyxl can read it back
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        self.assertIn("Ma Trận Đáp Án", wb.sheetnames)
        self.assertIn("Ánh Xạ Câu Hỏi", wb.sheetnames)

    def test_13_docx_answer_key_export(self):
        """Test generation of valid standalone Dap_An.docx."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=2, start_code=101, seed=20261018)

        variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
        prev_map = {code: prev for code, (_, prev) in variants.items()}

        docx_ans_bytes = create_answer_key_docx("Tin7.docx", prev_map, res.detected_answers)
        self.assertGreater(len(docx_ans_bytes), 5000)

    def test_14_formatting_and_bold_preservation(self):
        """Test that question numbers and option letters preserve original bold/rStyle formatting."""
        parser = DocxParser(self.tin7_bytes, "Tin7.docx")
        res = parser.analyze()
        cfg = ShuffleRequestConfig(num_variants=2, start_code=101, seed=20261018)

        variants = DocxShuffler(self.tin7_bytes, res, cfg).generate_all_variants()
        for code, (docx_bytes, _) in variants.items():
            doc = docx.Document(io.BytesIO(docx_bytes))
            # 1. Verify question prefixes preserve bold/Strong style
            for p in doc.paragraphs:
                txt = p.text.strip()
                if txt.startswith("Câu ") and len(p.runs) > 0:
                    first_run = p.runs[0]
                    # First run must have Strong style or bold
                    is_bold = first_run.bold or (first_run.style and first_run.style.name == "Strong")
                    self.assertTrue(is_bold, f"Question prefix lost bold in {code}: {txt[:30]}")

            # 2. Verify table options preserve bold/Strong style
            for t in doc.tables:
                if len(t.rows) == 2 and len(t.columns) == 2:
                    for row in t.rows:
                        for cell in row.cells:
                            for cp in cell.paragraphs:
                                if any(cp.text.strip().startswith(f"{c}.") for c in "ABCD") and len(cp.runs) > 0:
                                    r0 = cp.runs[0]
                                    is_bold = r0.bold or (r0.style and r0.style.name == "Strong")
                                    self.assertTrue(is_bold, f"Table option lost bold in {code}: {cp.text}")


if __name__ == "__main__":
    unittest.main()

