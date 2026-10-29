# RuPhO 결선과 러시아 대표 선발 과정

`rupho`는 **전러시아 물리 올림피아드 결선**의 학년별 시험이다. 기존 `T1`, `T2`, `T3`은 각각 9·10·11학년의 전체 시험지이며, 대표 선발 단계 X·Y와 같은 분류가 아니다. 원래 결선 자료와 파일 이름은 유지한다.

웹사이트에서는 **RuPhO 하나의 대회** 안에 결선·W·X·Y 단계 선택기를 둔다. 다음 키는 원문 출처·파일 이름·실전 시험을 연결하는 내부 자료 키이며, 별도 대회 카드로 노출하지 않는다.

| 키 | 표시 | 의미 |
|---|---|---|
| `rupho` | 결선 · 9·10·11학년 | 학년별 전러시아 결선 시험 |
| `ruphow` | W · 선발 예비 과정 | 결선에서 진행하는 예비 선발. 10학년의 X·Y 선발 준비 과정 |
| `ruphox` | X · 대표 선발 1차 | 러시아 IPhO 대표 선발 1차 |
| `ruphoy` | Y · 대표 선발 2차 | 러시아 IPhO 대표 선발 2차 |

주소는 `#/rupho?stage=final`, `#/rupho?stage=w`, `#/rupho?stage=x`, `#/rupho?stage=y`이며 연도 페이지에서도 단계를 고를 수 있다. 이전 `#/ruphow`, `#/ruphox`, `#/ruphoy` 주소는 같은 RuPhO의 해당 단계로 연결한다. 선택한 연도가 다른 단계에도 있으면 유지하고, 없으면 그 단계의 연도 목록을 연다. `rupho-archive.js`가 단일 공개 카탈로그를 구성하며 원본 `THEORY` 자료와 파일 링크는 변경하지 않는다.

[pho.rs 선발 과정 설명](https://xy.pho.rs/)은 W를 결선의 예비 선발, X와 Y를 각각 1·2차 선발로 설명한다. [phoXiv W](https://phoxiv.org/olympiads/rupho-w), [X](https://phoxiv.org/olympiads/rupho-x), [Y](https://phoxiv.org/olympiads/rupho-y)의 분류와 대조했다. phoXiv의 공개 대회 목록과 pho.rs에는 Z 단계가 없으므로 Z를 새로 만들거나 다른 대회에 대응시키지 않는다. IZhO는 별개의 국제 자우티코프 올림피아드다.

## 파일과 문제 번호

- `T`는 이론, `E`는 실험, `PE`는 지필 실험이다. `PE+`는 원문에 붙은 확장 훈련판 표기를 그대로 유지한다.
- phoXiv가 여러 `Part`로 공개한 이론 자료는 `T1a`, `T1b`와 같이 구분하고, 제목에 원래 `Part 1`, `Part 2`를 남긴다. 원문 문제 번호와 파일 역할은 `source_problem`과 `source_label`에 함께 기록한다.
- 파일 라벨 `Solution`만 해설로 분류한다. `Part 1`이나 `Part 2`를 해설로 추측하지 않는다.
- pho.rs에는 있고 phoXiv에는 PDF가 없는 W27·X27은 출처 스냅샷의 `pho_rs_only`에 기록한다. 존재하지 않는 PDF 주소를 만들지 않는다.

## 재생성과 검증

`python tools/rupho_selection_build.py --refresh`로 양쪽 출처를 다시 읽고, `--refresh` 없이 실행하면 확인한 `tools/rupho_selection_sources.json`으로 재생성한다. 출력은 단계별 `tools/theory/rupho[wxy].json`, 실험용 `rupho-selection.js`, 로고다. `theory_build.py`가 이론 자료를 합친다. `node --test tests/test-rupho-archive.cjs`는 단일 대회 목록, 전 연도의 문제·해설 링크, 실험 자료와 예전 주소의 연결을 검증한다. 다른 작업이 진행 중인 체크아웃에는 `tools/rupho_archive_integrate.py`로 `index.html`의 관련 변경만 적용할 수 있다.

`python tools/rupho_selection_validate.py --download`는 번호·단계·파일명 중복을 확인하고 원문 PDF를 내려받아 실제 PDF인지와 페이지 수를 검증한다. 이번 출처 대조에서는 W 6개년, X 11개년, Y 14개년의 이론 176문제와 실험/지필 실험 49문제, 원문 PDF 423개를 확인했다. 이론 자료는 319개 PDF이며 423개 전체가 다운로드·파싱 검증을 통과했다. 검증 결과는 `tmp/source-audit/rupho-selection/report.json`에 남긴다.
