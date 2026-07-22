import json
import re
import shutil
from pathlib import Path

SRC = Path(r"C:\Users\mmb26\AppData\Local\Temp\claude\D--project-Ark-Creature-stats\3363c478-cbbc-4b51-a35d-aaaa722ddbb2\scratchpad\gdre\HextechRunes_extracted\HextechRunes")
LOC = SRC / "localization" / "kor"
IMG = SRC / "images"
OUT = Path(__file__).parent
ICONS = OUT / "assets" / "icons"


def fix_text(s: str) -> str:
    # 커뮤니티에서 쓰는 용어에 맞춰 "룬" 표기를 "증강"으로 통일
    return s.replace("룬", "증강")


# extract_card_vars.py가 생성한 카드 수치 (없으면 플레이스홀더 그대로 둠)
CARD_VARS_FILE = Path(__file__).parent / "card_vars.json"
CARD_VARS = json.loads(CARD_VARS_FILE.read_text(encoding="utf-8")) if CARD_VARS_FILE.exists() else {}

PLACEHOLDER_RE = re.compile(r"\{(\w+)(?::[^}]*)?\}")


# extract_rune_registry.py가 생성한 증강 등급/직업 정보
RUNE_REGISTRY_FILE = Path(__file__).parent / "rune_registry.json"
RUNE_REGISTRY = json.loads(RUNE_REGISTRY_FILE.read_text(encoding="utf-8")) if RUNE_REGISTRY_FILE.exists() else {}

CHARACTER_NAMES = {
    "Ironclad": "아이언클래드",
    "Silent": "사일런트",
    "Regent": "리젠트",
    "Defect": "디펙트",
    "Necrobinder": "네크로바인더",
}

TIER_NAMES = {"Silver": "실버", "Gold": "골드", "Prismatic": "프리즘"}


# 게임 본체 CardKeyword 열거형의 한국어 표기
KEYWORD_NAMES = {
    1: "소모",       # Exhaust
    2: "천상",       # Ethereal
    3: "선천성",     # Innate
    4: "사용 불가",  # Unplayable
    5: "보존",       # Retain
    6: "교활",       # Sly
    7: "영원",       # Eternal
}


def card_keywords(item_id: str):
    """카드 키워드 표시 목록.

    - 기본 키워드: "소모"
    - 강화 시 제거: "소모(소모X)"
    - 강화 시 추가: "(보존)"
    """
    kw = CARD_VARS.get(item_id, {}).get("_keywords")
    if not kw:
        return None
    base = kw.get("base", [])
    added = kw.get("added", [])
    removed = kw.get("removed", [])
    out = []
    for k in base:
        name = KEYWORD_NAMES.get(k, f"키워드{k}")
        out.append(f"{name}({name}X)" if k in removed else name)
    for k in added:
        if k not in base:
            name = KEYWORD_NAMES.get(k, f"키워드{k}")
            out.append(f"({name})")
    return out or None


def card_cost(item_id: str):
    """카드 에너지 코스트 표시 문자열: "1" 또는 강화 시 변하면 "1(0)"."""
    cost = CARD_VARS.get(item_id, {}).get("_cost")
    if cost is None:
        return None
    s = str(cost["base"])
    if "upgrade" in cost:
        s += f"({cost['base'] + cost['upgrade']})"
    return s


def resolve_card_vars(item_id: str, desc: str) -> str:
    """설명의 {Damage} 같은 플레이스홀더를 DLL에서 추출한 실제 수치로 치환."""
    vars_ = CARD_VARS.get(item_id)
    if not vars_ or not desc:
        return desc

    def value_of(name: str):
        v = vars_.get(name)
        # 로컬라이제이션이 WishBlock처럼 표시용 이름을 쓰는 경우 원본 변수로 폴백
        if v is None and name.startswith("Wish"):
            v = vars_.get(name[4:])
        if v is None:
            return None
        if v["base"] == 0:
            return "X"  # 게임 내 동적 값 (게임도 X로 표시)
        s = str(v["base"])
        if v.get("upgrade"):
            # 강화 후 수치를 소괄호에 표시: 6(9) = 기본 6, 강화 시 9
            s = f"{v['base']}({v['base'] + v['upgrade']})"
        return s

    def sub(m, wrap: bool):
        val = value_of(m.group(1))
        if val is None:
            return m.group(0)
        return f"[blue]{val}[/blue]" if wrap else val

    # 이미 [blue]로 감싸진 플레이스홀더는 값만 치환
    desc = re.sub(
        r"\[blue\]\{(\w+)(?::[^}]*)?\}",
        lambda m: "[blue]" + (value_of(m.group(1)) or m.group(0)[6:]),
        desc,
    )
    # 나머지는 [blue]로 감싸서 치환
    return PLACEHOLDER_RE.sub(lambda m: sub(m, wrap=True), desc)


def snake_to_camel(name: str) -> str:
    parts = name.lower().split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def load_loc(filename: str) -> dict:
    data = json.loads((LOC / filename).read_text(encoding="utf-8"))
    items = {}
    for key, value in data.items():
        m = re.match(r"^(.*)\.(title|description|flavor|smartDescription)$", key)
        if not m:
            continue
        item_id, field = m.groups()
        items.setdefault(item_id, {})[field] = value
    return items


FORGE_TIER_ICON = {
    "SILVER_": "silverForge.png",
    "GOLD_": "goldForge.png",
    "PRISMATIC_": "prismaticForge.png",
}

FORGE_TIER_NAMES = {
    "SILVER_": "실버",
    "GOLD_": "골드",
    "PRISMATIC_": "프리즘",
}


def copy_icon(img_dir: Path, filename: str, icon_out_subdir: str):
    src = img_dir / filename
    if not src.exists():
        return None
    dest = ICONS / icon_out_subdir / filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dest)
    return f"assets/icons/{icon_out_subdir}/{filename}"


def build_category(loc_file: str, image_subdir: str, category: str, icon_out_subdir: str):
    items = load_loc(loc_file)
    img_dir = IMG / image_subdir
    results = []
    for item_id, fields in items.items():
        if "title" not in fields:
            continue
        if not re.match(r"^[A-Z0-9_]+$", item_id):
            continue
        camel = snake_to_camel(item_id)
        icon_rel = None
        subcategory = category

        # 등급: 증강은 DLL 레지스트리에서, 모루는 ID 접두사에서
        tier = TIER_NAMES.get((RUNE_REGISTRY.get(item_id) or {}).get("tier"))

        is_forge = category == "relic" and "_FORGE" in item_id
        if is_forge:
            subcategory = "forge"
            tier_file = None
            for prefix, fname in FORGE_TIER_ICON.items():
                if item_id.startswith(prefix):
                    tier_file = fname
                    tier = FORGE_TIER_NAMES[prefix]
                    break
            tier_file = tier_file or "silverForge.png"
            icon_rel = copy_icon(img_dir, tier_file, icon_out_subdir)
        else:
            icon_rel = copy_icon(img_dir, f"{camel}.png", icon_out_subdir)

        desc = resolve_card_vars(item_id, fix_text(fields.get("description", fields.get("smartDescription", ""))))

        # 카드 키워드: 보존/선천성 계열은 설명 맨 앞 줄, 소모 등 나머지는 맨 끝 줄에 표시
        keywords = card_keywords(item_id) if category == "card" else None
        kw_top = [k for k in (keywords or []) if any(n in k for n in ("보존", "선천성"))] or None
        kw_bottom = [k for k in (keywords or []) if k not in (kw_top or [])] or None

        results.append({
            "id": item_id,
            "category": category,
            "subcategory": subcategory,
            "cost": card_cost(item_id) if category == "card" else None,
            "kw_top": kw_top,
            "kw_bottom": kw_bottom,
            "character": CHARACTER_NAMES.get((RUNE_REGISTRY.get(item_id) or {}).get("character")),
            "tier": tier,
            "title": fix_text(fields.get("title", "")),
            "description": desc,
            "flavor": fix_text(fields.get("flavor", "")),
            "icon": icon_rel,
        })
    return results


def main():
    all_items = []
    all_items += build_category("relics.json", "relics", "relic", "relics")
    all_items += build_category("cards.json", "cards", "card", "cards")
    all_items += build_category("powers.json", "powers", "power", "powers")

    all_items.sort(key=lambda x: (x["category"], x["title"]))

    (OUT / "data.json").write_text(
        json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    counts = {}
    for it in all_items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    print("Extracted counts:", counts)
    print("Total:", len(all_items))
    missing_icons = [it["id"] for it in all_items if it["icon"] is None]
    print("Missing icons:", len(missing_icons), missing_icons[:10])


if __name__ == "__main__":
    main()
