# 이론 문제지 목록 (tools/theory/<대회>.json)

대회별로, 해마다 대회가 공개한 **이론 문제지와 해설(원문)**, 따로 공개된 채점 기준표 · 답안지가 어디 있는지 적은 목록입니다. 번역본은 넣지 않습니다.

한국어 번역본은 이 폴더가 아니라 `tools/theory_ko.json`에 적습니다(PDF 는 `python tools/pdf_release.py <폴더>`로 릴리스에 올림, 미러 대상 아님). `theory_build.py`가 원문 위에 얹어 연도 페이지에서 한국어판을 먼저 엽니다.

번역에 동반하는 영어 조판본은 같은 부분의 `en` 아래에 `paper` · `sol` 등을 지정합니다. 예를 들어 CPhO의 그림을 다시 그린 영어판은 `{"T":{"paper":"CPhO_2025_T_KO.pdf","en":{"paper":"CPhO_2025_T_BAUPC_EN.pdf"}}}`로 연결합니다. 원문의 주소와 기록은 이 폴더의 출처 목록에 그대로 보존합니다.

- `python tools/theory_build.py` → 사이트가 읽는 `theory.js`를 만듭니다 (연도 페이지의 «이론 문제», 이론 실전 모드).
- main에 이 폴더가 바뀌어 올라오면 `.github/workflows/theory-pdfs.yml`(`tools/theory_mirror.py`)이 각 PDF를 원래 주소에서 받아 PDF인지 확인하고 GitHub 릴리스 `pdf-<접두어>`에 올립니다. 이미 올라간 이름은 건너뜁니다. 받지 못한 파일은 실행 요약에 표로 남고, 다음 실행 때 다시 시도합니다. Actions › «Theory papers to releases» › Run workflow로 손으로(대회를 골라) 돌릴 수도 있습니다.

## 파일 이름
| 이름 | 뜻 |
|---|---|
| `IPhO_2024_T_EN.pdf` | 이론 전체 문제지 (언어 표시: EN, RU …) |
| `IPhO_2024_T1_EN.pdf` | 문제마다 따로 공개된 문제지 (T1, T2, …) |
| `IPhO_2024_TS.pdf`, `IPhO_2024_T1S.pdf` | 그 해설 |
| `IPhO_2024_TM.pdf` | 따로 공개된 채점 기준표 |
| `IPhO_2024_TA.pdf` | 공식 답안지 |
| `IJSO_2024_MC_EN.pdf` | 객관식 문제지 (MC) |
| `IPhO_2017_GT.pdf` | 이론 일반 지시사항 (`kind: general`, `for: theory`) |
| `IPhO_2017_GE.pdf`, `IOAA_2025_GE2.pdf` | 실험 · 관측 라운드 일반 지시사항 (`kind: general`, `for: exp`, 라운드가 여럿이면 `label`) |
| `IAO_2024_Ta_EN.pdf` | 연령 조가 나뉜 경우 (a: α, b: β), OPhO 초청 라운드는 `Ti` |

## JSON 모양
```json
{"comp":"ipho","prefix":"IPhO","years":[
  {"y":2024,"problems":[{"id":"T1","title":"…"}],
   "files":[{"file":"IPhO_2024_T1_EN.pdf","part":"T1","kind":"paper","lang":"EN","url":"https://…","bytes":123456},
            {"file":"IPhO_2024_T1S.pdf","part":"T1","kind":"solution","url":"https://…","bytes":…}]}],
 "missing":[{"y":1999,"why":"…"}]}
```
`kind`: paper · solution · marking · answer · general.

일반 지시사항은 연도 페이지 «문제를 고르세요» 아래에 버튼으로 나옵니다: 이론은 `THEORY[대회][연도].g`, 실험은 `window.GENERAL[대회][연도]`(theory.js). 이론 문제지가 없는 해(예: IPhO 2020)도 실험 지시사항만 적을 수 있습니다.

## NBPhO: 문제별로 자른 책자
NBPhO는 문제지 · 해설이 각각 한 권이라, 연습 모드용으로 문제별 PDF를 `pdfx/nbpho/NBPhO_<연도>_P<번호>_EN.pdf` / `…_P<번호>S.pdf`로 잘라 둡니다(`python tools/nbpho_split.py <책자 폴더>`, 결과 목록 `pdfx/nbpho/index.json`). `theory_build.py`가 이를 읽어 이론 문제마다 T<번호>로, 실험 문제는 실험 카드에 연결합니다. 책자 전체(T)는 실전 모드(실험 + 이론)에 씁니다.
