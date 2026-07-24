# -*- coding: utf-8 -*-
r"""게임 본체(sts2.dll) 디컴파일 소스에서 바닐라 카드의 에너지 코스트를 추출해
vanilla_cost.json 생성. build_data.py가 재빌드 시 vanilla 카드에 cost를 채운다.

사전: ilspycmd로 sts2.dll을 프로젝트(-p)로 디컴파일 → MegaCrit.Sts2.Core.Models.Cards
실행: python extract_vanilla_cost.py  (그 후 build_data.py 재실행)
"""
import json
import re
from pathlib import Path

CARDS_DIR = Path(r"C:\Users\mmb26\AppData\Local\Temp\claude\D--project-Ark-Creature-stats\3cd6324f-d6dd-45ba-8181-153e4b982d5b\scratchpad\game_decomp\MegaCrit.Sts2.Core.Models.Cards")
OUT = Path(__file__).parent
DATA = OUT / "data.json"

BASE_RE = re.compile(r":\s*base\((-?\d+)\s*,")
UP_RE = re.compile(r"EnergyCost\.UpgradeBy\((-?\d+)\)")


def pascal(base_id: str) -> str:
    return "".join(p.capitalize() for p in base_id.lower().split("_"))


def cost_for(class_name: str):
    f = CARDS_DIR / f"{class_name}.cs"
    if not f.exists():
        return None
    src = f.read_text(encoding="utf-8", errors="replace")
    m = BASE_RE.search(src)
    if not m:
        return None
    cost = int(m.group(1))
    if cost < 0:
        return "-"  # 사용 불가/저주 등
    # 강화 시 코스트 변경
    up = UP_RE.search(src)
    if up:
        upgraded = cost + int(up.group(1))
        if upgraded != cost:
            return f"{cost}({upgraded})"
    return str(cost)


def main():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    vanilla_cards = [d for d in data if d.get("vanilla") and d["category"] == "card"]

    cost_map, miss = {}, []
    for v in vanilla_cards:
        base = v["id"][len("VANILLA_"):]
        c = cost_for(pascal(base))
        if c is None:
            miss.append(v["title"])
            continue
        cost_map[v["id"]] = c

    (OUT / "vanilla_cost.json").write_text(
        json.dumps(cost_map, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"코스트 추출: {len(cost_map)}개 / 미매칭 {len(miss)}: {miss}")


if __name__ == "__main__":
    main()
