# -*- coding: utf-8 -*-
r"""게임 본체 아틀라스(card_atlas / power_atlas)에서 바닐라 카드/효과 아이콘을 크롭해
assets/icons/vanilla/ 에 저장하고, data.json의 vanilla 항목에 icon 경로를 채운다.

사전 준비 (scratchpad에 GDRE로 추출):
  - <ATLAS_DIR>/card_atlas.tpsheet, card_atlas_0.png, card_atlas_1.png
  - <ATLAS_DIR>/power_atlas.tpsheet, power_atlas.png
아틀라스 PNG는 GDRE recover로 .ctex→png 변환 필요(소스+.godot/imported 경로 모두 include).

실행: python extract_vanilla_icons.py  (그 후 build_data.py 재실행 불필요 — data.json 직접 갱신)
"""
import json
from pathlib import Path

from PIL import Image

ATLAS_DIR = Path(r"C:\Users\mmb26\AppData\Local\Temp\claude\D--project-Ark-Creature-stats\3cd6324f-d6dd-45ba-8181-153e4b982d5b\scratchpad\atlas\images\atlases")
OUT = Path(__file__).parent
ICON_DIR = OUT / "assets" / "icons" / "vanilla"

# 아틀라스 스프라이트명이 로컬라이제이션 ID와 다른 경우 별칭 (item base 소문자 → 스프라이트 basename)
SPRITE_ALIASES = {
    # INKED 효과는 아틀라스에 없음 → 크롭 생략(placeholder 유지)
}

# 카드/효과 크롭 후 목표 크기(원본 비율 유지, 파일 크기 절약)
MAX_SIZE = 220


def load_sheet(name: str):
    """tpsheet를 읽어 { 스프라이트_basename: (Image, region) } 반환."""
    sheet = json.loads((ATLAS_DIR / f"{name}_atlas.tpsheet").read_text(encoding="utf-8"))
    index = {}
    for tex in sheet["textures"]:
        img = Image.open(ATLAS_DIR / tex["image"]).convert("RGBA")
        for s in tex["sprites"]:
            base = s["filename"].split("/")[-1].rsplit(".", 1)[0]
            index.setdefault(base, (img, s["region"]))
    return index


def main():
    data = json.loads((OUT / "data.json").read_text(encoding="utf-8"))
    vanilla = [d for d in data if d.get("vanilla")]

    card_idx = load_sheet("card")
    power_idx = load_sheet("power")
    ICON_DIR.mkdir(parents=True, exist_ok=True)

    done, miss, icon_map = 0, [], {}
    for v in vanilla:
        base = v["id"][len("VANILLA_"):].lower()
        base = SPRITE_ALIASES.get(base, base)
        idx = power_idx if v["category"] == "power" else card_idx
        if base not in idx:
            miss.append(v["title"])
            continue
        img, r = idx[base]
        crop = img.crop((r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]))
        if max(crop.size) > MAX_SIZE:
            scale = MAX_SIZE / max(crop.size)
            crop = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.LANCZOS)
        fname = f"{v['id']}.png"
        crop.save(ICON_DIR / fname)
        v["icon"] = f"assets/icons/vanilla/{fname}"
        icon_map[v["id"]] = v["icon"]
        done += 1

    # build_data.py가 재빌드 시에도 아이콘을 붙일 수 있게 매핑 파일로 저장
    (OUT / "vanilla_icons.json").write_text(
        json.dumps(icon_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (OUT / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"크롭 완료: {done}개, 미매칭: {len(miss)} {miss}")


if __name__ == "__main__":
    main()
