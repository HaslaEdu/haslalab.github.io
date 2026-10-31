# 정답표 서식과 실시 날짜

2026-10-30 확인. 공식 2024~2026 정답표 24개와 사용자 제공 2023년 정답 자료 5세트의 모든 쪽을 측정했다. 원본은 `tmp/kphe_archive/originals`에 보존하며, 원본 SHA·헤더·정답 본문·룰의 좌표와 글꼴은 `kphe_key_design_profiles.json`에 기록했다. 공용 빌더나 공식 원본 PDF는 이 도우미가 변경하지 않는다.

| 회차 | 실시일 | 한국물리학회 근거 |
|---|---|---|
| 2023-1 | 2023-02-18 | [접수 기간 연장 안내](https://kphe.kps.or.kr/notice/notice_detail/34) |
| 2023-2 | 2023-09-02 | [본 시험 안내](https://kphe.kps.or.kr/notice/notice_detail/111) |
| 2024-1 | 2024-02-24 | [기출문제·정답](https://kphe.kps.or.kr/board/board_detail/8) |
| 2024-2 | 2024-08-31 | [기출문제·정답](https://kphe.kps.or.kr/board/board_detail/9) |
| 2025-1 | 2025-02-22 | [기출문제·정답](https://kphe.kps.or.kr/board/board_detail/10) |
| 2025-2 | 2025-08-30 | [기출문제·정답](https://kphe.kps.or.kr/board/board_detail/11) |
| 2026-1 | 2026-02-28 | [기출문제·정답](https://kphe.kps.or.kr/board/board_detail/12) |
| 2026-2 | 2026-09-05 | [기출문제·정답](https://kphe.kps.or.kr/board/board_detail/43) |

실시일과 공지 게시일·정답 수정일을 구분했다. 2024 공식 정답표에는 인쇄 날짜가 없으므로 원본은 그대로 보존하고, 새 해설에만 확인된 실시일을 최신 2026 서식으로 넣는다. 2025·2026 해설은 해당 회차·과정 공식 정답표의 날짜 글리프를 원본 벡터 클립으로 옮긴다. `kphe_exam_dates.json`은 29개 날짜의 원문·원본 SHA·원래 좌표·폰트·포인트·A4 좌표와 실시일 근거를 기록한다.

## 서식 재현

최신 정답표는 격자형 답안지가 아니라 중앙 세로선으로 나눈 2열 정답 목록이다. 2026 제2회 초급 정답표를 13행 정답 배치의 기준으로 사용하고, 과정 이름·로고·헤더 룰은 같은 회차의 해당 과정 정답표에서 가져온다. 2023의 26문항은 좌우 13행이며 마지막 오른쪽 행은 왼쪽 13행과 같은 기준선에 놓는다. 나머지 문항 수는 같은 흐름에서 끝난다.

본문은 원본 Haansoft Batang 15pt, 헤더는 원본 KoPubDotumBold 18/15pt다. 원문 PDF의 ToUnicode와 CIDToGIDMap을 복원해 원본 글리프를 그대로 사용하고, 번호·정답·원형 숫자는 원문 개별 문자 원점에 배치한다. 새 연도나 날짜에 필요한 숫자 중 원본 subset에 없는 글자는 [기존 KoPub 폰트 출처 기록](kphe_font_provenance.md)의 동일 원본 글꼴에서 보충한다. FontDescriptor의 ascent/descent도 원문 값으로 맞춘다. 복원된 작은 폰트 프로그램은 `tmp/kphe-key-fonts`의 빌드 캐시이며 커밋하지 않는다.

원본 728×1031 좌표를 빌더의 595×842 A4로 x/y 각각 정규화한다. 이는 `kphe_template._paste`의 `keep_proportion=False` 변환과 같다. JSON은 각 축의 환산 포인트와 변환 후 PDF가 보고하는 기하평균 포인트를 모두 기록한다. 실시 날짜 기준선은 A4 y=61.9374pt 부근이고 최대 bbox 하단은 약 65.00pt로 본문 시작 70.6pt보다 위다. 과정 줄 오른쪽 빈 공간에 들어간다.

2023 제1회 중급 정답 원문 첫 쪽의 잘못된 과정 이름과 제2회 고급으로 잘못 이름 붙인 제1회 정답표는 디자인의 신뢰 근거로 삼지 않는다. 후자는 제외하고 제2회 고급 문제지의 20개 표시 답안을 기존 manifest대로 사용한다. 모든 정답·복수 인정 답·정정 특례는 호출자가 넘긴 기존 manifest가 기준이며 이 모듈이 추론해 바꾸지 않는다.

## 재현 및 검증

```powershell
python -X utf8 tools/kphe_key_design.py --measure
python -X utf8 tools/kphe_solution_dates.py --modern-only
python -X utf8 tools/kphe_solution_dates.py --check-only
```

`build_2023_key(year, part, answers, target, corrections=None)`는 2023 정답표를 만든다. `draw_exam_date(page, year, part)`는 날짜만 붙이고, `exam_date_profile(year, part)`는 프로필을 반환한다. 날짜 overlay 도구의 `verify_page(page, profile)`를 정답표 검증에도 쓸 수 있다.

검증한 2023 정답표 5개에서 총 110개 정답이 manifest와 일치했고 각 1쪽이다. 날짜 29개는 원문·폰트·위치를 검증했다. 원본 날짜를 도우미로 다시 그린 결과는 동일 렌더 픽셀이었고, 원본 정답 본문 25개 재현은 1.5픽셀 허용 기준 정밀도·재현율 1.0이었다. 임시 PDF·PNG·검증 기록은 `tmp/kphe-key-design-qa`에 있다.

현대 해설 overlay는 각 페이지의 날짜 bbox에 0.3pt 여백만 더해 text redact(`images=0`, `graphics=0`)하고 원래 본문은 재조판하지 않는다. 예외는 2024 제1회 중급·고급 및 제2회 중급·고급 네 해설이다. 이 네 문제지의 기존 가로선은 A4 y61.4~63.85pt로 날짜와 겹치므로, 해설에서만 원래 길이와 약 2.45pt 두께를 유지해 최신 정답표의 가로선 중심 y67.865pt로 옮긴다. JSON의 `header_rule_adjustment`에 원래/새 영역과 이유를 남기며 PDF 페이지의 `KPhEDateHeaderRule` 값으로 중복 이동을 막는다. 공식 문제·정답 원본은 바꾸지 않는다.

임시 저장한 PDF에서 날짜·폰트·포인트·위치를 검증하고, 전후 144dpi 전체 페이지에서 허용 영역 밖 변경 픽셀이 0인 경우에만 원본 경로로 atomic replace한다. 허용 영역은 날짜 bbox+0.3pt와, 위 네 예외에 한해서만 원래/새 가로선 bbox+0.8pt 두 좁은 띠다. v2는 원래/새 선 주변을 0.7pt 여백의 흰 fill로 정리한 뒤 새 선을 1회 그린다. cover에는 stroke가 없으며, 초기 0.12pt cover에서 비치던 AA 잔상을 넓어진 여백으로 제거했다. `KPhEDateHeaderRule`의 v2 marker가 중복 처리를 막는다. 재실행 시 올바른 날짜와 가로선이 있으면 바이트를 다시 쓰지 않는다. 최초 해설 백업은 덮어쓰지 않으며 중간 v1은 SHA가 붙은 별도 파일로 보존한다.

현대 해설 24개·109쪽에서 이 검증을 모두 통과했다. 날짜 글자·폰트·포인트·bbox는 전 109쪽에서 0.035pt 허용 범위 안에 있고, 허용 영역 밖 변경 픽셀은 0이다. 동일 명령 재실행과 `--modern-only --check-only`는 모두 24개 파일을 다시 쓰지 않았다. 원본 정답 자료 29개 SHA도 다시 확인했다. 파일별 최종 SHA·날짜·글꼴·포인트·bbox·오차·네 가로선 예외는 [짧은 검증 기록](kphe_solution_dates_validation.json)에 수록했다. 2023S를 새로 만든 뒤 전체 29S의 `--check-only` 검사는 메인 빌더에서 수행한다.

v2 재교정은 위 네 파일 19쪽만 변경했다. 이 19쪽을 최초 적용 전 백업과 다시 비교해 허용 영역 밖 변경 픽셀 0을 확인했고, 날짜를 제외한 기존 선 자리의 비백색 픽셀도 288dpi에서 0이었다. 나머지 현대 해설 20개 SHA는 v1과 동일하다. 네 헤더를 직접 렌더해 잔상이 사라진 것을 확인한 PNG는 `tmp/kphe-solution-dates/header-rule-v2-final.png`다.
