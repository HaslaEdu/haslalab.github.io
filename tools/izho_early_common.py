"""Fill only unambiguous repeated IZhO archive labels; prose is translated manually."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABELS = {
    "THEORETICAL COMPETITION": "이론시험", "Theoretical Competition": "이론시험",
    "SOLUTIONS FOR THEORETICAL COMPETITION": "이론시험 해설",
    "SOLUTIONS TO THE PROBLEMS OF THEORETICAL COMPETITION": "이론시험 문제 해설",
    "SOLUTIONS OF PROBLEMS OF THEORETICAL TOUR": "이론시험 문제 해설",
    "Marking scheme": "채점 기준", "Grading scheme": "채점 기준", "Grading Scheme": "채점 기준",
    "Description": "내용", "Content": "내용", "Points": "배점", "points": "배점",
    "Total": "합계", "total": "합계", "Sum": "합계", "Correct answer": "정답",
    "where": "여기서", "whence": "따라서", "therefore,": "따라서", "therefore": "따라서",
    "and": "및", "or": "또는", "with": "단,", "In this case": "이 경우",
    "Consequently,": "따라서", "Consequently": "따라서", "thus": "따라서", "Thus": "따라서",
    "Numerical value": "수치", "Correct numerical value": "올바른 수치", "Correct formula": "올바른 식",
}


def convert(source, year, kind):
    if source in LABELS:
        return LABELS[source]
    if "International Zhautykov Olympiad" in source and ("Theoretical" in source or "Almaty" in source):
        return f"제{year - 2004}회 국제 자우티코프 올림피아드 / 이론시험" + (" 해설" if kind == "TS" else "")
    if re.fullmatch(r"January\s+\d+,?\s+20\d\d", source):
        day = re.search(r"January\s+(\d+)", source)[1]
        return f"{year}년 1월 {day}일"
    if re.fullmatch(r"(?:Fig\.?|Figure)\s*\d+[a-z]?(?:\s+(?:Fig\.?|Figure)\s*\d+[a-z]?)*", source):
        return re.sub(r"Fig(?:ure)?\.?", "그림", source)
    if re.fullmatch(r"(?:Problem|Theoretical Question|Question)\s*\d+[A-CА-В]?(?:\.?)\s*(?:\(\d+(?:\.\d+)?\s*points?\))?", source, re.I):
        return re.sub(r"points?", "점", re.sub(r"Problem|Theoretical Question|Question", "문제", source, flags=re.I), flags=re.I)
    if re.fullmatch(r"(?:Formula|Equation|Eq\.?)\s*[\d().\s\[\],;=+−–-]*", source, re.I):
        return re.sub(r"^(?:Formula|Equation|Eq\.?)", "식", source, flags=re.I)
    if re.fullmatch(r"(?:Total|Sum)\s*[\d.,\s\[\]]*", source, re.I):
        return re.sub(r"^(?:Total|Sum)", "합계", source, flags=re.I)
    if re.fullmatch(r"\d+[A-CА-В]\s*\(\d+(?:[.,]\d+)?\s*points?\)", source, re.I):
        return re.sub(r"points?", "점", source, flags=re.I)
    return None


def main():
    for year in range(2010, 2018):
        for kind in ("T", "TS"):
            path = ROOT / "tools/ko/izho" / str(year) / kind / "translation.json"
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            for entry in data["entries"]:
                if not entry["ko"]:
                    entry["ko"] = convert(entry["source"], year, kind) or ""
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            missing = [entry for entry in data["entries"] if not entry["ko"]]
            print(year, kind, "remaining", len(missing), "of", len(data["entries"]))


if __name__ == "__main__":
    main()
