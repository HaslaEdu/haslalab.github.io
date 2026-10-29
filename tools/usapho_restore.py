#!/usr/bin/env python3
"""Restore USAPhO Korean Drive translations to the official exam's page layout.

    python tools/usapho_restore.py --audit-only
    python tools/usapho_restore.py

Input paths come from tools/usapho_restore_sources.json. The original page
geometry, page furniture and question boundaries are the template. Korean text,
mathematics and illustrations are copied as vector PDF content, not OCR'd.
The 2021 USAPhO+ appendix and the 2022 camp examination are separate exams and
are deliberately excluded from the USAPhO semifinal output.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pymupdf as fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "tmp/source-audit/usapho-design"
OUT = ROOT / "pdfx/usapho"
AUDIT = ROOT / "tools/usapho_restore_sources.json"
QSTART = re.compile(r"^(?:\(\d+(?:점)?\)\s*)?(?:(?:Question|Problem|문제)\s*([AB][1-4])(?:[.:\s]|$)|([AB][1-4])\.)", re.I)
SELECTED = {2021: (0, 9), 2022: (7, 13)}
FONT = ROOT / "tools/ko/fonts/NotoSansKR-Regular.ttf"
SCAN_OCR = ROOT / "tools/usapho_scan_positions.json"
_SCAN_CACHE = {}


def korean_box(page, rect, text, size=10, minimum=7.8):
    """Keep the source's prose region; wrap translated administrative text."""
    page.insert_font(fontname="NotoKR", fontfile=str(FONT))
    page.draw_rect(rect + (-4, -1, 4, 1), color=None, fill=(1, 1, 1), overlay=True)
    for font_size in [size - .2 * n for n in range(int((size - minimum) / .2) + 2)]:
        probe = fitz.open()
        check = probe.new_page(width=page.rect.width, height=page.rect.height)
        check.insert_font(fontname="NotoKR", fontfile=str(FONT))
        trial = check.new_shape()
        room = trial.insert_textbox(rect, text, fontsize=font_size, fontname="NotoKR", lineheight=1.35)
        if room < 0:
            probe.close()
            continue
        trial.commit()
        bounds = [line["rect"] for line in lines(check)]
        fits = bounds and max(r.y1 for r in bounds) <= rect.y1 - 1 and max(r.x1 for r in bounds) <= rect.x1 + .5
        probe.close()
        if not fits:
            continue
        shape = page.new_shape()
        spare = shape.insert_textbox(rect, text, fontsize=font_size, fontname="NotoKR", lineheight=1.35)
        if spare >= 0:
            shape.commit()
            return font_size
    raise ValueError(f"Administrative translation does not fit on page {page.number + 1}")


def source_date(text):
    match = re.search(r"(March|April)\s+(\d+)(?:st|nd|rd|th)?(?:,?\s*(20\d\d))?", text)
    if not match:
        return text
    return ((match[3] + "년 ") if match[3] else "") + {"March": "3", "April": "4"}[match[1]] + "월 " + match[2] + "일"


def page_ranges(text):
    text = re.sub(r"\s+", " ", text)
    text = text.replace("the cover sheet", "표지").replace("the instructions", "안내문")
    text = text.replace("Part A questions", "Part A 문제").replace("Part B questions", "Part B 문제")
    text = re.sub(r"pages?\s+([\d–-]+)", r"\1쪽", text)
    return text.replace("and ", "및 ").replace("the ", "")


def proctor_bullet(text):
    """Translate every published proctor bullet, keeping dates/page ranges."""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.split(r"We acknowledge|Copyright", text)[0].strip()
    if text.startswith("This examination consists of three"):
        return "이 시험은 세 부분으로 구성됩니다."
    if text.startswith(("This examination consists of two", "This examination has two")):
        if "three questions" in text:
            return "이 시험은 두 부분으로 구성됩니다. Part A와 Part B는 각각 3문항이며, 각 부분의 제한 시간은 90분입니다."
        if "four questions" in text:
            return "이 시험은 두 부분으로 구성됩니다. Part A는 4문항, Part B는 2문항이며, 각 부분의 제한 시간은 90분입니다."
        return "이 시험은 두 부분으로 구성됩니다."
    if text.startswith("Part A has"):
        return "Part A는 4문항이며 제한 시간은 90분입니다."
    if text.startswith("Part B has"):
        return "Part B는 2문항이며 제한 시간은 90분입니다."
    if text.startswith("Part C has"):
        return "Part C는 1문항이며 제한 시간은 20분입니다. Part C의 답안은 대표 선발에 사용하지 않고 미국광학회의 특별상 심사에 사용합니다."
    if text.startswith("The first page that follows"):
        return "다음 첫 페이지는 표지입니다. 응시자는 시험의 모든 부분에서 표지를 가지고 있을 수 있습니다."
    if text.startswith(("The three parts are then", "The parts are then")):
        return "각 부분은 페이지 머리말 가운데에 표시됩니다. 응시자는 한 번에 한 부분만 풀어야 하며, 시간이 남아도 다른 부분을 풀 수 없습니다."
    if text.startswith("Allow 90 minutes to complete Part A"):
        return "Part A에 90분을 주십시오. 이 시간에는 Part B" + ("나 Part C" if "or Part C" in text else "") + "를 보게 해서는 안 됩니다. Part A 답안을 회수한 다음 Part B를 시작하게 하십시오. Part A와 B 사이에는 10~15분의 휴식 시간을 허용합니다."
    if text.startswith("Allow 90 minutes to complete Part B"):
        if "Part C" in text:
            return "Part B에 90분을 주십시오. Part C를 보거나 Part A로 돌아가게 해서는 안 됩니다. Part B 답안을 회수한 다음 Part C를 시작하게 하십시오. Part B와 C 사이에는 10~15분의 휴식 시간을 허용합니다."
        return "Part B에 90분을 주십시오. Part A로 돌아가게 해서는 안 됩니다."
    if text.startswith("Allow 20 minutes"):
        return "Part C에 20분을 주십시오. 이 부분은 선택 사항이며 점수는 미국 대표 선발에 사용하지 않습니다. Part A나 B로 돌아갈 수 없습니다."
    if text.startswith("Ideally the test supervisor"):
        pieces = re.findall(r"(?:the cover sheet|Part [ABC])\s*\(pages? [\d–-]+\)", text)
        result = "시험지를 " + ", ".join(page_ranges(x) for x in pieces) + "로 나누어 각각 따로 배부하는 것이 좋습니다. 응시자는 표지를 계속 가지고 있을 수 있습니다."
        if "answer sheets for" in text:
            match = re.search(r"answer sheets for.*?\(pages? ([\d–-]+)\)", text)
            result += " Part A 일부 문항의 답안지(" + match[1] + "쪽)도 따로 준비하십시오."
        if "single sided" in text:
            result += " 답안지는 반드시 단면으로 인쇄하십시오."
        return result
    if text.startswith("The supervisor must collect"):
        return "시험이 끝나면 표지를 포함한 모든 문제지와 응시자가 사용한 계산용 종이를 회수하십시오. 응시자는 문제지를 가져갈 수 없습니다. 문제지는 " + source_date(text) + " 이후에 돌려줄 수 있습니다."
    if text.startswith(("Examinees are allowed calculators", "Students are allowed calculators", "Students may bring calculators")):
        return "계산기는 사용할 수 있으나 기호 계산, 프로그래밍, 그래프 기능은 사용할 수 없습니다. 계산기를 공유할 수 없으며, 데이터와 프로그램을 메모리에서 지워야 합니다. 시험 중이나 시험지가 있는 동안 휴대전화 및 기타 전자 기기를 사용할 수 없습니다. 표, 책, 공식 모음 등 외부 참고자료도 사용할 수 없습니다."
    if text.startswith("Please provide the examinees"):
        return "Part A를 위해 모눈종이를 제공하십시오." + (" 직선자나 자도 유용할 수 있습니다." if "straight edge" in text else "")
    if text.startswith("Divide the exam paper"):
        return "시험지를 안내문(2~3쪽), Part A(4~6쪽), Part B(8~10쪽), Part A 한 문항의 답안지(12~13쪽)로 나누십시오. 분리와 답안 스캔이 쉽도록 모두 단면으로 인쇄하십시오."
    if text.startswith("Provide students with the instructions"):
        return "응시자에게 안내문(2~3쪽)을 나누어 주십시오. 물리 상수 참고표가 있으므로 시험의 두 부분 모두에서 가지고 있을 수 있습니다."
    if text.startswith("Provide students with blank"):
        return "계산용 백지를 나누어 주십시오. 응시자는 자신의 종이를 가져와 사용할 수 없습니다."
    if text.startswith("Then provide students with Part A"):
        return "Part A와 해당 답안지를 나누어 주고 90분을 허용하십시오. 일찍 끝내더라도 이 시간에는 Part B를 주지 마십시오. 90분이 끝나면 Part A의 풀이, 답안지, 문제지를 모두 회수하십시오."
    if text.startswith("Students are allowed a 10"):
        return "Part A와 B 사이에 10~15분 휴식을 허용하십시오. 그 다음 Part B에 90분을 주십시오. Part A로 돌아가게 해서는 안 됩니다."
    if text.startswith("For each student, print out"):
        pieces = re.findall(r"(?:instructions|Part [AB] questions)\s*\(pages? [\d–-]+\)", text)
        result = "응시자마다 시험지와 답안지를 한 부씩 인쇄하십시오. 모두 단면으로 인쇄하고 스테이플러로 묶지 마십시오. 시험지를 " + ", ".join(page_ranges(x) for x in pieces) + "로 나누십시오."
        if "Page 11" in text:
            result += " 11쪽은 B3의 추가 답안지로 사용할 수 있는 그래프 용지입니다."
        return result
    if text.startswith("Begin by giving students"):
        return "먼저 안내문과 모든 답안지를 배부하십시오. 응시자가 안내를 읽고 답안지에 인적 사항을 쓰게 하십시오. 안내문은 두 부분 모두에서 소지할 수 있습니다. 시험 내내 사용할 계산용 백지도 제공하십시오."
    if text.startswith("To start the exam"):
        return ("서명한 정직 서약서를 회수한 뒤 " if "Honesty Policy" in text else "") + "시험을 시작할 때 Part A 문제를 나누어 주고 90분을 허용하십시오. 일찍 끝내더라도 Part B를 주지 마십시오. 90분이 끝나면 Part A 문제와 답안지를 회수하십시오."
    if text.startswith("Then give students a 5"):
        return "5~10분 휴식 후 Part B 문제를 나누어 주고 90분을 허용하십시오. Part A로 돌아가게 해서는 안 됩니다."
    if text.startswith("At the end of the exam"):
        result = "시험이 끝나면 문제지, 안내문, 답안지, 계산용 종이를 포함한 모든 종이를 회수하십시오. 응시자는 문제지를 가져갈 수 없습니다."
        if "Honor Code Certification" in text:
            result += " 명예 규약 확인서를 나누어 주고 서명한 확인서를 회수하십시오."
        if "after" in text:
            result += " 이 자료는 " + source_date(text) + " 이후에 돌려줄 수 있습니다."
        return result
    if text.startswith("After the exam, sort"):
        result = "시험 후 각 응시자의 답안지를 페이지 순서대로 정리하십시오. 빈 답안지도 포함하여 모든 답안지를 스캔하십시오."
        if "April 3rd" in text:
            result += " 4월 3일 이후에는 누구나 문제를 논의할 수 있습니다. 스캔본의 분실이나 판독 불가에 대비하여 4월 19일까지 모든 원본 답안지를 보관하십시오."
        return result
    raise ValueError("Untranslated proctor instruction: " + text)


def student_bullet(text):
    text = re.sub(r"\s+", " ", text).strip().replace("ﬁ", "fi").replace("ﬃ", "ffi")
    text = re.split(r"Possibly useful information|We acknowledge|Copyright", text)[0].strip()
    if text.startswith("This examination consists of two parts and six"):
        return "이 시험은 두 부분, 6문항으로 구성됩니다. 통상 Part A에 90분, 10~15분의 휴식 후 Part B에 90분이 주어집니다. 향후 USAPhO 시험을 연습하려면 이 지침을 따를 수 있습니다."
    if text.startswith("Ordinarily, you are allowed calculators"):
        return "통상 계산기는 허용되지만 기호 계산, 프로그래밍, 그래프 기능은 사용할 수 없습니다. 계산기를 공유할 수 없으며 메모리의 데이터와 프로그램을 지워야 합니다. 시험 중이나 시험지가 있는 동안 휴대전화, 스마트워치, PDA, 카메라를 사용할 수 없습니다. 표, 책, 공식 모음을 가져올 수 없습니다. 향후 USAPhO 시험을 연습하려면 이 지침을 따를 수 있습니다."
    if text.startswith(("Work Part A first", "Work on Part A first")):
        count = "3" if "three problems" in text else "4"
        return f"먼저 Part A를 푸십시오. {count}문항을 모두 푸는 시간은 90분입니다." + (" 각 문항은 25점입니다." if "25 points" in text else "") + " 이 시간에는 Part B" + ("나 C" if "or C" in text else "") + "를 보지 마십시오." + (" 배점이 같더라도 난이도는 같지 않을 수 있습니다." if "difficulty" in text else "")
    if text.startswith("After you have completed Part A"):
        return "Part A를 마친 후에는 휴식을 취할 수 있습니다." + (" Part B를 시작하면 Part A로 돌아갈 수 없으므로, 남은 시간에 Part A의 답안을 검토하는 것이 좋습니다." if "return" in text else "")
    if text.startswith(("Then work Part B", "Then work on Part B")):
        count, points = ("3", "25") if "three problems" in text else ("2", "50")
        return f"다음으로 Part B를 푸십시오. {count}문항을 모두 푸는 시간은 90분입니다." + (f" 각 문항은 {points}점입니다." if "points" in text else "") + " 이 시간에는 Part A" + ("나 C" if "or C" in text else "") + "를 보지 마십시오."
    if text.startswith("Show all your work"):
        return "모든 풀이 과정을 보이십시오. 부분 점수가 주어집니다." + (" 종이 뒷면에는 쓰지 마십시오. 채점받을 내용은 문제지가 아닌 답안지에 쓰십시오." if "back of" in text else "")
    if text.startswith("Show your work and reasoning"):
        return "풀이와 근거를 보이십시오. 근거를 명료하게 설명하면 부분 점수를 받을 수 있습니다. 종이 뒷면에는 쓰지 마십시오. 자세한 답안 작성 안내는 다음 쪽에 있습니다."
    if text.startswith("Start each question"):
        ids = ("학교 ID 번호, 이름" if "school ID" in text else "감독관 AAPT 번호, 학생 AAPT 번호, 이름" if "proctor" in text else "AAPT ID 번호, 이름" if "AAPT" in text else "이름")
        return "각 문제는 새 종이에서 시작하십시오. 각 페이지 오른쪽 위에 " + ids + ", 문제 번호 및 해당 문제의 페이지 번호/전체 페이지 수를 쓰십시오. 예: Doe, Jamie / A1 - 1/3."
    if text.startswith(("A hand-held calculator", "You may use a calculator")):
        return "휴대용 계산기를 사용할 수 있으나 메모리의 데이터와 프로그램을 지워야 합니다. 기호 계산, 프로그래밍, 그래프 기능은 사용할 수 없습니다. 계산기를 공유할 수 없습니다. 시험 중이나 시험지가 있는 동안 휴대전화, PDA, 카메라 등 허가되지 않은 전자 기기를 사용할 수 없습니다. 표, 책, 공식 모음 등 외부 참고자료도 사용할 수 없습니다."
    if text.startswith("Questions with the same"):
        return "배점이 같은 문항이라도 난이도가 반드시 같은 것은 아닙니다."
    if text.startswith("Part C is an optional"):
        return "Part C는 선택 사항이며 추가로 20분이 주어집니다. 이 점수는 미국 대표 선발에 영향을 주지 않으나 미국광학회가 수여하는 특별상과 표창에 사용될 수 있습니다."
    if text.startswith(("In order to maintain", "Do not discuss")):
        return "시험 보안을 위해 " + source_date(text) + " 이후까지 문제나 답, 풀이에 관한 정보를 논의하거나 전달하지 마십시오." + (" 위반하면 실격될 수 있습니다." if "disqualification" in text else "")
    if text.startswith("At the beginning of the exam"):
        return "시험 시작 시 안내문, 답안 및 계산용 백지, 시험지 묶음을 받아야 합니다."
    if text.startswith("The 2021 USAPhO"):
        return "2021 USAPhO는 이틀에 걸쳐 진행되는 두 개의 90분 시험으로 구성됩니다.\nPart A: 4월 19일 월요일 오후 4:00~5:30(미국 동부시간)\nPart B: 4월 21일 수요일 오후 4:00~5:30(미국 동부시간)\nAAPT가 주관하며 Art of Problem Solving이 제공하는 플랫폼에서 시행합니다."
    if text.startswith("This year, we require"):
        return "올해 시험은 고등학교 과학·물리 교사 또는 학부모·보호자가 감독해야 합니다."
    if text.startswith("Before you start the exam"):
        return "시험 전에 답안 및 계산용 백지, 필기구, 메모리와 프로그램을 지운 휴대용 공학용 계산기, USAPhO 시험 페이지에 접속할 컴퓨터를 준비하십시오. 그런 다음 명예 서약에 동의하고 시험지를 내려받으십시오."
    if text.startswith("At the end of the exam, you have 20"):
        return "각 부분의 시험이 끝나면 모든 문항의 풀이를 업로드할 시간 20분이 주어집니다. 문항별로 풀이의 각 페이지를 스캔하거나 촬영하여 하나의 PDF로 합친 뒤 시험 플랫폼에 업로드하십시오."
    if text.startswith("USAPhO graders"):
        return "채점자는 누락된 페이지나 판독할 수 없는 필기에 대해 책임지지 않습니다. 늦은 제출은 받지 않습니다. 특별한 상황 속에서 올해 USAPhO에 참여해 주셔서 감사합니다. 여러분과 가족의 건강을 기원하며, 더 많은 학생이 물리학을 공부하고 AAPT의 F = ma 시험에 도전하도록 격려해 주시기 바랍니다."
    if text.startswith("You should receive"):
        return "이 안내문, 다음 쪽의 참고표, 문항 표지 또는 답안지, 풀이 및 계산용 백지를 받아야 합니다. 시험 시작 전에 주의 깊게 읽으십시오."
    if text.startswith("When the exam begins, your proctor"):
        return "시험이 시작되면 감독관이 Part A 문제를 나누어 줍니다. 3문항을 푸는 시간은 90분이며 각 문항은 25점입니다. 난이도는 서로 다를 수 있습니다. 모두 풀었다면 풀이를 검토할 수 있으나 Part B를 볼 수 없습니다."
    if text.startswith("After 90 minutes"):
        return "90분 후 감독관이 Part A의 문제와 답안지를 회수합니다." + (" 계산용 종이는 답안지에 포함하지 마십시오." if "scratch work" in text else "") + " 그런 다음 짧게 휴식합니다."
    if text.startswith("Then you will work on Part B"):
        return "다음으로 Part B를 풉니다. 3문항, 90분이며 각 문항은 25점입니다. 이 시간에는 Part A를 볼 수 없습니다. 시험이 끝나면 문제지를 포함한 모든 종이를 감독관에게 반납하십시오."
    if text.startswith(("This year, all of your solutions", "All of your solutions must")):
        return "모든 풀이는 공식 답안지에 써야 하며 그 밖의 내용은 채점하지 않습니다. 시험 시작 전에 지시에 따라 이름, 학생 AAPT 번호 및 감독관 AAPT 번호를 답안지에 쓰십시오."
    if text.startswith("There are several answer sheets"):
        return "문항마다 여러 장의 답안지가 있습니다. 공간이 부족하면 묶음 끝의 추가 답안지를 사용하십시오. 채점에 포함되도록 해당 문항 마지막 답안지 하단에 추가 답안지를 사용한다고 표시해야 합니다."
    if text.startswith("Only write within"):
        return "각 답안지의 테두리 안에만 쓰십시오. 각 소문항의 최종 답에는 상자를 그리는 것이 좋습니다. 풀이를 순서대로 정리하고 근거를 간단히 설명하면 부분 점수에 도움이 됩니다. 연필이나 펜을 사용할 수 있으나 스캔 후에도 읽을 수 있게 명료하게 쓰십시오."
    if text.startswith("You may have to fit"):
        return "데이터에 직선을 맞추어야 할 수 있습니다. 모눈 답안지에 그래프를 그리고 자, 연필, 펜 또는 종이의 곧은 변을 사용할 수 있습니다."
    if text.startswith("All smartphones"):
        return "스마트폰, 태블릿, 스마트워치 및 기타 인터넷 연결 기기는 시험 시작 전에 모두 제출해야 합니다. 시험용으로 지정된 데스크톱, 노트북 또는 크롬북만 사용할 수 있습니다."
    if text.startswith("You must remain"):
        return "시험 시간 내내 시험실 안에 있어야 합니다."
    if text.startswith("When the exam begins, click"):
        return "시험이 시작되면 Part A 링크를 누르십시오. Start를 누르면 타이머가 시작됩니다. 3문항을 푸는 시간은 90분이며 각 문항은 25점입니다. 난이도는 다를 수 있습니다. 모두 풀었다면 검토할 수 있으나 Part B로 넘어가지는 마십시오."
    if text.startswith("After the break, click"):
        return "휴식 후 Part B 링크를 누르십시오. 다시 90분 동안 3문항을 풀며 각 문항은 25점입니다."
    if text.startswith("At the end of Part B"):
        return "Part B가 끝나면 Part B 답안지(계산용 종이 제외), 사용하지 않은 종이와 사용한 계산용 종이 전부, 이 안내문을 반납해야 합니다."
    if text.startswith("After you have completed Part A,"):
        return "Part A를 마친 후 휴식할 수 있습니다."
    if text.startswith("Show all your work."):
        return "모든 풀이 과정을 보이십시오. 부분 점수가 주어집니다."
    if text.startswith("Do not discuss the contents"):
        return "시험 내용은 " + source_date(text) + " 이후까지 누구와도 논의하지 마십시오."
    if text.startswith("Good luck"):
        return "좋은 결과를 기원합니다."
    raise ValueError("Untranslated student instruction: " + text)


def administrative(output, original, korean, question_groups, selection, year):
    first_kq = min(p[0] for pieces in question_groups.values() for p in pieces)
    prefix = [korean[i] for i in range(selection[0], first_kq)]
    for i, source in enumerate(original):
        text = page_text(source)
        page = output[i]
        if year < 2007:
            if i == 0 and prefix:
                source_lines = lines(source)
                source_start = [l["rect"].y0 for l in source_lines if re.search(r"instructions", l["text"], re.I)]
                source_end = [l["rect"].y0 for l in source_lines if "possiblyuseful" in re.sub(r"\s+", "", l["text"]).lower()]
                kp = prefix[0]
                ko_lines = lines(kp)
                ko_start = [l["rect"].y0 for l in ko_lines if re.search(r"지시\s*사항|안내|INSTRUCTIONS|Instructions", l["text"]) and l["rect"].y0 > 30]
                ko_end = [l["rect"].y0 for l in ko_lines if re.search(r"참고용\s*정보|유용|Possibly useful", l["text"], re.I)]
                if not (source_start and source_end and ko_start and ko_end):
                    raise ValueError(f"{year}: scan cover instruction bounds need review")
                start, end = min(source_start), min(source_end) - 5
                ka, kb = min(ko_start), min(ko_end) - 4
                rect = fitz.Rect(45, start, source.rect.width - 42, end)
                page.draw_rect(rect + (-2, -2, 2, 2), color=None, fill=(1, 1, 1))
                crop = fitz.Rect(40, ka, kp.rect.width - 40, kb)
                page.show_pdf_page(rect, korean, selection[0], clip=crop)
            continue
        # The excluded supervisor page was often dropped from the Drive copy.
        if "DO NOT DISTRIBUTE THIS PAGE" in text:
            source_lines = lines(source)
            first = min(l["rect"].y0 for l in source_lines if "DO NOT DISTRIBUTE" in l["text"])
            bullets = [proctor_bullet(p) for p in re.split("•", text)[1:]]
            body = "이 페이지를 배포하지 마십시오\n시험 감독관을 위한 중요 안내\n\n" + "\n\n".join("• " + p for p in bullets)
            acknowledgement = re.search(r"We acknowledge.*?\n(.*?)Copyright", text, re.S)
            if acknowledgement:
                names = re.sub(r"\s+", " ", acknowledgement[1]).strip()
                names = re.sub(r"^\(in alphabetical order\):?\s*", "", names)
                body += "\n\n출제에 기여한 다음 분들께 감사드립니다(알파벳순).\n" + names
            korean_box(page, fitz.Rect(70, first - 2, source.rect.width - 68, footer(source) - 1), body, 9.5)
            continue
        if "STOP:" in text:
            source_lines = lines(source)
            first = min(l["rect"].y0 for l in source_lines if "STOP:" in l["text"])
            part = "C" if "Continue to Part C" in text else "B"
            body = f"정지: Part {part}로 넘어가지 마십시오\n\n현재 부분의 시간이 남아 있다면 풀이를 검토하십시오. 시험 감독관의 지시를 받기 전까지 다음 부분으로 넘어가면 안 됩니다."
            if "not be able to return" in text or "cannot go back" in text:
                body += "\n\n다음 부분을 시작한 뒤에는 이전 부분으로 돌아갈 수 없습니다."
            korean_box(page, fitz.Rect(72, first - 2, source.rect.width - 72, min(first + 210, footer(source) - 1)), body, 15)
            continue
        # Translate the prose on the source's student cover, retaining logos,
        # constants, formulae, rules, margins, and copyright as source vectors.
        cover_heading = [l for l in lines(source) if re.fullmatch(r"INSTRUCTIONS|Instructions for the Student|Information About The 2021 USAPhO|Information about USAPhO Test", l["text"].strip())]
        if cover_heading and "•" in text:
            first = cover_heading[0]["rect"].y0
            stop = [l["rect"].y0 for l in lines(source) if re.search(r"Possibly [Uu]seful [Ii]nformation|Reference table", l["text"])]
            bottom = min(stop) - 8 if stop else footer(source) - 1
            prose = re.split(r"Possibly [Uu]seful [Ii]nformation|Reference table|Copyright", text)[0]
            bullets = [student_bullet(p) for p in re.split("•", prose)[1:]]
            body = ("2021 USAPhO 안내" if year == 2021 else "USAPhO 안내" if year == 2020 else "학생을 위한 안내")
            if "DO NOT OPEN" in text:
                body += "\n시작하라는 지시가 있기 전까지 시험지를 펼치지 마십시오."
            body += "\n\n" + "\n\n".join("• " + p for p in bullets)
            if year == 2020:
                body += "\n\n특별한 상황 속에서 올해 USAPhO에 참여해 주셔서 감사합니다. 여러분과 가족의 건강을 기원하며 더 많은 학생이 물리학을 공부하고 AAPT의 F = ma 시험에 도전하도록 격려해 주시기 바랍니다."
            acknowledgement = re.search(r"We acknowledge.*?\n(.*?)Copyright", text, re.S)
            if acknowledgement:
                names = re.sub(r"\s+", " ", acknowledgement[1]).strip()
                names = re.sub(r"^\(in alphabetical order\):?\s*", "", names)
                body += "\n\n출제에 기여한 다음 분들께 감사드립니다(알파벳순).\n" + names
            korean_box(page, fitz.Rect(72, first - 1, source.rect.width - 72, bottom), body, 9.5)
        if "Following is some further guidance on formatting" in text:
            body = "답안 작성 형식에 대한 추가 안내\n\n각 문제는 새 종이에서 시작하십시오. 각 페이지 오른쪽 위에 학생 AAPT 번호, 감독관 AAPT 번호, 문제 번호, 해당 문제의 페이지 번호/전체 페이지 수를 쓰십시오. 예를 들어 B3 풀이의 두 번째 페이지는 다음과 같이 표시할 수 있습니다.\n\nstudent AAPT #29485\nproctor AAPT #1038\nB3: 2/2\n\n제공된 답안지에도 AAPT 번호를 쓰십시오. 스캔이 쉽도록 한 면에만 쓰십시오. 연필이나 펜을 사용할 수 있으나 스캔 후에도 판독할 수 있게 명료하게 쓰십시오. 익명 채점을 위해 어떤 종이에도 이름을 쓰지 마십시오.\n\n학생 안내 끝\n시작하라는 지시가 있기 전까지 시험지를 펼치지 마십시오."
            korean_box(page, fitz.Rect(72, 70, source.rect.width - 72, footer(source) - 1), body, 10.5)
        replacements = {
            "Answer Sheets": "답안지", "Fundamental Constants": "기본 상수", "Useful Approximations": "유용한 근사식",
            "REFERENCE SHEET": "참고 자료", "Reference table of possibly useful information": "풀이에 사용할 수 있는 참고표",
            "Following are answer sheets for some of the graphical portions of the test.": "다음은 시험의 그래프 문항 일부에 사용할 답안지입니다.",
            "You may use this sheet for both parts of the exam.": "이 자료는 시험의 두 부분 모두에서 사용할 수 있습니다.",
        }
        for line in lines(source):
            value = line["text"].strip()
            translated = replacements.get(value)
            match = re.fullmatch(r"Answer for Part ([AB]), Question (\d+)", value)
            if match:
                translated = f"Part {match[1]}, 문제 {match[2]} 답안"
            if translated:
                rect = line["rect"] + (-1, -1, 10, 4)
                rect.x1 = min(rect.x1, source.rect.width - 45)
                korean_box(page, rect, translated, min(12, max(8.5, line["rect"].height * .75)), 7)


def lines(page):
    result = [
        {"rect": fitz.Rect(line["bbox"]), "text": "".join(s["text"] for s in line["spans"])}
        for block in page.get_text("dict")["blocks"] if "lines" in block
        for line in block["lines"]
    ]
    if not result:
        match = re.search(r"USAPhO_(\d{4})_T_EN", page.parent.name)
        if match:
            key = match[1] + "-" + str(page.number + 1)
            if key not in _SCAN_CACHE:
                saved = json.loads(SCAN_OCR.read_text(encoding="utf-8")) if SCAN_OCR.exists() else {}
                path = WORK / "scans" / (key + ".json")
                _SCAN_CACHE[key] = saved.get(key) or (json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else [])
            for item in _SCAN_CACHE[key]:
                text = re.sub(r"\b([AB])[lI](?=[. :]|$)", r"\g<1>1", item["text"])
                text = re.sub(r"\b([AB])\s+([1-4])(?=[. :]|$)", r"\1\2", text)
                if re.fullmatch(r"[AB][1-4]", text.strip()):
                    text += "."
                result.append({"rect": fitz.Rect(item["rect"]), "text": text, "ocr": True})
    return sorted(result, key=lambda x: (round(x["rect"].y0, 1), x["rect"].x0))


def page_text(page):
    return page.get_text() or "\n".join(line["text"] for line in lines(page))


def footer(page):
    found = [l["rect"].y0 for l in lines(page) if ("Copyright" in l["text"] or re.search(r"Page\s*\d+\s*of\s*\d+", l["text"], re.I))
             and l["rect"].y0 > page.rect.height * .7]
    return min(found) - 6 if found else page.rect.height - 42


def top(page):
    match = re.search(r"(?:19\d\d|20\d\d)", Path(page.parent.name).name)
    if match and int(match[0]) == 2006 and re.search(r"_T_EN\.pdf$", page.parent.name):
        # The source scan prints the team logo on every page; its left edge is
        # partly outside the narrow OCR strip. Verified against all seven scans.
        return 145
    if match and 1997 <= int(match[0]) <= 2006:
        header = [line["rect"].y1 for line in lines(page) if line["rect"].y0 < 170 and re.search(
            r"^(?:AAPT|AIP|UNITED STATES PHYSICS TEAM|Page \d+ of \d+|200[0-6]$)|준결승\s*시험|Semi.Final Exam", line["text"], re.I)]
        return max(header) + 5 if header else 10
    return page.rect.height * .075


def excluded(page):
    text = page_text(page)
    administrative = {"Answer Sheets", "답안지", "Cover Sheet", "Student Instructions", "Proctor Instructions", "REFERENCE SHEET"}
    return bool(re.search(r"STOP:|정지:|DO NOT DISTRIBUTE", text)) or any(
        re.fullmatch(r"INSTRUCTIONS:?|지시\s*사항\s*\((?:Instructions|INSTRUCTIONS)\)|안내\s*\(INSTRUCTIONS\)", line["text"].strip(), re.I)
        for line in lines(page)
    ) or any(
        line["rect"].y0 < 120 and (line["text"].strip() in administrative or line["text"].startswith("Reference table"))
        for line in lines(page)
    )


def sections(doc, start=0, stop=None):
    """Find each printed question and its continuation, retaining the source ID."""
    stop = len(doc) if stop is None else stop
    result, active, page_headers = {}, None, {}
    for i in range(start, stop):
        page = doc[i]
        if excluded(page):
            continue
        body_top, body_bottom = top(page), footer(page)
        anchors = []
        for line in lines(page):
            if line["rect"].y0 < body_top or line["rect"].y0 >= body_bottom:
                continue
            if line.get("ocr") and line["rect"].x0 > 110 and line["rect"].y0 < 180:
                continue  # AIP in the source logo can be OCR'd as A1.
            match = QSTART.match(line["text"].strip())
            if match:
                code = (match[1] or match[2]).upper()
                if code != active:
                    anchors.append((code, line["rect"].y0 - 1))
            elif re.match(r"^(?:Optical Society of America Bonus Question|미국광학회.*보너스)", line["text"]):
                anchors.append(("C1", line["rect"].y0 - 1))
        if not anchors and (not active or excluded(page)):
            continue
        if anchors:
            # The official Part A/B label and other furniture above the question
            # are retained from the English template, not the reformatted copy.
            page_headers[i] = anchors[0][1]
            brand = any(l.get("ocr") and l["rect"].x0 > 110 and l["rect"].y0 < 180
                        and re.match(r"A(?:APT|IP|1|l)", l["text"], re.I) for l in lines(page))
            if active and anchors[0][0] != "B1" and not brand and anchors[0][1] > top(page) + 22:
                body = "\n".join(l["text"] for l in lines(page) if top(page) <= l["rect"].y0 < anchors[0][1]).strip()
                if body and not re.fullmatch(r"(?:Part [AB]|준결승시험.?\s*Part [AB]|2022 USAPhO|\s)+", body):
                    page_headers[i] = top(page)
                    result[active].append((i, top(page), anchors[0][1] - 5))
            for index, (code, y) in enumerate(anchors):
                if code in result:
                    raise ValueError(f"Duplicate question {code} on page {i + 1}")
                bottom = anchors[index + 1][1] - 8 if index + 1 < len(anchors) else footer(page)
                result[code] = [(i, y, bottom)]
                active = code
        else:
            page_headers[i] = top(page)
            result[active].append((i, top(page), footer(page)))
    return result, page_headers


def ink(page, y0, y1):
    """Visible text, vector art and images within a body crop."""
    rects = [line["rect"] & fitz.Rect(0, y0, page.rect.width, y1)
             for line in lines(page) if line["rect"].y0 >= y0 and line["rect"].y1 <= y1]
    for kind, bbox in page.get_bboxlog():
        if "text" in kind:
            continue
        rect = fitz.Rect(bbox)
        if rect.y1 <= y0 or rect.y0 >= y1 or rect.width <= 0 or rect.height <= 0:
            continue
        # A page-size invisible clipping path is not body content.
        if rect.y0 < y0 - 10 and rect.y1 > y1 + 10:
            continue
        rects.append(rect & fitz.Rect(0, y0, page.rect.width, y1))
    return rects


def body_width(doc, groups):
    if not any(page.get_text().strip() for page in doc):
        # Original scans have no text layer. Detect the ink of the actual source
        # body pixels, rather than inferring its width from the OCR ID strip.
        bounds = []
        for pieces in groups.values():
            for i, y0, y1 in pieces:
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), colorspace=fitz.csGRAY, clip=fitz.Rect(0, y0, page.rect.width, y1))
                image = Image.frombytes("L", [pix.width, pix.height], pix.samples)
                box = image.point(lambda value: 255 if value < 160 else 0).getbbox()
                if box:
                    bounds.append(box)
        return min(b[0] for b in bounds) - 1, max(b[2] for b in bounds) + 1
    rects = []
    for pieces in groups.values():
        for i, y0, y1 in pieces:
            rects += ink(doc[i], y0, y1)
    return min(r.x0 for r in rects) - 1, max(r.x1 for r in rects) + 1


def ribbon(doc, pieces, left, right):
    crops, height = [], 0
    intervals, labels = [], {}
    for i, y0, y1 in pieces:
        boxes = ink(doc[i], y0, y1)
        if not boxes:
            continue
        a, b = max(y0, min(r.y0 for r in boxes) - 1), min(y1, max(r.y1 for r in boxes) + 1)
        crop = fitz.Rect(left, a, right, b)
        crops.append((i, crop, height))
        for rect in boxes:
            intervals.append((max(a, rect.y0) - a + height, min(b, rect.y1) - a + height))
        for line in lines(doc[i]):
            if a <= line["rect"].y0 < b:
                match = re.match(r"^\s*(?:\(([a-z]{1,3})\)|([a-z]{1,3})\.)", line["text"])
                if match:
                    labels.setdefault(match[1] or match[2], []).append(line["rect"].y0 - a + height)
        height += crop.height + 5
    height -= 5
    if height <= 0:
        raise ValueError("No translated question content")
    result = fitz.open()
    page = result.new_page(width=right - left, height=height)
    for index, crop, y in crops:
        page.show_pdf_page(fitz.Rect(0, y, crop.width, y + crop.height), doc, index, clip=crop, keep_proportion=False)
    merged = []
    for a, b in sorted(intervals):
        if merged and a <= merged[-1][1] + .25:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    cuts = [0.] + [(one[1] + two[0]) / 2 for one, two in zip(merged, merged[1:]) if two[0] - one[1] > 1] + [height]
    return result, cuts, labels


def place_question(output, source, target_slots, translated, cuts, labels, left, right):
    """Allocate the complete vector ribbon to the original question's pages."""
    height, width = translated[0].rect.height, translated[0].rect.width
    capacities = [y1 - y0 for _, y0, y1 in target_slots]
    if len(target_slots) > 1 and len(cuts) == 2:
        # A translated diagram can sit beside the entire (shorter) Korean prose.
        # Do not slice that illustration merely because the English prose had a
        # continuation page. Use the first original region that holds it intact.
        natural = (right - left) / width
        fitting = [n for n, capacity in enumerate(capacities) if height * natural <= capacity]
        chosen = fitting[0] if fitting else max(range(len(capacities)), key=lambda n: capacities[n])
        index, y0, y1 = target_slots[chosen]
        scale = min(natural, (y1 - y0) / height)
        output[index].show_pdf_page(fitz.Rect(left, y0, left + width * scale, y0 + height * scale), translated, 0)
        return {"scale": round(scale, 4), "pages": [index + 1], "source_height": round(height, 1),
                "split_positions": [0, round(height, 1)], "original_continuation_regions": [i + 1 for i, _, _ in target_slots if i != index],
                "layout_note": "Kept the complete illustration intact; Korean prose fits one original region."}
    total_capacity = sum(capacities)
    boundaries = [0.]
    accumulated = 0
    for index, capacity in enumerate(capacities[:-1]):
        accumulated += capacity
        ideal = height * accumulated / total_capacity
        remaining = len(capacities) - index - 1
        candidates = [c for c in cuts if c > boundaries[-1] + 8 and c < height - 8 * remaining]
        if not candidates:
            raise ValueError("No safe line/figure boundary for an original page break")
        next_page, next_top, next_bottom = target_slots[index + 1]
        preferred = []
        for line in lines(source[next_page]):
            if not next_top <= line["rect"].y0 < min(next_top + 240, next_bottom):
                continue
            match = re.match(r"^\s*(?:\(([a-z]{1,3})\)|([a-z]{1,3})\.)", line["text"])
            if match:
                preferred = [p for p in labels.get(match[1] or match[2], []) if p > boundaries[-1] + 8]
                if preferred:
                    break
        if preferred:
            position = min(preferred, key=lambda p: abs(p - ideal))
            before = [c for c in candidates if c <= position + .5]
            if before:
                boundaries.append(max(before))
            else:
                boundaries.append(min(candidates, key=lambda c: abs(c - ideal)))
        else:
            boundaries.append(min(candidates, key=lambda c: abs(c - ideal)))
    boundaries.append(height)
    scale = min((right - left) / width, *(capacity / (b - a) for capacity, a, b in zip(capacities, boundaries, boundaries[1:])))
    for (index, y0, y1), a, b in zip(target_slots, boundaries, boundaries[1:]):
        rect = fitz.Rect(left, y0, left + scale * width, y0 + scale * (b - a))
        output[index].show_pdf_page(rect, translated, 0, clip=fitz.Rect(0, a, width, b), keep_proportion=False)
    return {"scale": round(scale, 4), "pages": [i + 1 for i, _, _ in target_slots],
            "source_height": round(height, 1), "split_positions": [round(x, 1) for x in boundaries]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--years", nargs="*", type=int)
    parser.add_argument("--audit-file", type=Path, default=AUDIT)
    args = parser.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    info = json.loads(args.audit_file.read_text(encoding="utf-8"))
    report_path = WORK / ("layout-audit.json" if args.audit_only else "restore-report.json")
    result = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() and not args.audit_only else {}
    additions_path = ROOT / "tools/usapho_ko_additions.json"
    additions = json.loads(additions_path.read_text(encoding="utf-8")) if additions_path.exists() else {"usapho": {}}
    for year, paths in info.items():
        y = int(year)
        if args.years and y not in args.years:
            continue
        original, korean = fitz.open(ROOT / paths["en"]), fitz.open(ROOT / paths["ko"])
        try:
            originals, furniture = sections(original)
            selection = SELECTED.get(y, (0, len(korean)))
            translations, _ = sections(korean, *selection)
        except ValueError as exc:
            raise ValueError(f"{year}: {exc}") from exc
        report = {"source": paths["en"], "translation": paths["ko"], "selected_translation_pages": [selection[0] + 1, selection[1]],
                  "original_pages": len(original), "translated_questions": list(translations), "original_questions": list(originals)}
        if set(originals) != set(translations):
            report["error"] = "Question IDs differ"
            result[year] = report
            continue
        report["original_regions"] = originals
        report["translation_regions"] = translations
        if args.audit_only:
            result[year] = report
            continue
        left, right = body_width(original, originals)
        kl, kr = body_width(korean, translations)
        output = fitz.open()
        preserved_graphs = []
        if y in (1997, 2006):
            # The official final page is the supplied full-page pressure graph.
            # The Drive translation moved that graph below the B2 prose. Restore
            # the actual source graph page and keep the translated prose on B2.
            graph_page = 7 if y == 1997 else 6
            preserved_graphs = [graph_page]
            originals["B2"] = [piece for piece in originals["B2"] if piece[0] != graph_page]
            pieces = []
            for index, y0, y1 in translations["B2"]:
                if y == 2006 and index == len(korean) - 1:
                    prose_ends = [line["rect"].y1 for line in lines(korean[index])
                                  if y0 < line["rect"].y0 < y1 and re.search(r"6월\s*21일", line["text"])]
                    labels = [line["rect"].y0 for line in lines(korean[index])
                              if y0 < line["rect"].y0 < y1 and re.search(r"상대\s*세기", line["text"])]
                    if not labels:
                        raise ValueError("2006 B2: cannot locate the start of the supplied graphs")
                    pieces.append((index, y0, max(prose_ends) + 1 if prose_ends else min(labels) - 4))
                    continue
                images = [fitz.Rect(info["bbox"]) for info in korean[index].get_image_info()]
                images = [rect for rect in images if rect.height > 100 and rect.y0 > y0]
                if images:
                    graph = max(images, key=lambda rect: rect.get_area())
                    pieces.append((index, y0, graph.y0 - 2))
                    tail = [line for line in lines(korean[index]) if graph.y1 + 2 < line["rect"].y0 < y1]
                    if tail:
                        pieces.append((index, graph.y1 + 2, y1))
                else:
                    pieces.append((index, y0, y1))
            translations["B2"] = pieces
            report["preserved_source_graph_pages"] = [graph_page + 1]
        question_pages = {i for pieces in originals.values() for i, _, _ in pieces}
        for i, page in enumerate(original):
            target = output.new_page(width=page.rect.width, height=page.rect.height)
            if i not in question_pages:
                target.show_pdf_page(target.rect, original, i)
            else:
                header = fitz.Rect(0, 0, page.rect.width, furniture[i] - 2)
                target.show_pdf_page(header, original, i, clip=header)
                foot = fitz.Rect(0, footer(page) + 3, page.rect.width, page.rect.height)
                target.show_pdf_page(foot, original, i, clip=foot)
        report["questions"] = {}
        for code, slots in originals.items():
            strip, cuts, labels = ribbon(korean, translations[code], kl, kr)
            try:
                report["questions"][code] = place_question(output, original, slots, strip, cuts, labels, left, right)
            except ValueError as exc:
                raise ValueError(f"{year} {code}: {exc}") from exc
            strip.close()
        if y == 2006:
            # The Drive PDF's first plot curve starts above its axis label. Its
            # tiny upper edge must not follow the B2 prose onto the prior page.
            ending = [line for block in output[5].get_text("dict")["blocks"] if "lines" in block
                      for line in block["lines"] if re.search(r"6월\s*21일", "".join(span["text"] for span in line["spans"]))]
            if not ending:
                raise ValueError("2006 B2: missing final June-21 sentence")
            baseline = max(span["origin"][1] for span in ending[-1]["spans"])
            output[5].draw_rect(fitz.Rect(left, baseline + 2, right, footer(original[5]) - 2), color=None, fill=(1, 1, 1))
            report["format_cleanup"] = "Removed the curve edge from the relocated graph after the final B2 sentence."
        administrative(output, original, korean, translations, selection, y)
        output.set_metadata({"title": f"USAPhO {year} - Korean, official page layout", "subject": "Korean translation from the user's Google Drive; original AAPT page geometry and exam identity restored", "author": "HaslaLab"})
        OUT.mkdir(exist_ok=True)
        path = OUT / f"USAPhO_{year}_T_KO.pdf"
        output.save(path, garbage=4, deflate=True)
        report["output"] = str(path.relative_to(ROOT)).replace("\\", "/")
        report["output_pages"] = len(output)
        report["administrative_pages"] = [i + 1 for i in range(len(original)) if i not in question_pages]
        output.close()
        additions["usapho"][year] = {"T": {"paper": report["output"]}}
        result[year] = report
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if not args.audit_only:
        (ROOT / "tools/usapho_ko_additions.json").write_text(json.dumps(additions, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    selected = {year: item for year, item in result.items() if not args.years or int(year) in args.years}
    print(json.dumps({"years": sorted(selected), "errors": {year: item["error"] for year, item in selected.items() if item.get("error")},
                      "output_pages": sum(item.get("output_pages", 0) for item in selected.values())}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
