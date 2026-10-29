"""Question numbers with an unresolved source/key discrepancy, without spoilers."""
import json
import re
from pathlib import Path

def review_questions():
    result = {}
    folder = Path(__file__).resolve().parent / 'kphe_solutions'
    for path in sorted(folder.glob('*.json')):
        match = re.match(r'(\d{4}-\d)-', path.name)
        if not match:
            continue
        for part, rows in json.loads(path.read_text(encoding='utf-8')).items():
            if not isinstance(rows, list):
                continue
            numbers = [row['number'] for row in rows if row.get('status') == 'needs_review'
                       or ('computed_answer' in row and row['computed_answer'] != row.get('answer'))]
            if numbers:
                result.setdefault(match[1], {})[part] = sorted(numbers)
    return result
