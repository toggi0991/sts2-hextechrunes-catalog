# -*- coding: utf-8 -*-
r"""HextechRunes.dll 디컴파일 소스의 HextechPlayerRuneRegistry에서
증강별 등급(실버/골드/프리즘)과 직업 전용 정보를 추출해 rune_registry.json 생성.

사용법: extract_card_vars.py와 동일하게 DECOMP 경로를 맞추고 실행.
형식: { "RUNE_ID": { "tier": "Silver|Gold|Prismatic", "character": "Ironclad|..."|null, "tag": "OUTPUT", "flags": "None" } }
"""
import json
import re
from pathlib import Path

DECOMP = Path(r"C:\Users\mmb26\AppData\Local\Temp\claude\D--project-Ark-Creature-stats\3cd6324f-d6dd-45ba-8181-153e4b982d5b\scratchpad\decomp\HextechRunes")
OUT = Path(__file__).parent / "rune_registry.json"

ENTRY_RE = re.compile(
    r"Rune<(\w+)>\(HextechRarityTier\.(\w+)"          # 클래스명, 등급
    r"(?:,\s*PlayerRuneFlags\.(\w+))?"                 # 플래그 (선택)
    r"(?:,\s*(?:PlayerRuneCharacterPool\.(\w+)|null))?"  # 직업 풀 (선택)
    r"(?:,\s*\d+)?"                                    # characterOrder (선택)
    r'(?:,\s*"(\w+)")?'                                # 태그 (선택)
    r"\)"
)


def main():
    src = (DECOMP / "HextechPlayerRuneRegistry.cs").read_text(encoding="utf-8", errors="replace")

    # 클래스명 → data.json 아이템 ID 매칭용: 소문자 영숫자로 정규화해 비교
    data = json.loads((Path(__file__).parent / "data.json").read_text(encoding="utf-8"))
    id_by_norm = {d["id"].replace("_", "").lower(): d["id"] for d in data}

    result = {}
    unmatched = []
    for cls, tier, flags, pool, tag in ENTRY_RE.findall(src):
        item_id = id_by_norm.get(cls.lower())
        if item_id is None:
            unmatched.append(cls)
            continue
        result[item_id] = {
            "tier": tier,
            "character": pool or None,
            "tag": tag or "COMPREHENSIVE",
            "flags": flags or "None",
        }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(result)}개 증강 → {OUT}")
    if unmatched:
        print(f"매칭 실패 {len(unmatched)}개: {unmatched[:10]}")


if __name__ == "__main__":
    main()
