# STS2 HextechRunes 도감

슬레이 더 스파이어 2(STS2) 스팀 창작마당 증강모드 "海克斯符文(HextechRunes)"의 룬/모루/카드/효과를 한 곳에서 검색할 수 있는 정적 웹페이지입니다.

## 사용

`index.html`을 정적 호스팅(GitHub Pages 등)으로 열면 됩니다. 별도 빌드 과정 없이 순수 HTML/CSS/JS + `data.json`으로 동작합니다.

로컬에서 직접 열어볼 때는 `file://`로는 `data.json`을 fetch할 수 없으므로 로컬 서버가 필요합니다.

```
python -m http.server 8743
```

또는 `run.bat`을 더블클릭하세요.

## 데이터 출처 및 갱신

`data.json`과 `assets/icons/`는 워크샵 모드 `HextechRunes.pck`에서 [GDRE Tools](https://github.com/GDRETools/gdsdecomp)로 추출한 로컬라이제이션 텍스트/이미지를 가공한 것입니다. 모드가 업데이트되면:

1. GDRE Tools로 `.pck`를 다시 추출
2. `build_data.py` 안의 `SRC` 경로를 추출 위치로 맞추고 재실행
3. 갱신된 `data.json` / `assets/icons/`를 커밋

## 주의

- 이 저장소의 아이콘과 텍스트는 워크샵 모드 제작자의 리소스이며, 모드 자체가 리그 오브 레전드(라이엇 게임즈)의 "핵스텍" 테마를 차용하고 있습니다. 원작자 및 IP 홀더의 권리를 침해하지 않는 선에서 개인/커뮤니티 참고용으로만 사용해 주세요.
- 설명 중 `{Damage}`, `{Cards}` 같은 값은 게임 내 등급(실버/골드/프리즘)에 따라 동적으로 계산되는 수치라 고정값으로 표시되지 않습니다.
