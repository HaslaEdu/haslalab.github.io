# 대회 로고 출처

로고가 없던 13개 대회를 보완하고, 국기로 대신 표시하던 BAUPC·CPhO·RuPhO 및 RuPhO W/X/Y를 공식 표장으로 교체했습니다. 별도 대회 로고를 확인할 수 없는 경우 공식 주최기관의 표장을 사용하며, 화면의 로고 설명과 아래 출처 기록에서 구분합니다. RuPhO W/X/Y는 전러시아 학생 올림피아드 공통 표장을 공유합니다.

원본 파일은 원래 색과 비율을 보존합니다. 다크 모드에서는 별도 SVG 표시본을 사용합니다. 외곽 배경을 투명하게 처리하고 어두운 글자·선을 밝게 표시해 흰 사각 받침 없이 읽을 수 있게 합니다. 표시본과 원본 해시는 [variants.json](variants.json)에 기록하며, `tools/build_logo_variants.py`로 다시 생성할 수 있습니다.

KMO·AMC·Putnam·USABO·USNCO·RuPhO는 글자 내부의 닫힌 공간에 남은 종이색도 다크 표시본에서 제거합니다. AMC·Putnam의 다면체와 USNCO ACS 문장의 흰 면은 보존하며 라이트 표시본은 유지합니다.

USAAAO·AMC·Eötvös·RuPhO는 가장자리에서 배경색과 섞인 색·투명도를 복원한 SVG 표시본을 사용합니다. USAAAO의 AAA 안쪽 배경을 제거하고 AMC 다면체의 흰 면, Eötvös의 초상·글자·진한 타원선은 보존합니다. 보정 범위와 픽셀 수는 `variants.json`의 `darkMatteCleanup`에 기록합니다.

KMChC·WOPhO는 저해상도 원본을 확대하지 않고, 원래 실루엣과 색을 따른 [표시용 벡터 복원본](display/README.md)을 사용합니다. 공식 배포 벡터 원본과 구분하며 기존 PNG는 보존합니다. 표시본은 라이트·다크 모드 모두에 적용됩니다.

| 키 | 구분 | 공식 출처 |
|---|---|---|
| ortvay | 공식 문제지 제목 표장 | [출처](https://ortvay.elte.hu/) |
| eotvos | 주최기관 표장 | [출처](https://elft.hu/eotvos-lorand-fizikaverseny-2026/) |
| plancks | 2026 국제 결선 공식 표장 | [출처](https://plancks2026.verenigingspin.nl/) |
| baupc | 주최기관 표장 | [출처](https://liquids.seas.harvard.edu/penanen/competition/welcome.html) |
| cpho | 주최기관 표장 | [출처](https://www.cps-net.org.cn/Home/Content/show/id/905.do) |
| rupho | 대회·공통 표장 | [출처](https://vserosolimp.edsoo.ru/brendbook) |
| ruphow | 대회·공통 표장 | [출처](https://vserosolimp.edsoo.ru/brendbook) |
| ruphox | 대회·공통 표장 | [출처](https://vserosolimp.edsoo.ru/brendbook) |
| ruphoy | 대회·공통 표장 | [출처](https://vserosolimp.edsoo.ru/brendbook) |
| kmchc | KChO·KMChC 공통 대회 표장 | [출처](https://olympiad.kchem.org/) |
| usnco | USNCO 전용 워드마크 | [출처](https://www.sazacs.org/) |
| apao | 중앙 공식 사이트 공통 표장 | [출처](http://www.issp.ac.ru/iao/apao/img/logo.html) |
| usabo | 대회·공통 표장 | [출처](https://www.cee.org/programs/usa-biolympiad) |
| mskbo | 한국중학생생물대회 전용 표장 (현 중학생생물챌린지) | [출처](https://mskbo.bioedu.kr/) |
| ceso | 대회·공통 표장 | [출처](https://ceso.ssoc.org.cn/) |
| jeso | 대회·공통 표장 | [출처](https://x.com/jesojp) |
| usaaao | 주최기관 표장 | [출처](https://x.com/USA__AAO) |
| kmo | 대회·공통 표장 | [출처](https://www.kmo.or.kr/main.html) |
| kumc | 주최기관 표장 | [출처](https://www.kms.or.kr/) |
| cmo | 주최기관 표장 | [출처](https://www.cms.org.cn/competition/NationalMiddleSchoolMathematicsWinterCamp.html) |
| amc | AMC 프로그램 표장 | [출처](https://maa.edvistas.com/datamate/studentlogin.aspx) |
| usamo | 공식 교사용 매뉴얼 제목 표장 (2004) | [출처](https://maa.org/maa-invitational-competitions/) |
| putnam | Putnam 전용 표장 | [출처](https://math.artsandsciences.baylor.edu/news/story/2021/2021-baylor-putnam-team) |

원본 이미지 주소와 자르기 내역: [물리](sources-physics.json), [과학](sources-science.json), [수학](sources-math.json). USAMO·Ortvay는 실제 문서의 제목을 사용하며 별도 영구 심벌로 주장하지 않습니다. Eötvös 원본은 유지하고 표시 크기만 조정했습니다.
