---
title: AI 영상편집 자동화 — 5단계 골격과 냉정 리뷰 (Whisper·FFmpeg·Remotion)
slug: video-editing-automation
tags: [영상, 자동화, 스킬, ffmpeg, whisper, remotion, 리뷰]
created: 2026-06-14
updated: 2026-06-14
sources: [2026-06-14-video-automation-article-review.md, "https://min-inter.co.kr/wiki/video-editing-automation-whisper-ffmpeg-remotion/"]
related: [[video-skills]], [[my-projects]], [[claude-code-skills]]
confidence: high
status: active
---

## 한 줄 요약
말 위주 영상 자동편집의 5단계 골격(입력분석→편집결정→컷→꾸미기→출력)과, min-inter 글을 내 실제 구현(`video-editor/`)과 냉정하게 비교한 결과 — 글은 정직·정확하나 **라우드니스 정규화가 빠졌고**, 양쪽의 최대 미개척 레버는 **LLM 내용컷(군말 제거)** 이다.

## 핵심 내용

### 5단계 골격 (어떤 영상 자동화든 매핑됨)
1. **입력분석** 음성→텍스트+타임코드 (Whisper/faster-whisper/WhisperX/Vrew)
2. **편집결정** 남길/버릴 구간 판단 — *의미 판단은 LLM에 위임* (군말·중복·횡설수설)
3. **컷 실행** 자르고 잇기 (ffmpeg `select`+`setpts` / auto-editor)
4. **꾸미기** 자막·모션그래픽·비율 (ffmpeg `subtitles`/`ass` / Remotion)
5. **출력** 인코딩 (libx264 / GPU `h264_nvenc` / Mac `videotoolbox`)
- 설계철학: **의미판단=AI, 시간계산=코드** · 단계마다 중간산출 저장(재개) · 무엇을→언제 순서.
- 저자도 인정한 한계: 미적 판단·감성 B-roll 선택은 자동화 불가 → "자동화=핸즈오프"가 아니라 "스크립트 보조".

### 냉정 리뷰 — 글이 맞고 내 구현(`video-editor/edit_videos.py`)이 이미 하는 것
faster-whisper STT, `silencedetect` 무음감지, 컷 후 `setpts/asetpts` 싱크, concat 규격 주의, 자막 번인, 중간산출 보존. → **방향성 일치(검증됨).**

### 글이 더 나은 것 (습득 대상)
- ⭐ **`--initial_prompt` 도메인 힌트** — 상품명·전문용어를 주면 한국어 정확도↑. → **즉시 습득(구현 완료)**: video-editor `--initial-prompt`.
- ⭐ **large-v3-turbo** — medium보다 정확, large-v3보다 빠르고 환청 적음(GPU 권장). → 도움말에 명시.
- **WhisperX** forced alignment — 단어 단위 정밀(노래방 자막·단어 컷). (torch+pyannote, 무거움)
- **Remotion** — React로 매 프레임 렌더, 복잡 모션그래픽. (Node+headless Chromium, 느림)
- **LLM 내용컷(2단계)** — 무음이 아닌 *군말·중복*을 제거. **내 도구엔 없음.**
- HW 인코더(nvenc/videotoolbox), 화자 분리(diarization).

### 내가 더 나은 것 (글에 없음 — 양방향 정직)
- ⭐ **라우드니스 정규화(EBU R128 loudnorm)** — 글에 **아예 없음.** 작게 녹음된 영상(실측 −77 dB)은 이게 없으면 "전부 무음"으로 99% 잘려나가고 자막도 빔. 실전 최대 함정 해결.
- 자동 규격통일(scale+pad 레터박스 → 해상도·방향 섞여도 합쳐짐). 글은 "같은 소스/재인코딩"만 언급.
- ASS 리치 스타일(커스텀 폰트·단어별 주황 강조·줌팝), 짤 오버레이(키워드 타이밍·줌인/아웃), 인트로/전환 SFX.
- 환청 억제 실전노하우: `word_timestamps`가 오히려 글자를 깸 → **문장 비례 분할 + 한글없는 큐 버리기**.

### 결론
글은 기술적으로 정직하고 명령들이 전부 실제로 맞다(서베이로서 우수). 내 구현은 한국어 쇼츠 특화 + 실전 강건성(loudnorm·규격통일)에서 앞서고, 글은 도구 폭(Remotion·WhisperX·HW가속·무코딩 Vrew)에서 앞선다.

## 연결고리 (Connections)
- [[video-skills]] — 기존 영상 스킬 3종(watch·youtube-shorts·osmu)과 같은 계열. 이 글은 그 토대가 되는 *파이프라인 이론*을 제공.
- [[my-projects]] — 쿠팡·인스타·유튜브 콘텐츠 운영에 직접 투입되는 실전 도구(`video-editor/`)의 근거.
- [[claude-code-skills]] — 결과물을 `/video-edit` 슬래시 스킬(`.claude/commands/video-edit.md`)로 박제 → 어느 세션서든 호출.

## 미해결/모순 (Open Questions)
- [미해결] **2단계 LLM 내용컷 미구현** — 무음이 아닌 군말·중복을 SRT 기반으로 LLM이 KEEP/CUT 판단. *다음 빌드 1순위 레버.*
- [확인필요] large-v3-turbo가 CPU(저음량 오디오)에서도 환청이 적은지 — GPU 없이 실측 미검증(현재는 medium 권장).
- [확인필요] Remotion 도입 ROI — 모션그래픽 이득 vs Node+Chromium 무게/속도. 어느 임계에서 ffmpeg ASS를 넘어서나.
