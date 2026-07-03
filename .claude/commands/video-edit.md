# /video-edit — AI 영상편집 자동화 플레이북

말 위주 영상(토킹헤드·강의·쇼츠)을 **무음 컷 → 합치기 → 한국어 자막 → 꾸미기 → 출력**까지
자동 편집하는 스킬. 구현체는 `video-editor/edit_videos.py`, 이론적 골격은 [[video-editing-automation]] 참고.

> 핵심 원칙(이 스킬이 따르는 설계): **"의미 판단은 AI, 시간 계산은 코드."**
> 무엇을 자를지(군말·중복) 같은 의미 판단만 LLM에 맡기고, 초 단위 더하기·타임코드 변환은 코드가 한다.

---

## 5단계 골격 (어떤 영상 자동화든 여기에 매핑된다)

| 단계 | 할 일 | 이 저장소의 도구 | 더 센 대안(상황별) |
|------|-------|------------------|--------------------|
| 1 입력분석 | 음성→텍스트+타임코드 | faster-whisper (`transcribe_to_cues`) | 단어정밀=WhisperX, 무코딩=Vrew |
| 2 편집결정 | 남길/버릴 구간 판단 | (현재 무음만) | **LLM에 SRT 주고 군말·중복 컷** ← 미구현, 최대 미개척 레버 |
| 3 컷 실행 | 자르고 잇기 | ffmpeg `select/aselect`+`setpts` | auto-editor / **PyCapCut draft**(비파괴 컷, 아래 '출력 모드 분기') |
| 4 꾸미기 | 자막·짤·효과음·비율 | ffmpeg `ass`/overlay (ASS 스타일·줌·SFX) | **Remotion**(복잡 모션그래픽) / CapCut 템플릿(draft 경로) |
| 5 출력 | 인코딩 | libx264 | GPU `h264_nvenc` / Mac `h264_videotoolbox` |

---

## 기본 실행

```bash
# 1) 준비물(최초 1회): ffmpeg + 한글폰트 + faster-whisper
bash video-editor/setup.sh

# 2) input/ 에 영상 넣고 실행 (이름순 합쳐짐)
python video-editor/edit_videos.py
# → output/edited_*.mp4 (+ .srt)
```

## 품질을 끌어올리는 핵심 옵션 (실전에서 검증된 것)

- **음성이 작게 녹음됐을 때**: 자동 라우드니스 정규화(EBU R128)가 기본 ON이라 그냥 돌리면 됨.
  (이게 없으면 조용한 영상은 "전부 무음"으로 잡혀 99% 잘려나간다 — 실측으로 확인된 함정.)
- **자막 정확도 ↑ (도메인 어휘 힌트)**: `--initial-prompt "상품명,전문용어,..."`
  예: `--initial-prompt "피그마,상세페이지,초당옥수수,제주다팜"` → 깨짐·환청 토큰 감소.
- **모델 선택**: 기본 `medium`. GPU 있으면 `--model large-v3-turbo`(정확·빠름).
  ⚠️ `large-v3`는 잡음·저음량 오디오에서 **영어 환청**이 늘 수 있음(실측). CPU만 있으면 medium이 무난.
- **자막 끊기/위치/강조**: `--max-chars 12 --margin-v 360 --highlight "피그마,AI,색상" --orange "#FF8C42"`
- **짤(밈) 삽입**: `--overlay '경로@자막키워드|대체키워드@지속초'` (키워드가 나오는 자막 시점에 줌인/줌아웃 오버레이)
- **효과음**: `assets/sound.wav`(인트로 두둥)·`assets/sound1.wav`(전환 휘릭) 자동. 끄기 `--no-intro-sound`.

## 자막 타임스탬프 함정 (반드시 기억)

- AI 타임스탬프는 미세하게 부정확 → 문장 단위로 그대로 자르면 끝음절이 잘리거나 다음 말이 묻어옴.
  → 말 구간 앞뒤 `--margin 0.2` 여유, 그리고 단어 타임스탬프 대신 **문장 비례 분할**을 쓴다
     (medium의 `word_timestamps`는 깨진 글자·환청을 유발 → 끄고 문장 단위 전사를 비례 분할).
- 컷 후 싱크 틀어짐 → `setpts=PTS-STARTPTS`/`asetpts` (이 도구는 `select` 필터에서 이미 처리).
- concat 실패 → 해상도·fps·코덱이 달라서. 이 도구는 **scale+pad 레터박스로 자동 규격 통일** 후 합침.

## 출력 모드 분기: ffmpeg 최종렌더 vs CapCut draft (PyCapCut) ⭐

같은 분석(무음컷·자막 cue·군말컷 결정)을 **두 가지로 내보낼 수 있다. 경쟁이 아니라 출력 분기다.**
분석의 단일 진실 공급원은 `edit_videos.py`(detect_silences 등)이고, 출력만 갈라진다.

| | ffmpeg 최종 mp4 (기본, `edit_videos.py`) | CapCut draft (`export_capcut.py`) |
|---|---|---|
| 언제 | 대량·무인·야간 배치, 클립 양산, N채널 증폭 | **사람이 마지막으로 만지는 메인 영상 1편** |
| 강점 | 결정적·재현 가능, EBU R128 오디오, ASS 픽셀 자막, 서버 단독 완결 | **비파괴 컷**(경계 드래그 재조정), CapCut 트렌디 자막 템플릿·효과 |
| 사람 개입 | 0회 | 1회 필수(최종 export는 CapCut 앱에서만) |

```bash
# CapCut draft 내보내기 (무음컷 + faster-whisper 자막 주입, 비파괴 컷)
python video-editor/export_capcut.py input/원본.mp4 \
  --draft-dir output/drafts --transcript output/transcript.json
# → draft 폴더를 통째로 PC의 CapCut 초안 폴더(com.lveditor.draft)로 복사 → CapCut 재시작
#   (draft 안 README_이식방법.txt 에 OS별 경로·재연결 절차 동봉. 내 PC에서 직접 실행하면
#    --draft-dir 에 CapCut 초안 폴더를 지정해 복사 없이 바로 뜬다.)
```

**규칙(중요):**
- 자막은 CapCut 자동자막에 맡기지 않는다(2025 유료화: 무료 10분/프로젝트 + 한국어 정확도 통제 불가).
  faster-whisper 결과를 주입하고, CapCut 에서는 **스타일 템플릿 입히기만** 한다.
- 기존 CapCut draft 를 읽어 템플릿으로 쓰지 않는다(신버전 draft 암호화로 깨지는 영역 — 새 draft 평문 생성만 신뢰).
- 무인 파이프라인(크론·배치)에 draft 경로를 끼우지 않는다 — GUI 필요해서 구조적으로 막힘. 깨지면 ffmpeg 경로로 폴백.
- draft 포맷은 비공식 리버스엔지니어링(pycapcut==0.0.3 고정) → 업그레이드 전 `python video-editor/smoke_capcut.py` 필수.

## 언제 더 센 도구로 갈아탈까 (escalation)

- **단어 단위 정밀/노래방 자막**이 필요 → WhisperX(forced alignment, wav2vec2).
- **복잡한 모션그래픽/데이터 기반 그래픽** → Remotion(React로 매 프레임 렌더). 단 Node+headless Chromium, 느림.
- **군말·중복·횡설수설 자동 컷**(무음이 아니라 내용) → ✅구현됨: `--llm-cut`(Claude API 키) 또는 `--cut-segments '4,12,16'`(대화형으로 내가 고른 번호). 문장 단위 전사 → LLM이 뺄 문장 선택 → 해당 구간만 컷·자막 타임코드 재정렬(비발화 구간 보존).
- **인터뷰/다화자** → WhisperX diarization(pyannote).
- **대량/긴 영상 빠른 인코딩** → GPU `h264_nvenc`.

## 안전·운영

- 중간 산출물(merged·SRT·ASS) 보존 → 실패 시 그 지점부터 재개(`--keep-work`).
- 원본·결과 미디어는 커밋하지 않음(.gitignore). 폰트/효과음/짤은 `assets/`(출처 `assets/README.md`).
