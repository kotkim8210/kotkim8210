# OSMU Video Builder (auto)

대본 → **본편 1편(16:9) + OSMU 클립 N개(9:16)** 자막 자동 번인.
역사·금융 '나락' 롱폼 채널용 반자동 파이프라인. **명령 1개로 전 과정**을 돌린다.

> ⚠️ 컷·자막·리프레임·고증검출 같은 **노가다는 자동**, 음성·이미지·대본 ★관점 30%는 **사람**.
> 같은 템플릿 양산 = 슬롭 = 수익화 차단. 자동화는 증폭기지 창작 대체기가 아니다.

---

## 이제 당신이 하는 일은 딱 3가지 — **`human_tasks.md` 한 장이면 끝**
실행하면 `human_tasks.md`(체크리스트)와 `voice_script.md`(음성 복붙용 대본)가 자동 생성됩니다.
1. **대본 ★관점 승인** (Claude가 초안 작성, 당신은 두세 군데만 본인 말투로)
2. **음성 만들기** — **`voice_script.md`** 열어서 세그먼트별 대본을 브루에 복붙 → 적힌 파일명대로 저장
3. **이미지 만들기** — `image_prompts.16x9.md` 프롬프트 → ChatGPT/ImageFX → 적힌 파일명대로 저장

`voice_script.md`는 (저장 파일명 + 읽을 내용)이 세그먼트별로 분리돼 있고, 맨 아래 '전체 한 번에
복사' 블록도 있습니다. 나머지(고증 검색·검증, TTS 교정, 프롬프트 생성, 길이 계산, 조립)는 전부 자동.

---

## 설치 (1회)
```bash
pip install moviepy imageio-ffmpeg pillow numpy
pip install faster-whisper        # 동기화 자막(whisper) 쓸 때만
```
ffmpeg는 imageio-ffmpeg에 포함. 한국어 폰트 NanumGothic.ttf 동봉.

## 명령 1개로 전부
```bash
# 준비 단계 + 현황판 (고증→TTS교정→이미지프롬프트→무엇이 남았는지)
python auto.py examples/tulip_full_config.json --era 17c

# 현황판만 보기
python auto.py examples/tulip_full_config.json --status

# 이미지·음성 준비됐으면 영상까지
python auto.py examples/tulip_full_config.json --era 17c --build
```
- **idempotent**: 이미 만든 단계는 건너뜀(`--force`로 재실행).
- **게이트**: 고증 미검증 or 자산 부족이면 `--build`가 막힌다(슬롭·오류 차단).

## lean config (대본 형식)
id/text/caption만 적으면 경로는 자동 유도(`assets/<id>.jpg`, `assets/<id>.mp3`).
`config.example.json` 참고. 20분이면 text 합계 6,400~7,000자.

```json
{ "voice": {"backend":"files"}, "captions": {"mode":"whisper"},
  "segments": [ {"id":"s1","text":"...","caption":"...","era":"modern?"} ],
  "clips": [ {"name":"01_hook","from_segments":["s1"],"hook":"..."} ] }
```

## 모듈 (auto.py가 순서대로 호출)
| 파일 | 역할 |
|---|---|
| `auto.py` | **마스터 오케스트레이터** + 현황판 + 게이트 |
| `factcheck.py` | 고증 검출 → `factcheck_todo.json`(Claude 작업목록) + factlog 연동 |
| `ttsfix.py` | 숫자·영문 한글화, 호흡 분할 → `config.tts.json`(읽기용) |
| `promptgen.py` | 이미지 프롬프트 16:9/9:16 + `image_manifest.json`(파일명 매핑) |
| `handoff.py` | **`voice_script.md`(음성 복붙용)** + **`human_tasks.md`(체크리스트)** 생성 |
| `images.py` | (선택) 이미지 자동 생성 — `images.backend` 설정 시 |
| `voice.py` | 음성 백엔드: files(브루)/elevenlabs/xtts |
| `captions.py` | Whisper 동기화 자막 |
| `build.py` | 영상 조립(본편+클립+자막) |
| `osmu_common.py` | lean config 로더 + 경로 규칙 |

## 고증 자동 해결 (SKILL.md)
`factcheck.py`가 **[수치확인]·[실명위험]** 을 `factcheck_todo.json`에 모으면,
**Claude가 채팅에서 web_search로 직접 검증·수정**하고 `factlog.json`에 기록한다.
한 번 검증한 숫자는 다음 화차부터 다시 보채지 않는다. 상세: `SKILL.md`.

## (선택) 완전 자동 이미지/음성
- 이미지: `"images": {"backend":"openai","model":"gpt-image-1"}` + `OPENAI_API_KEY` → 빠진 이미지 자동 생성.
- 음성: `"voice": {"backend":"elevenlabs","voice_id":"..."}` + `ELEVENLABS_API_KEY` → 대본만 넣으면 자동 발성.
- 기본은 둘 다 OFF(무비용·브루/ChatGPT 분업).

## n8n 자동화
버튼 하나로 `auto.py` 호출. 상세: `N8N_GUIDE.md`. 래퍼: `run_prep.sh`/`run_build.sh`.
n8n은 파이썬과 **같은 PC에서 self-host**(npx)해야 Execute Command 작동(Cloud 불가).
