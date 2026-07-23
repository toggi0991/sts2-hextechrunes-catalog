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

# 모드 번역이 게임 공식 명칭과 다른 용어 별칭
TERM_ALIASES = {
    "영체화": "불가침",          # Intangible
    "집중": "밀집",              # Focus
    "단검": "단도",              # Shiv
    "교활함": "교활",            # Sly
    "드림캐쳐": "드림캐처",
    "미니어쳐 텐트": "미니어처 텐트",
    "전기 구체": "번개 구체",    # Ball Lightning
    "회오리바람": "소용돌이",    # Whirlwind
}


def clean_placeholders(desc: str) -> str:
    """게임 내 동적 값 플레이스홀더 정리: {X:choose(...)}는 제거, 나머지는 X로 표시."""
    desc = re.sub(r"\{[^{}]*:choose\([^{}]*\}", "", desc)
    return re.sub(r"\{[^{}]*\}", "X", desc)


# 게임 본체 CardKeyword 열거형의 공식 한국어 표기 (game_localization/kor/card_keywords.json 기준)
KEYWORD_NAMES = {
    1: "소멸",     # Exhaust
    2: "휘발성",   # Ethereal
    3: "선천성",   # Innate
    4: "사용불가", # Unplayable
    5: "보존",     # Retain
    6: "교활",     # Sly
    7: "영구",     # Eternal
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


def build_keyword_info(all_items) -> dict:
    """키워드/효과 툴팁 사전 생성: { 용어: 설명 }.

    출처: 게임 본체 card_keywords.json + powers.json (공식 한국어) + 모드 효과 항목.
    """
    info = {}
    game_loc = Path(__file__).parent / "game_localization" / "kor"

    # 게임 본체: 카드/유물/구체/기본 개념/고난/파워 — 모두 <ID>.title/.description 구조.
    # 같은 이름이 겹치면 뒤 파일이 우선이므로, 툴팁으로 자주 쓰이는 파워를 마지막에 둠
    # (예: "영체화"는 카드가 아니라 파워 의미로 연결)
    for fname in ("cards.json", "relics.json", "orbs.json", "static_hover_tips.json", "afflictions.json", "powers.json"):
        f = game_loc / fname
        if not f.exists():
            continue
        data = json.loads(f.read_text(encoding="utf-8"))
        for key, title in data.items():
            if not key.endswith(".title"):
                continue
            base = key[: -len(".title")]
            desc = data.get(f"{base}.description") or data.get(f"{base}.smartDescription")
            if title and desc:
                info[title] = desc

    # 모드 항목(효과/카드/증강)이 게임 본체와 이름이 겹치면 모드 설명을 우선
    for it in all_items:
        if it["title"] and it["description"]:
            info[it["title"]] = it["description"]

    # 카드 키워드는 마지막에 덮어써서 항상 공식 정의 유지
    ck = game_loc / "card_keywords.json"
    if ck.exists():
        data = json.loads(ck.read_text(encoding="utf-8"))
        for key, title in data.items():
            if key.endswith(".title"):
                desc = data.get(key[: -len(".title")] + ".description")
                if desc:
                    info[title] = desc

    for alias, target in TERM_ALIASES.items():
        if target in info:
            info[alias] = info[target]

    result = {k: clean_placeholders(v) for k, v in info.items()}
    # 클라이언트의 바로 이동에서 별칭을 공식 명칭으로 풀 수 있게 함께 내보냄
    result["__aliases__"] = dict(TERM_ALIASES)
    return result


def build_vanilla_items(all_items):
    """모드 설명에서 참조되는 바닐라(게임 본체) 카드/효과를 도감 항목으로 추가."""
    game_loc = Path(__file__).parent / "game_localization" / "kor"

    # 모드 항목 설명 속 [gold] 참조 용어 수집 (별칭은 공식 명칭으로 변환)
    refs = set()
    for it in all_items:
        for m in re.findall(r"\[gold\](.*?)\[/gold\]", it["description"]):
            t = re.sub(r"\[.*?\]", "", m).strip()
            if t and not t[0].isdigit():
                refs.add(TERM_ALIASES.get(t, t))

    existing = {it["title"] for it in all_items}
    out = []
    for fname, category in (("cards.json", "card"), ("powers.json", "power")):
        data = json.loads((game_loc / fname).read_text(encoding="utf-8"))
        seen = set()
        for key, title in data.items():
            if not key.endswith(".title"):
                continue
            if title not in refs or title in existing or title in seen:
                continue
            base = key[: -len(".title")]
            desc = data.get(f"{base}.description") or data.get(f"{base}.smartDescription")
            if not desc:
                continue
            seen.add(title)
            out.append({
                "id": f"VANILLA_{base}",
                "category": category,
                "subcategory": category,
                "cost": None,
                "kw_top": None,
                "kw_bottom": None,
                "character": None,
                "tier": None,
                "vanilla": True,
                "title": title,
                "description": clean_placeholders(desc),
                "flavor": data.get(f"{base}.flavor", ""),
                "icon": None,
            })
    return out


def main():
    all_items = []
    all_items += build_category("relics.json", "relics", "relic", "relics")
    all_items += build_category("cards.json", "cards", "card", "cards")
    all_items += build_category("powers.json", "powers", "power", "powers")

    vanilla = build_vanilla_items(all_items)
    all_items += vanilla
    print("Vanilla items:", len(vanilla))

    all_items.sort(key=lambda x: (x["category"], x["title"]))

    (OUT / "data.json").write_text(
        json.dumps(all_items, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    keyword_info = build_keyword_info(all_items)
    (OUT / "keywords.json").write_text(
        json.dumps(keyword_info, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Keyword info:", len(keyword_info))

    counts = {}
    for it in all_items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1
    print("Extracted counts:", counts)
    print("Total:", len(all_items))
    missing_icons = [it["id"] for it in all_items if it["icon"] is None]
    print("Missing icons:", len(missing_icons), missing_icons[:10])


if __name__ == "__main__":
    main()
