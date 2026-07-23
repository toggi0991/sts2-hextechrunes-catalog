# -*- coding: utf-8 -*-
r"""HextechRunes.dll 디컴파일 소스에서 카드 수치(DynamicVar)를 추출해 card_vars.json 생성.

사용법:
  1. ilspycmd로 모드 DLL을 디컴파일:
     dotnet ilspycmd.dll -p -o <출력폴더> "<워크샵경로>\lib\<버전>\HextechRunes.dll"
  2. DECOMP 경로를 디컴파일 출력의 HextechRunes 폴더로 맞추고 실행:
     python extract_card_vars.py
  3. 생성된 card_vars.json을 커밋하고 build_data.py 재실행

card_vars.json 형식: { "CARD_ID": { "VarName": { "base": 6, "upgrade": 3 } } }
base가 0인 변수(예: 골골이의 소원)는 게임 내 동적 값이라 "X"로 표시됨.
"""
import json
import re
from pathlib import Path

DECOMP = Path(r"C:\Users\mmb26\AppData\Local\Temp\claude\D--project-Ark-Creature-stats\3cd6324f-d6dd-45ba-8181-153e4b982d5b\scratchpad\decomp\HextechRunes")
OUT = Path(__file__).parent / "card_vars.json"

# 클래스명 접미사 Var → 로컬라이제이션 플레이스홀더 이름
BUILTIN_VAR_NAMES = {
    "DamageVar": "Damage",
    "BlockVar": "Block",
    "HealVar": "Heal",
    "EnergyVar": "Energy",
    "CardsVar": "Cards",
    "GoldVar": "Gold",
    "StarsVar": "Stars",
    "RepeatVar": "Repeat",
    "MaxHpVar": "MaxHp",
    "SummonVar": "Summon",
}


def camel(card_id: str) -> str:
    return "".join(p.capitalize() for p in card_id.lower().split("_"))


def num(s: str):
    v = float(s)
    return int(v) if v == int(v) else v


def parse_canonical_vars(src: str) -> dict:
    """CanonicalVars 프로퍼티에서 변수 이름과 기본값을 파싱."""
    m = re.search(r"CanonicalVars\s*=>(.*?);\n", src, re.S)
    if not m:
        return {}
    body = m.group(1)
    vars_ = {}
    # new DynamicVar("Name", 9m)
    for name, val in re.findall(r'new DynamicVar\("(\w+)",\s*(\d+(?:\.\d+)?)m\)', body):
        vars_[name] = {"base": num(val)}
    # new PowerVar<IntangiblePower>(1m)
    for name, val in re.findall(r"new PowerVar<(\w+)>\((\d+(?:\.\d+)?)m?\)", body):
        vars_[name] = {"base": num(val)}
    # new DamageVar(12m, ...) / new EnergyVar(2) / new CardsVar(2)
    for cls, val in re.findall(r"new (\w+Var)\((\d+(?:\.\d+)?)m?[,)]", body):
        name = BUILTIN_VAR_NAMES.get(cls)
        if name:
            vars_[name] = {"base": num(val)}
    return vars_


def parse_cost(src: str, vars_: dict):
    """생성자 첫 인자(에너지 코스트)와 강화 시 코스트 변화를 파싱."""
    m = re.search(r":\s*base\((\d+)[,)]", src)
    if not m:
        return
    cost = {"base": int(m.group(1))}
    m = re.search(r"EnergyCost\.UpgradeBy\((-?\d+)\)", src)
    if m:
        cost["upgrade"] = int(m.group(1))
    vars_["_cost"] = cost


def parse_keywords(src: str, vars_: dict):
    """CanonicalKeywords(기본 키워드)와 강화 시 키워드 추가/제거를 파싱."""
    kw = {}
    m = re.search(r"CanonicalKeywords\s*=>(.*?);\n", src, re.S)
    if m:
        base = [int(v) for v in re.findall(r"\(CardKeyword\)(\d+)", m.group(1))]
        if base:
            kw["base"] = base
    up = re.search(r"protected override void OnUpgrade\(\)\s*\{(.*?)\n\t\}", src, re.S)
    if up:
        added = [int(v) for v in re.findall(r"AddKeyword\(\(CardKeyword\)(\d+)\)", up.group(1))]
        removed = [int(v) for v in re.findall(r"RemoveKeyword\(\(CardKeyword\)(\d+)\)", up.group(1))]
        if added:
            kw["added"] = added
        if removed:
            kw["removed"] = removed
    if kw:
        vars_["_keywords"] = kw


def parse_upgrades(src: str, vars_: dict):
    """OnUpgrade 안의 UpgradeValueBy 상수를 변수에 매핑."""
    m = re.search(r"protected override void OnUpgrade\(\)\s*\{(.*?)\n\t\}", src, re.S)
    if not m:
        return
    body = m.group(1)
    # DynamicVars["Name"].UpgradeValueBy(1m) 또는 DynamicVars.Name).UpgradeValueBy(4m)
    for name, val in re.findall(r'DynamicVars\["(\w+)"\]\.UpgradeValueBy\((\d+(?:\.\d+)?)m\)', body):
        if name in vars_:
            vars_[name]["upgrade"] = num(val)
    for name, val in re.findall(r"DynamicVars\.(\w+)\)*\.UpgradeValueBy\((\d+(?:\.\d+)?)m\)", body):
        if name in vars_:
            vars_[name]["upgrade"] = num(val)


# 정규식으로 파싱 불가한 특수 케이스 수동 지정
MANUAL_OVERRIDES = {
    # 불태우는 일격: 강화 공식 n(n+7)/2+12 (무제한 강화). 1강 기준 12→16이므로 +4로 표기
    "SEARING_ATTACK_CARD": {"Damage": {"upgrade": 4}},
}


def parse_class_sources(cs_path: Path) -> str:
    """카드 클래스 소스에 부모 클래스(CardModel 제외) 소스를 이어붙여 반환.

    예: DragonSoulCardBase.OnUpgrade의 AddKeyword(선천성)를 자식 카드들이 상속.
    자식이 같은 멤버를 오버라이드하면 자식 정의가 먼저 매치되도록 자식 소스를 앞에 둠.
    """
    src = cs_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"class \w+ : (\w+)", src)
    base = m.group(1) if m else None
    if base and base != "CardModel":
        base_file = DECOMP / f"{base}.cs"
        if base_file.exists():
            src += "\n" + base_file.read_text(encoding="utf-8", errors="replace")
    return src


def main():
    # data.json의 카드 ID 목록 기준으로 디컴파일 소스 매칭
    data = json.loads((Path(__file__).parent / "data.json").read_text(encoding="utf-8"))
    card_ids = [d["id"] for d in data if d["category"] == "card"]

    result = {}
    for card_id in card_ids:
        cs = DECOMP / f"{camel(card_id)}.cs"
        if not cs.exists():
            print(f"[skip] {card_id}: {cs.name} 없음")
            continue
        src = parse_class_sources(cs)
        vars_ = parse_canonical_vars(src)
        parse_upgrades(src, vars_)
        parse_cost(src, vars_)
        parse_keywords(src, vars_)
        for name, patch in MANUAL_OVERRIDES.get(card_id, {}).items():
            vars_.setdefault(name, {}).update(patch)
        result[card_id] = vars_
        print(card_id, vars_)

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(result)}개 카드 → {OUT}")


if __name__ == "__main__":
    main()
