# 기기 내 답안 사진 스캔 (v2)

카메라 사진을 서버에 올리기 전에 종이의 네 모서리를 찾아 원근을 보정하고 또렷하게(clean) 다듬습니다. 모든 계산은 브라우저 안에서 끝나며 **외부 요청이 없습니다**(모서리 모델은 이 사이트에서 받습니다). 사용자가 전송을 누를 때 기존 시험·월간문제 업로드 경로를 사용합니다. 계정 토큰, QR 소유권, 제출·채점 규칙은 이 모듈에서 바꾸지 않습니다.

## 종이 찾기 (v2, nonsul 스캐너 방식)

v1의 DocAligner 모델(ONNX, 약 16MB)은 종이가 화면 밖으로 나가거나 반사광이 있으면 엉뚱한 사각형을 잡았습니다(합성 4000px 사진에서 모서리 오차 175–275px). v2는 HaslaEdu/nonsul의 스캐너처럼 **밝은 종이 영역**에서 출발합니다. `scanner.js`의 `findPage`:

1. **영역** — 약 320px 사본에서 화소마다 «종이다움»(밝고 무채색: 나무·책상·천은 색이 있거나 어둡습니다)을 계산하고 3×3 최댓값으로 글씨의 영향을 지웁니다. Otsu 문턱(과 그 위·아래 구간의 두 번째 문턱)으로 나눈 조각들을 얇은 선이 끊지 않도록 닫은 뒤, 네 변 모양을 꽉 채우는(0.82–1.12) 조각 중 크고 가운데 있는 것을 고릅니다. 밝은 바탕 위의 회색 종이도 매끈하고 주변보다 분명히 어두우면 고릅니다.
2. **책상 위 종이** — 고른 영역 안에 더 밝고 테두리에 닿지 않으며 경계가 계단처럼 뚜렷한 사각형이 있으면 그것이 종이입니다(반사광은 경계가 흐려 제외).
3. **네 변** — 영역의 볼록 껍질을 넷으로 줄이고, 약 1600px 사본에서 각 변의 법선 64개를 따라 «바깥에서 종이 밝기로 들어가는 첫 경계»를 찾아 직선을 맞춥니다(바닥 이음매는 안쪽이 나무라서, 답안 칸 선은 그 바깥에 진짜 가장자리가 있어서 제외). 이웃 직선의 교점이 모서리입니다.
4. **확인** — 사진 밖으로 나간 변이 없고 변마다 경계가 충분히 보이면 `verified`(=`cornersReliable`). 사진 밖으로 나간 종이는 보이는 부분으로 자르되 `clipped`, 확인 필요로 둡니다. 자동 촬영은 네 변이 강하고 A4 모양(정면 또는 원근을 푼 비율이 A4에서 7% 이내)일 때만 합니다.

합성 장면(4000×3000)에서 모서리 오차: 나무 바닥 1–4px, 어두운 책상 1px, 반사광 2px, 사진 밖으로 나간 종이 ~20px(보이는 부분 기준). 한 장 약 0.1–0.3초입니다.

## 학습된 모서리 모델 (DocCornerNet, scanic-ml)

어지러운 책상·흰 종이 위 흰 종이처럼 밝기만으로 종이가 구분되지 않는 사진을 위해, Worker는 [scanic](https://github.com/marquaye/scanic)(MIT)의 **DocCornerNet LEAN** 모서리 모델과 그 전용 최소 ONNX Runtime(1.5MB, gzip 0.55MB)을 함께 돌립니다. 파일은 `vendor/scanic-ml-0.2.0/`, 로더는 `vendor/scanic-1.7.1/`에 두고 이 사이트에서만 받습니다(CDN·API 없음, 이후 브라우저 캐시). 모델은 큰 가중치 48개를 fp16으로 담은 `doccornernet_lean.f16.bin`(1.09MB, 전송 gzip 0.84MB; 원본 .ort는 1.93MB, gzip 1.67MB)으로 받아 Worker에서 원래의 fp32 모델로 되살려 돌립니다(`decodeCornerModel`, 한 번 약 40ms). 그래서 추론 속도는 그대로이고(약 21ms), 모서리 차이는 고정 사진에서 0.01px, 합성 장면에서 224px 입력 기준 최대 0.44px입니다. INT8은 최대 15px(224px 기준) 어긋나서 쓰지 않습니다. 처음 한 번 받는 양은 모델·런타임 합쳐 약 1.4MB(gzip)입니다. 다시 만들기: `python3 tools/pack_corner_model.py <scanic-ml 0.2.0의 doccornernet_lean.ort> vendor/scanic-ml-0.2.0/doccornernet_lean.f16.bin`. 모델이 낸 사각형도 같은 변 맞춤(`findPage`의 seed)을 거치고, `chooseDocument`가 고릅니다: 두 결과가 같은 종이면 측정이 확인된 쪽, 다르면 네 변이 더 잘 측정된 쪽, 둘 다 확인되지 않으면 자신 있는(0.8 이상) 모델 쪽. 인쇄 마커는 언제나 우선합니다. 합성 장면에서 어지러운 책상 254px → 2px, 그림자만 있는 흰 책상의 흰 종이 (없음) → 3px.

인쇄 마커가 있는 답안지는 지금처럼 마커로 찾습니다(`MARKER_INSET`).

## 출력

기본은 `mode: 'clean'`, `pageFormat: 'a4'`(200dpi, 1654×2339)입니다. 펴기는 작업 사본(2400px)이 아니라 원본 사진에서 종이 부분만 잘라(짧은 변 최대 2400px) Worker에서 합니다. 결과의 `sourceBlob`을 `reprocess(..., { source })`로 넘기면 모서리를 고쳐도 원본 해상도를 유지합니다.

## 실시간 카메라

하슬라 논술 스캐너처럼 **셔터를 누르면 테두리를 그린 바로 그 영상 프레임**을 그 테두리로 스캔합니다. 휴대폰의 별도 정지 사진(ImageCapture)은 찍지 않습니다. 정지 사진은 화각·노출·플래시가 달라 종이를 다시 찾아야 했고, 테두리는 맞았는데 책상이 찍히는 원인이었습니다. 영상은 4:3, 최대 4032×3024를 요청하고 가능하면 연속 초점을 켭니다. 프레임은 긴 변 3840px까지 보관합니다. 테두리가 없거나 1.5초보다 오래됐으면 지금 프레임을 찍어 다시 찾습니다.

## 호출 계약

`processShot(file, { mode?, pageFormat?, corners?, detectionHint?, signal?, onProgress? })`는 `blob`, 편집 기준 `baseUrl`, `corners`, `cornersReliable`, `method`(`page` | `marker` | `manual` | `frame`), `paperStatus`, `warpApplied`, `outputFormat`, `sourceBlob`, 화질·크기를 돌려줍니다. `reprocess(baseUrl, corners, mode, dpi, inset, { preserveOriginal?, pageFormat?, source?, signal? })`, `editCorners(..., { marker, lang, pageFormat, signal })`는 v1과 같습니다.

## 검증

`node --test tests/test-markerless-scanner.mjs tests/test-scan-quality.mjs tests/test-monthly-scan.cjs`(순수 계산), 브라우저: `tests/test-scan-engine-browser.cjs`, `tests/test-scan-camera-browser.cjs`, `tests/test-scan-resolution-browser.cjs`(`HASLA_PLAYWRIGHT_PATH`, `CHROME_BIN`). 합성 사진은 실제 휴대폰·필기 사진 전체의 품질 검증을 대신하지 않습니다.
