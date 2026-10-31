# 하슬라논술 스캔 방식 이식

기준은 [HaslaEdu/nonsul의 `24b8036037cb227237bd2fe75023f7b4d7472ef0`](https://github.com/HaslaEdu/nonsul/tree/24b8036037cb227237bd2fe75023f7b4d7472ef0)입니다. 로컬 작업 중인 논술 코드가 아닌 GitHub에 저장된 버전을 참조했습니다.

- 이미지 처리: [`src/api/scanner.js`](https://github.com/HaslaEdu/nonsul/blob/24b8036037cb227237bd2fe75023f7b4d7472ef0/src/api/scanner.js)
- 촬영·확인 흐름: [`src/screens/Scan.jsx`](https://github.com/HaslaEdu/nonsul/blob/24b8036037cb227237bd2fe75023f7b4d7472ef0/src/screens/Scan.jsx)
- OCR 요청·응답 처리: [`src/api/ocr.js`](https://github.com/HaslaEdu/nonsul/blob/24b8036037cb227237bd2fe75023f7b4d7472ef0/src/api/ocr.js), [`supabase/functions/ocr/index.ts`](https://github.com/HaslaEdu/nonsul/blob/24b8036037cb227237bd2fe75023f7b4d7472ef0/supabase/functions/ocr/index.ts)

`scanner.js`의 원근 보정, A4 200 DPI, 2400px 작업 크기, 그림자 보정과 흑백 처리는 이미 같은 코드였습니다. HaslaLab 답안지의 네 검은 표식 탐지는 유지합니다. 추가 품질 손실이 나던 업로드 재압축과 편집용 JPEG를 개선해, 용량 안에 들어오는 PNG·JPEG·WebP는 그대로 전송하고 보정 반복 시 무손실 기준 이미지를 사용합니다. 용량을 맞추려고 해상도를 계속 15%씩 줄이던 동작은 제거했습니다.

Upstage 요청은 같은 `POST https://api.upstage.ai/v1/document-digitization`을 사용합니다. 일반 문서는 `model=ocr`, 수식 문서는 `model=document-parse`, `ocr=force`, `output_formats=["markdown"]`, `coordinates=true`입니다. 별도의 enhanced 모드나 새 OCR 제공자를 추가하지 않았습니다. 키는 기존 Worker Secret `UPSTAGE_API_KEY`만 사용하며 브라우저로 보내지 않습니다.

Upstage 원문과 LaTeX·신뢰도 정보를 보존하고, Gemini의 항목·그림 구조화는 보조 정보로 사용합니다. 채점 입력에도 인식 원문을 전달합니다. Upstage가 실패하면 재시도 또는 재촬영할 상태로 남기며, 성공한 다른 엔진의 재필사로 몰래 바꾸지 않습니다. 실전 시험의 답안 수정 제한·QR 업로드 토큰·마감·채점 규정은 기존대로 유지합니다.

논술의 큰 파일 허용치를 그대로 복사하지 않은 이유는 저장 방식의 차이입니다. 현재 HaslaLab은 이미지와 인식 결과를 D1에 저장하며 한 행의 최대 크기는 2,000,000바이트입니다. 사진의 기존 서버 제한 1,900,000바이트와 클라이언트 제한 1,850,000바이트를 유지하고, 서버는 인식 결과를 합친 저장 크기도 확인합니다. 원문을 자르는 대신 명시적인 재촬영 상태를 사용합니다. 더 큰 원본 보관이 필요하면 기존 `LAB_PAGES` R2 바인딩을 구성한 후 저장 정책을 별도로 바꿔야 합니다.

검증에는 합성 A4 이미지와 로컬 Upstage·Gemini 응답을 사용합니다. 실제 학생 답안이나 유료 API를 자동 테스트에 사용하지 않습니다.

검은 표식이 없는 일반 A4도 종이 바깥 테두리로 찾습니다. 촬영 화면과 사진 보정은 같은 검출 함수를 사용하며, 네 변의 근거가 충분하고 초점·위치가 안정적인 경우에만 자동 촬영합니다. 경계가 불확실하면 직접 촬영한 뒤 「모서리 맞추기」에서 조정할 수 있습니다. 종이 모서리로 잡은 좌표에는 검은 표식용 여백 보정을 적용하지 않습니다. 이 처리는 기기 안에서 실행하며 별도 서버 요청이나 AI 사용료를 추가하지 않습니다.

`node --test tests/test-markerless-scanner.mjs tests/test-scan-quality.mjs tests/test-monthly-scan.cjs`로 표식 없는 용지·오인식·자동 촬영·기존 화질 보존을 검증합니다. `node tools/build-site-catalogue.cjs`는 촬영 화면·KMO 업로드·스캔 비교 화면의 공통 엔진 URL을 내용 해시로 갱신합니다.

참고: [Upstage API](https://console.upstage.ai/api/parse/document-parsing), [수식·좌표 출력](https://console.upstage.ai/docs/capabilities/parse/understanding-output), [D1 제한](https://developers.cloudflare.com/d1/platform/limits/).
