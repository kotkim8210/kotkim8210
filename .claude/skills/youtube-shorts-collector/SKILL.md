---
name: youtube-shorts-collector
description: Claude Code 전용 YouTube 쇼츠 데이터 수집 자동화 스킬. yt-dlp로 미국 Creative Commons 쇼츠의 조회수·채널 구독자·좋아요·업로드일·영상 길이·라이선스·인기 댓글(좋아요순)을 자동 수집하고 V/S 비율(조회수÷구독자)을 계산해서, youtube-shorts-creator(큐레이션 스킬)의 Stage 0.5부터 바로 이어받을 인수인계 마크다운을 생성한다. 검색 모드(해시태그 CC필터 검색으로 후보 발굴)와 시드 모드(사용자가 URL 직접 제공) 지원. 일반 채팅 Claude가 유튜브 조회수·댓글을 직접 못 긁는 한계를 Claude Code의 yt-dlp 실행으로 해결. 사용자가 "쇼츠 수집", "유튜브 댓글 긁기", "조회수 수집", "떡상 영상 데이터", "CC 영상 검색", "yt-dlp", "collect.py", "영상 메타데이터", "인기 댓글 수집", "쇼츠 후보 발굴"을 언급하거나, 큐레이션 전에 영상 데이터를 자동 수집하고 싶을 때 사용. 수집 후에는 youtube-shorts-creator 스킬로 넘겨 대본·현지화·스토리보드를 만든다.
---

# YouTube Shorts Collector (Claude Code 전용)

`yt-dlp`로 유튜브 쇼츠의 큐레이션용 데이터를 자동 수집한다. 전체 시스템 맥락은 이 폴더의 `CLAUDE.md` 참고.

> **이 저장소에서의 위치**: 이 스킬은 `.claude/skills/youtube-shorts-collector/`에 설치되어 있다.
> 아래 모든 경로(`scripts/`, `output/`)는 **이 스킬 폴더 기준**이다. 실행 전 반드시
> `cd .claude/skills/youtube-shorts-collector` 후 실행할 것 (저장소 루트의 `scripts/`와 다른 폴더임).
> 수집 결과는 이 폴더의 `output/`에 저장되며 git에는 커밋되지 않는다.

## 무엇을 수집하나

- 조회수 · 채널 구독자 수 · 좋아요 · 업로드일 · 영상 길이
- 라이선스 (Creative Commons 여부 자동 판정)
- **인기 댓글 (좋아요순)** — 큐레이션 Stage 3 주제 결정의 핵심
- V/S 비율(조회수÷구독자) 자동 계산

## 사전 준비 (최초 1회)

```bash
pip install -U yt-dlp
```
자세히는 `setup.md`.

## 스크립트 구성

| 스크립트 | 역할 | 단독 실행 |
|---------|-----|--------|
| `scripts/collect.py` | **메인**. 검색/시드 → 메타+댓글 → 인수인계 MD 생성 | 아래 참고 |
| `scripts/search_cc.py` | CC 필터 검색만 | `python scripts/search_cc.py "#piano #shorts"` |
| `scripts/fetch_meta.py` | 한 영상 메타만 | `python scripts/fetch_meta.py "URL"` |
| `scripts/fetch_comments.py` | 한 영상 댓글만 | `python scripts/fetch_comments.py "URL" --top 15` |

## 메인 사용법

### 검색 모드 (Claude가 후보 발굴)

```bash
python scripts/collect.py --query "#piano #shorts" --min-views 5000000 --top 8
```

- `--query`: 해시태그 검색어 (CC 필터 자동 적용)
- `--min-views`: 최소 조회수 (1000만 최우선이면 `10000000`, 500만이면 `5000000`)
- `--top`: 상세 수집할 상위 N개 (기본 8)
- `--comments`: 인수인계에 넣을 댓글 수 (기본 15)

### 시드 모드 (사용자가 URL 제공)

```bash
python scripts/collect.py --urls "URL1" "URL2" "URL3"
```

사용자가 이미 CC 필터로 골라온 영상들의 데이터만 수집. 가장 정확하고 빠름.

## 출력

`output/collected_YYYYMMDD_HHMM.md` (인수인계) + `.json` (원본 데이터)

인수인계 MD에는:
- CC 아닌 영상은 "제외 대상"으로 분리
- CC 영상은 조회수순 표 (V/S·길이·업로드·유형힌트 포함)
- 영상별 인기 댓글 표
- CC BY 크레딧 작성용 원본 채널·설명
- 저작권 재확인 경고 (배경음악 등)

## 수집 후 → 큐레이션 스킬로

생성된 인수인계 MD를 **youtube-shorts-creator 스킬의 Stage 0.5(장르 분기)**로 넘긴다. 이미 조회수·댓글·CC가 확보돼 있어 그 스킬의 Stage 0(사용자 수동 수집)은 건너뛴다.

## 장르별 검색어 (검색 모드용)

| 장르 | 해시태그 |
|-----|--------|
| 음악·악기 | `#piano` `#guitar` `#violin` `#cello` `#cover` `#fingerstyle` |
| 미술·페인팅 | `#painting` `#drawing` `#speedpainting` `#watercolor` `#calligraphy` |
| 감성 라이프스타일 | `#aesthetic` `#lifestyle` `#morningroutine` `#cozy` |
| 자기계발·철학 | `#stoicism` `#mindset` `#motivation` `#discipline` |

## 주의 (수집기가 판단 못 하는 것)

- 영상 속 **배경음악**이 상업 음원이면 CC여도 재업로드 위험 → 사람이 확인, BGM 교체
- 음악 연주는 **연주 대상 곡**의 저작권 확인 (클래식·자작곡 안전)
- 유형(M/P) 힌트는 참고용, 확정은 Stage 0.5에서
- 연령제한·비공개 영상은 수집 실패 가능

## 트러블슈팅

- `yt-dlp 미설치` → `pip install -U yt-dlp`
- 수집 0개 → 조회수 필터 낮추거나 다른 해시태그
- 댓글 안 긁힘 → 해당 영상 댓글 비활성일 수 있음. 다른 영상으로
- 자주 실패 → `pip install -U yt-dlp`로 최신화 (유튜브 변경 대응)
