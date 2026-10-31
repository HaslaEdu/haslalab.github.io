# 기기 내 답안 사진 스캔

카메라 사진을 서버에 올리기 전에 문서의 네 모서리를 찾고 원근을 보정합니다. 이 단계는 OCR과 분리돼 있으며 사진은 브라우저 메모리와 Worker 안에서만 처리됩니다. 사용자가 전송을 누를 때 기존 시험·월간문제 업로드 경로를 사용합니다. 계정 토큰, QR 소유권, 제출·채점 규칙은 이 모듈에서 바꾸지 않습니다.

`scanner.js` → `document-detector.mjs` → `document-worker.mjs`가 지연 로드됩니다. Worker는 DocAligner LCNet-100 ONNX 모델의 네 모서리 heatmap을 해석하고 원본 작업 크기의 실제 경계로 좌표를 다듬습니다. 종이의 원근이 강해도 A4 정면 비율로 거르지 않습니다. 네 인쇄 표식이 충분히 확실한 기존 답안지는 모델 추론을 생략합니다. 원근 변환, 화질 검사, 필터, 이미지 인코딩도 Worker에서 실행합니다. 오래된 프레임 응답은 요청 ID로 배제하고 취소한 대기 비트맵은 닫습니다. 진행 중인 네이티브 추론 자체를 중단할 수는 없습니다.

기본 출력은 `mode: 'original'`, `pageFormat: 'auto'`입니다. 색 그래프·화살표·기하 도형을 남기며, auto는 검출한 변의 비율을 사용합니다. 실제 용지 크기나 정확한 원래 종횡비를 단안 사진만으로 측정하는 기능은 아닙니다. A4를 직접 선택하면 기존 200dpi A4 출력으로 맞춥니다. A3/A5를 A4와 자동 구별한다고 주장하지 않습니다. 출력의 짧은 변은 기본 1654px, 긴 변 상한은 3200px입니다.

모델·브라우저 기능이 없거나 경계 검증이 불확실하면 자동 촬영과 자동 크롭을 하지 않습니다. 전체 작업 이미지를 유지하고 사용자가 모서리를 확인할 수 있게 합니다. 이때 흑백·그림자 필터도 자동 적용하지 않습니다. 수동 보정은 Worker가 없어도 동작하지만 그 환경에서는 변환 연산이 메인 스레드에서 실행됩니다. 작업 기준 이미지는 긴 변 최대 2400px로 읽은 무손실 PNG이며 카메라 원본 파일 자체와 같다는 뜻은 아닙니다.

## 정적 모델과 라이선스

- DocAligner LCNet-100: [원본 프로젝트](https://github.com/DocsaidLab/DocAligner), Apache-2.0. 고정 모델 4,767,987바이트와 SHA-256은 `document-model.mjs`에 있습니다.
- 모델 배포·heatmap 해석 참고: [quadscan](https://github.com/storrealbac/quadscan), [ml-web-scanner](https://github.com/andor83/ml-web-scanner), MIT. 고정 커밋·출처·모델 해시는 `vendor/docaligner-lcnet/NOTICE.md`, 각 라이선스도 같은 폴더에 포함합니다.
- [ONNX Runtime Web](https://github.com/microsoft/onnxruntime/tree/v1.20.1), 1.20.1, MIT. CPU WASM과 런타임·제3자 고지는 `vendor/onnxruntime-web-1.20.1/`에 있습니다. 외부 CDN이나 새 유료 서비스는 사용하지 않습니다.

스캐너를 처음 사용할 때 모델+WASM 약 16MB와 작은 JS 런타임을 같은 출처에서 받습니다. 일반 홈페이지 로딩에는 포함하지 않습니다. 모델과 WASM의 길이·SHA-256을 검증한 뒤 버전별 Cache Storage에 저장합니다. 저장하는 것은 공개 정적 파일뿐이며 사진·토큰·인식 결과는 캐시하지 않습니다. 캐시 불일치는 삭제 후 다시 받고, 실패하면 수동 모드로 남습니다. 한 Worker의 준비 실패는 반복 다운로드하지 않으며 다음 페이지 방문에서 다시 시도할 수 있습니다. 저사양 기기의 실제 속도와 오프라인 첫 실행은 보장하지 않습니다.

## 호출 계약

`processShot(file, { mode?, pageFormat?, corners?, signal?, onProgress? })`는 `blob`, 편집 기준 `baseUrl`, `corners`, `cornersReliable`, `method`, 화질·크기와 아래 필드를 돌려줍니다.

- `warpApplied`: 검증 또는 사용자 확인한 모서리로 원근 보정했는지 여부.
- `outputFormat`: `'auto' | 'a4'`. `a4WarpApplied`는 `warpApplied && outputFormat === 'a4'`인 호환 필드입니다.
- `paperStatus`: 문서 경계 또는 수동 확인 상태이며 실제 A4 크기 인증이 아닙니다.

`reprocess(baseUrl, corners, mode, dpi, inset, { preserveOriginal?, pageFormat?, signal? })`는 동일한 무손실 기준 이미지로 다시 보정합니다. 보정 미확인 사진은 `preserveOriginal: true`를 유지해야 합니다. `editCorners(..., { marker, lang, pageFormat })`는 `{ corners, marker, pageFormat }`을 반환하고 사용자가 auto/A4를 고릅니다. 기존 인쇄 마커에만 `MARKER_INSET`을 사용합니다.

## 검증

`node --test tests/test-document-model.mjs tests/test-markerless-scanner.mjs tests/test-scan-quality.mjs tests/test-monthly-scan.cjs`로 순수 계산·취소·기존 흐름을 확인합니다. 실제 브라우저 검사는 `node --test tests/test-document-ml-browser.cjs`입니다. Playwright 모듈 경로 `HASLA_PLAYWRIGHT_PATH`와 설치된 Chrome 경로 `CHROME_BIN`을 지정할 수 있습니다. 시험은 로컬 서버와 실제 고정 모델을 사용하며 외부 요청을 차단합니다. 모델 제공자나 유료 OCR은 호출하지 않습니다.

CC0 합성 사진 `tests/fixtures/scanner-graph-photo.jpg`로 강한 원근, 색 그래프와 방향 화살표, 실제 모서리 오차·색 보존, 메인 스레드 진행, 자산 캐시 재사용을 검사합니다. 결과는 `tmp/scanner-ml-qa/`에 저장합니다. 이는 실제 Chrome 검증이며 다양한 실제 휴대폰·사용자 필기 사진 전체의 품질 검증을 대신하지 않습니다. QR 업로드의 기존 1,850,000바이트 제한과 서버 저장 제한은 그대로 적용합니다.
