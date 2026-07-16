# 내 주변 T멤버십

SKT T멤버십 제휴 브랜드(전체 183개, 17개 카테고리)를 내 위치 기준 지도에서 바로 찾아주는 웹앱.
카카오맵 API로 주변 매장을 검색하고, 등급별(VIP/Gold/Silver) 할인 정보와 T멤버십 이용 링크를 보여줍니다.
매장이 없는 온라인/구독형 혜택(카드, 스트리밍, 온라인몰 등)은 지도에는 안 뜨고 검색으로만 찾을 수 있어요.

## 파일 구조

```
index.html                          앱 전체 (지도, 검색, 필터 UI + 로직)
benefits.json                       혜택 데이터 (183개 브랜드, 17개 카테고리)
scripts/check_benefits.py           공식 카탈로그를 통째로 다시 긁어서 benefits.json과 비교하는 스크립트
scripts/requirements.txt            스크립트 의존성 (beautifulsoup4)
.github/workflows/check-benefits.yml 매주 자동 실행 + 변경 시 PR 생성
```

## 데이터 소스

인덱스: `https://sktmembership.tworld.co.kr/mps/pc-bff/benefitbrand/list-tab2.do`
("혜택 브랜드 한눈에 보기" — 카테고리별 브랜드 전체 목록, 183개)

브랜드별 상세: `https://sktmembership.tworld.co.kr/mps/pc-bff/benefitbrand/detail.do?brandId={id}`
(등급별 할인율이 여기 있음. 인덱스 페이지 자체엔 할인율이 없음)

## 매장형(store) vs 온라인(online) 분류

카테고리 단위로 분류했습니다. 브랜드 하나하나가 아니라 카테고리 전체 기준이라 일부 오차가 있을 수 있습니다.

지도에 마커로 표시되는 store 카테고리: 영화/공연/전시, 베이커리, 외식, 카페/아이스크림, 피자/치킨, 편의점, 교통, 키즈(ZEM), 테마파크

검색으로만 찾아지고 지도엔 안 뜨는 online 카테고리: 쇼핑, 패션/뷰티, 여행, 반려동물, 생활/건강, 금융/통신, 교육, 콘텐츠

예를 들어 "여행" 카테고리엔 SK렌터카·면세점처럼 실제 매장이 있는 곳도 섞여 있지만, 항공권·여행자보험처럼 순수 온라인 예약도 많아서 카테고리 전체를 online으로 뒀습니다.
특정 브랜드만 예외로 두고 싶으면 benefits.json에서 그 항목의 location_type만 직접 store로 바꾸면 됩니다.
다음 자동 갱신 때 verified를 manual로 같이 바꿔두면 스크립트가 덮어쓰지 않습니다.

## 혜택 데이터는 어떻게 최신 상태로 유지되나

매주 월요일 09:00(KST)에 GitHub Actions가 공식 카탈로그 전체(183개)를 다시 긁어서 비교합니다.

값이 하나라도 바뀌면 benefits.json을 통째로 새로 만든 뒤 Pull Request를 자동으로 엽니다.
바로 반영/배포되지 않고, GitHub 알림(메일/웹)으로 확인한 뒤 준호님이 직접 Merge 해야 실제 앱에 반영됩니다.
값이 안 바뀌었으면 아무 일도 일어나지 않습니다.

공식 사이트에 새 카테고리가 생기면(scripts/check_benefits.py의 CAT_META에 없는 카테고리) 그 카테고리 브랜드는 자동으로 건너뛰고 GitHub Actions 로그에 경고만 남깁니다. CAT_META에 직접 추가해줘야 반영됩니다.

Actions 탭에서 "Run workflow" 버튼으로 언제든 수동 실행도 가능합니다.

## benefits.json 직접 수정하고 싶을 때

index.html은 열 필요 없습니다. benefits.json만 고쳐서 커밋하고 푸시하면 끝입니다.

브랜드 하나 통째로 추가/삭제하려면 benefits 배열에 항목을 추가/삭제하세요.

할인율만 수동으로 바꾸려면 해당 브랜드의 tiers 값을 수정하고, verified를 manual로 바꾸세요. 그러면 다음 자동 확인 때 그 브랜드는 덮어쓰지 않고 건너뜁니다. 다만 자동 확인은 카탈로그 전체를 다시 만드는 방식이라, verified가 manual인 항목도 인덱스에 남아있는 한 다음 실행 때 다시 덮어써질 수 있습니다. 완전히 손대지 못하게 하려면 scripts/check_benefits.py의 build_dataset() 함수에서 해당 id를 건너뛰도록 예외 처리가 필요합니다.

updated_at도 변경이 있을 때만 같이 바뀝니다. 앱 상단에 "OO 기준"으로 표시됩니다.

브랜드 항목 예시:

```json
{
  "id": "b1053",
  "name": "파리바게뜨",
  "keyword": "파리바게뜨",
  "cat": "bakery",
  "location_type": "store",
  "tiers": [["VIP / Gold", "천원당 100원 할인(모바일카드) / 50원 할인(플라스틱카드)"], ["Silver", "천원당 50원 할인"]],
  "note": "",
  "link": "https://sktmembership.tworld.co.kr/mps/pc-bff/benefitbrand/detail.do?brandId=1053",
  "verified": "scraped"
}
```

카테고리 아이콘/색은 브랜드마다가 아니라 categories 배열에서 카테고리 단위로 관리됩니다.

## 배포 전 필수 설정: Kakao Developers

Kakao Developers(developers.kakao.com) 사이트에서 해당 앱의 앱 설정, 플랫폼 키, Web 플랫폼 메뉴로 들어갑니다.

사이트 도메인에 이 저장소의 GitHub Pages 주소를 정확히 등록하세요. 예: `https://capjjunse.github.io/tmembership-nearby-map` (뒤에 슬래시나 하위 경로 없이 등록하는 걸 권장합니다)

제품 설정에서 카카오맵이 활성화(ON) 상태인지도 확인하세요.

이 두 가지가 안 되어 있으면 지도가 비어있고 "카카오맵을 불러오지 못했어요" 알림이 뜹니다.

참고: index.html에 들어있는 JavaScript 키는 원래 브라우저에서 노출되는 게 정상입니다. 실제 보안은 키를 숨기는 것이 아니라 위의 도메인 등록으로 이루어집니다. REST API 키나 어드민 키처럼 서버 전용 시크릿 키는 이 저장소에 넣지 않았습니다.

## GitHub Pages로 배포하기

이 저장소(capjjunse/tmembership-nearby-map)엔 이미 위 파일들이 푸시되어 있습니다.
GitHub 저장소의 Settings, Pages 메뉴에서 Source를 main 브랜치의 / (root)로 설정하면 몇 분 안에 `https://capjjunse.github.io/tmembership-nearby-map/` 주소로 열립니다.

이후 로컬에서 직접 수정해서 다시 올리고 싶다면 아래처럼 하면 됩니다.

```bash
git clone https://github.com/capjjunse/tmembership-nearby-map.git
cd tmembership-nearby-map
# 수정...
git add .
git commit -m "혜택 데이터 수정"
git push
```

주소를 확인한 뒤 위 "배포 전 필수 설정" 항목의 카카오 도메인 등록을 진행하세요.
