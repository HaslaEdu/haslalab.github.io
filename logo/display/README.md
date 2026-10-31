# 로고 표시용 벡터 복원본

공식 고해상도 벡터를 확보하지 못한 두 표장을 기존 래스터의 윤곽·색·비율에 맞춰 복원했습니다. 공식 배포 벡터가 아닌 표시용 파생 자산입니다. 원래 PNG는 변경하지 않고 보존합니다.

- `kmchc.svg`, `kmchc-dark.svg`: 공식 화학올림피아드 계정의 기존 104×128 표장에서 빨강·파랑 곡선을 추적하고 중앙 육각형·원을 정리했습니다. 내부는 투명하며 다크 모드는 선의 대비와 색 밝기만 보완합니다. [공식 포털](https://olympiad.kchem.org/), [추적 기록](kmchc-provenance.json).
- `wopho.svg`: 기존 500×132 표장의 다섯 글자 외곽·구멍·기울기를 추적했습니다. 원본에서 채취한 무지개색 그라디언트와 벡터 입체 효과를 사용하며 글꼴을 대체하지 않았습니다. [2011 공식 문제지](https://olimpicos.net/files/wopho/WoPhO_2011_Q1.pdf)의 표장과 대조했습니다. 문서 내 큰 비트맵도 작은 이미지를 늘린 것이어서 새 고해상도 원본으로 취급하지 않았습니다. [추적 기록](wopho-provenance.json).

저장소 루트에서 재현:

```sh
python tools/trace_kmchc.py logo/kmchc.png logo/display
python tools/restore_wopho_vector.py logo/wopho.png logo/display --smooth --name wopho
python tools/build_logo_variants.py
node tools/build-site-catalogue.cjs
```

추적 도구는 Pillow·NumPy를 사용하며 원본 파일을 읽기만 합니다. 최종 SVG는 폰트·외부 파일·비트맵 삽입 없이 경로와 그라디언트로 렌더링됩니다.
