"""
Answer Key Manager Module.
Parses, normalizes, and validates answer strings from various teacher input formats.
"""
import re
from typing import Dict, List, Tuple


class AnswerManager:
    """Handles answer string normalization and conversion."""

    @staticmethod
    def parse_pasted_answer_string(raw_text: str, total_expected: int = 0) -> Dict[int, str]:
        """Parses raw text pasted by teachers in various popular formats:
        - 'C A D B B C A...'
        - '1C 2A 3D 4B...'
        - '1.C 2.A 3.D 4.B...'
        - '1-C, 2-A, 3-D...'
        - '1: C, 2: A, 3: D...'
        - Newlines:
          1. A
          2. B
        """
        raw = raw_text.strip()
        result: Dict[int, str] = {}
        if not raw:
            return result

        # Format 1: Explicit numbered pairs like '1C', '1.C', '1: C', '1 - C', 'Câu 1: C'
        numbered_pattern = re.compile(
            r'(?:Câu\s*)?([0-9]{1,3})\s*[\s.:)-]\s*([A-Da-d]|Đúng|Sai|True|False)',
            re.IGNORECASE
        )
        matches = numbered_pattern.findall(raw)
        if len(matches) >= 3:
            for q_str, a_str in matches:
                ans = a_str.upper() if a_str.upper() in ['A', 'B', 'C', 'D'] else a_str.title()
                result[int(q_str)] = ans
            return result

        # Format 2: Shorthand like '1C 2A 3B 4D' without separator
        short_pattern = re.compile(r'([0-9]{1,3})([A-Da-d])')
        matches_short = short_pattern.findall(raw)
        if len(matches_short) >= 3:
            for q_str, a_str in matches_short:
                result[int(q_str)] = a_str.upper()
            return result

        # Format 3: Raw sequence of letters like 'C A D B B C A' or 'C, A, D, B...'
        tokens = re.split(r'[\s,;\-]+', raw)
        valid_letters = [t.upper() for t in tokens if t.upper() in ['A', 'B', 'C', 'D', 'ĐÚNG', 'SAI']]
        if valid_letters:
            for i, letter in enumerate(valid_letters, start=1):
                ans = 'Đúng' if letter == 'ĐÚNG' else ('Sai' if letter == 'SAI' else letter)
                result[i] = ans
            return result

        return result
