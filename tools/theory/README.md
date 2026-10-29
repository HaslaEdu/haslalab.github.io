# 이론 문제지 목록 (tools/theory/<대회>.json)

대회별로, 해마다 대회가 공개한 **이론 문제지와 해설(원문)**, 따로 공개된 채점 기준표 · 답안지가 어디 있는지 적은 목록입니다. 번역본은 넣지 않습니다.

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
| `IAO_2024_Ta_EN.pdf` | 연령 조가 나뉜 경우 (a: α, b: β), OPhO 초청 라운드는 `Ti` |

## JSON 모양
```json
{"comp":"ipho","prefix":"IPhO","years":[
  {"y":2024,"problems":[{"id":"T1","title":"…"}],
   "files":[{"file":"IPhO_2024_T1_EN.pdf","part":"T1","kind":"paper","lang":"EN","url":"https://…","bytes":123456},
            {"file":"IPhO_2024_T1S.pdf","part":"T1","kind":"solution","url":"https://…","bytes":…}]}],
 "missing":[{"y":1999,"why":"…"}]}
```
`kind`: paper · solution · marking · answer.
