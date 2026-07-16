#!/usr/bin/env python3
"""
T멤버십 공식 "혜택 브랜드 한눈에 보기" 페이지(list-tab2.do)를 기준으로
전체 브랜드 카탈로그를 다시 만들어서 benefits.json과 비교한다.

- list-tab2.do 에서 카테고리별 브랜드 인덱스(브랜드ID) 를 가져오고
- 브랜드마다 detail.do?brandId=ID 를 호출해서 등급별(VIP/Gold/Silver) 할인 정보를 가져온다
- 새로 만든 데이터와 기존 benefits.json이 다르면 파일을 덮어쓰고 changed=True

GitHub Actions가 이 스크립트를 실행하고, 변경이 있으면 Pull Request를 연다
(자동으로 바로 반영/배포하지 않음 — 검증 없는 값이 그대로 나가는 걸 막기 위해서).

새로운 카테고리가 생기면(공식 사이트에 신규 카테고리 추가) CAT_META에 없는 카테고리로 잡히고,
그 카테고리의 브랜드는 이번 갱신에서 건너뛰고 경고만 출력한다 — 사람이 CAT_META에 추가해줘야 함.
"""
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

INDEX_URL = "https://sktmembership.tworld.co.kr/mps/pc-bff/benefitbrand/list-tab2.do"
DETAIL_URL = "https://sktmembership.tworld.co.kr/mps/pc-bff/benefitbrand/detail.do?brandId={id}"
BENEFITS_PATH = Path(__file__).resolve().parent.parent / "benefits.json"
REQUEST_DELAY_SEC = 0.15

# 카테고리(한글명) -> {id, icon, color, location_type}
# location_type: "store"(지도에 매장 표시) / "online"(지도 표시 안 함, 검색에서만 노출)
CAT_META = {
    "영화/공연/전시": {"id": "movie", "icon": "🎬", "color": "#7c5cff", "location_type": "store"},
    "베이커리": {"id": "bakery", "icon": "🥐", "color": "#ff8a5c", "location_type": "store"},
    "외식": {"id": "dining", "icon": "🍽️", "color": "#ff5c8a", "location_type": "store"},
    "카페/아이스크림": {"id": "cafe", "icon": "☕", "color": "#22b8cf", "location_type": "store"},
    "피자/치킨": {"id": "pizza", "icon": "🍕", "color": "#ff5c5c", "location_type": "store"},
    "편의점": {"id": "cvs", "icon": "🏪", "color": "#22c55e", "location_type": "store"},
    "교통": {"id": "traffic", "icon": "🚗", "color": "#16a34a", "location_type": "store"},
    "키즈(ZEM)": {"id": "kids", "icon": "🧸", "color": "#fb923c", "location_type": "store"},
    "테마파크": {"id": "theme", "icon": "🎢", "color": "#ef4444", "location_type": "store"},
    "쇼핑": {"id": "shopping", "icon": "🛍️", "color": "#fbbf24", "location_type": "online"},
    "패션/뷰티": {"id": "fashion", "icon": "💄", "color": "#ec4899", "location_type": "online"},
    "여행": {"id": "travel", "icon": "✈️", "color": "#06b6d4", "location_type": "online"},
    "반려동물": {"id": "pet", "icon": "🐾", "color": "#f472b6", "location_type": "online"},
    "생활/건강": {"id": "life", "icon": "🧺", "color": "#a78bfa", "location_type": "online"},
    "금융/통신": {"id": "finance", "icon": "💳", "color": "#64748b", "location_type": "online"},
    "교육": {"id": "education", "icon": "📚", "color": "#3b82f6", "location_type": "online"},
    "콘텐츠": {"id": "content", "icon": "🎵", "color": "#8b5cf6", "location_type": "online"},
}
CAT_ORDER = list(CAT_META.keys())

GRADE_LABELS = {
    frozenset(["vip"]): "VIP",
    frozenset(["gold"]): "Gold",
    frozenset(["silver"]): "Silver",
    frozenset(["white"]): "White",
    frozenset(["vip", "gold"]): "VIP / Gold",
    frozenset(["gold", "silver"]): "Gold / Silver",
    frozenset(["vip", "gold", "silver"]): "전 등급",
    frozenset(["vip", "gold", "silver", "white"]): "전 등급",
}


def fetch(url: str) -> str:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; tmembership-bot/1.0)"})
    with urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", errors="replace")


def grade_label(grades: list[str]) -> str:
    return GRADE_LABELS.get(frozenset(grades), " / ".join(g.capitalize() for g in grades))


def clean_text(raw: str, grades: list[str]) -> str:
    letters = {"vip": "V", "gold": "G", "silver": "S", "white": "L"}
    text = raw.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    for g in grades:
        letter = letters.get(g, "")
        if letter:
            text = re.sub(rf"^\s*{letter}\s+", "", text)
    return text.strip()


def parse_brand_index(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for cate_box in soup.select(".cate-box"):
        top = cate_box.select_one(".cate-top")
        cat_name = top.get("data-text") if top else None
        for a in cate_box.select("a.benefit-box"):
            out.append({"id": a.get("data-id"), "name": a.get_text(strip=True), "category": cat_name})
    return out


def parse_detail_tiers(html: str):
    soup = BeautifulSoup(html, "html.parser")
    dl = soup.select_one("dl.dl-bnf")
    if not dl:
        return None
    dd = dl.find("dd")
    if not dd:
        return None
    tiers = []
    for info in dd.select("div.info"):
        grades = []
        for badge in info.select("i.badge-circle"):
            for g in ["vip", "gold", "silver", "white"]:
                if g in (badge.get("class") or []):
                    grades.append(g)
        if not grades:
            continue
        text = clean_text(info.get_text(" ", strip=True), grades)
        if "포인트 사용" in text or "포인트 적립" in text:
            continue
        tiers.append([grade_label(grades), text])
    return tiers or None


def make_keyword(name: str) -> str:
    kw = re.sub(r"\(.*?\)", "", name).strip()
    kw = kw.split("/")[0].strip()
    return kw or name


def build_dataset() -> dict:
    index = parse_brand_index(fetch(INDEX_URL))

    unknown_cats = sorted({item["category"] for item in index if item["category"] not in CAT_META})
    if unknown_cats:
        print(f"⚠️  CAT_META에 없는 새 카테고리 발견, 이번엔 건너뜀: {unknown_cats}", file=sys.stderr)

    benefits = []
    for i, item in enumerate(index):
        meta = CAT_META.get(item["category"])
        if not meta:
            continue
        html = fetch(DETAIL_URL.format(id=item["id"]))
        tiers = parse_detail_tiers(html)
        time.sleep(REQUEST_DELAY_SEC)
        if not tiers:
            print(f"⚠️  {item['name']}(id={item['id']}) 할인 정보를 못 찾음, 건너뜀", file=sys.stderr)
            continue
        benefits.append(
            {
                "id": f"b{item['id']}",
                "name": item["name"],
                "keyword": make_keyword(item["name"]),
                "cat": meta["id"],
                "location_type": meta["location_type"],
                "tiers": tiers,
                "note": "",
                "link": DETAIL_URL.format(id=item["id"]),
                "verified": "scraped",
            }
        )
        if i % 30 == 0:
            print(f"{i}/{len(index)} 진행중...", file=sys.stderr)

    categories = [
        {
            "id": CAT_META[k]["id"],
            "label": k,
            "color": CAT_META[k]["color"],
            "icon": CAT_META[k]["icon"],
            "location_type": CAT_META[k]["location_type"],
        }
        for k in CAT_ORDER
    ]

    return {
        "source": "https://sktmembership.tworld.co.kr/mps/pc-bff/benefitbrand/list-tab2.do",
        "source_detail": DETAIL_URL,
        "categories": categories,
        "benefits": benefits,
    }


def main() -> int:
    old = json.loads(BENEFITS_PATH.read_text(encoding="utf-8")) if BENEFITS_PATH.exists() else {}
    new = build_dataset()

    # updated_at은 비교에서 제외 (내용이 같으면 날짜만 바뀌었다고 PR 열지 않음)
    old_compare = {"categories": old.get("categories"), "benefits": old.get("benefits")}
    new_compare = {"categories": new["categories"], "benefits": new["benefits"]}
    changed = old_compare != new_compare

    if changed:
        from datetime import date

        new["updated_at"] = date.today().strftime("%Y.%m.%d")
        BENEFITS_PATH.write_text(json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"변경 있음 · 브랜드 {len(new['benefits'])}개로 갱신")
    else:
        print("변경 없음")

    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
