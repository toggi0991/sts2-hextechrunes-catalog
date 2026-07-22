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
            s += f"(+{v['upgrade']})"
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

        is_forge = category == "relic" and "_FORGE" in item_id
        if is_forge:
            subcategory = "forge"
            tier_file = None
            for prefix, fname in FORGE_TIER_ICON.items():
                if item_id.startswith(prefix):
                    tier_file = fname
                    break
            tier_file = tier_file or "silverForge.png"
            icon_rel = copy_icon(img_dir, tier_file, icon_out_subdir)
        else:
            icon_rel = copy_icon(img_dir, f"{camel}.png", icon_out_subdir)

        results.append({
            "id": item_id,
            "category": category,
            "subcategory": subcategory,
            "title": fix_text(fields.get("title", "")),
            "description": resolve_card_vars(item_id, fix_text(fields.get("description", fields.get("smartDescription", "")))),
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
