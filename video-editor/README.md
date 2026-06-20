# 🎬 영상 자동 편집기 (Video Auto-Editor)

여러 영상을 넣으면 **말 없는 조용한 부분을 자동으로 잘라내고**, **이름 순서대로 이어 붙인 뒤**,
**말하는 내용을 한국어 자막으로 자동으로 입혀** 하나의 영상으로 만들어 줍니다.

```
input/   ← 편집할 영상들을 여기에 넣는다 (파일 이름 순서대로 합쳐짐)
output/  ← 완성된 영상(.mp4)과 자막(.srt)이 여기에 생성됨
```

---

## 빠른 시작

```bash
# 1) 준비물 설치 (최초 한 번)
bash video-editor/setup.sh

# 2) input 폴더에 영상 넣기
#    예) input/01_오프닝.mp4, input/02_본론.mov, input/03_마무리.mp4
#    → 파일 이름의 사전순(01, 02, 03 …)으로 합쳐집니다.

# 3) 실행
python video-editor/edit_videos.py

# 4) output 폴더에서 결과 확인
#    output/edited_YYYYMMDD_HHMMSS.mp4  (자막이 입혀진 영상)
#    output/edited_YYYYMMDD_HHMMSS.srt  (생성된 자막 파일)
```

> 처음 실행하면 음성 인식 모델을 한 번 내려받습니다(인터넷 필요). 이후에는 캐시되어 빠릅니다.

---

## 동작 원리 (파이프라인)

1. **음성 정규화** — 마이크 볼륨이 작게 녹음된 영상도 들리도록 음량을 표준 수준으로 끌어올립니다(EBU R128).
   이 덕분에 작게 녹음된 영상이 "전부 조용함"으로 잘못 판정돼 통째로 잘려나가거나 자막이 비는 일을 막습니다.
   (끄려면 `--no-normalize-audio`)
2. **무음 컷** — 각 영상에서 일정 시간 이상 조용한 구간을 찾아 잘라냅니다. (ffmpeg `silencedetect`)
   말이 끊기지 않도록 말하는 구간 앞뒤에 약간의 여유(margin)를 남깁니다.
3. **규격 통일 & 이어 붙이기** — 해상도·프레임레이트가 제각각인 영상도 같은 캔버스(기본 1920×1080·30fps)로
   맞춘 뒤(비율 유지 + 레터박스), 파일 이름 순서대로 이어 붙입니다.
4. **한국어 전사** — 합쳐진 영상의 음성을 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)로
   한국어 자막(.srt)으로 변환합니다. (VAD로 환청·잡음 구간을 걸러냅니다)
5. **자막 입히기** — 한글 자막을 영상 위에 태워(burn-in) `output`에 저장합니다.
   - 글자수 ~12자로 짧게 끊고, **GmarketSans 굵은 글씨 + 검은 외곽선**, 화면 하단에 배치.
   - `--highlight` 로 지정한 **중요 단어는 밝은 주황색(#FF8C42)** 으로 강조.
6. **효과음 & 짤(이미지)** — `assets/` 폴더의 리소스를 활용합니다.
   - **인트로 효과음**(`assets/sound.wav`, "두둥")을 맨 앞에 붙입니다.
   - **전환 효과음**(`assets/sound1.wav`, "휘릭")을 영상이 넘어가는 지점(2개 이상일 때)에 넣습니다.
   - `--overlay '경로@자막키워드@지속초'` 로 **짤 이미지**를 자막 키워드가 나오는 타이밍에 오버레이합니다.

> 폰트·효과음은 `bash video-editor/setup.sh` 또는 `assets/` 폴더에 들어 있습니다. (출처는 `assets/README.md`)

---

## 자주 쓰는 옵션

```bash
# 자막 정확도를 더 높이고 싶을 때 (느리지만 한국어 인식이 가장 좋음)
python video-editor/edit_videos.py --model large-v3

# 더 빠르게(정확도는 낮게) 돌리고 싶을 때
python video-editor/edit_videos.py --model small

# 무음 판정을 더 민감/둔감하게 (기본 -30dB, 0.6초)
python video-editor/edit_videos.py --noise -35dB --min-silence 1.0

# 자막을 태우지 않고 켜고 끌 수 있는 '소프트 자막'으로만 넣기
python video-editor/edit_videos.py --soft-subs

# 무음 컷 없이 그냥 합치기만
python video-editor/edit_videos.py --no-trim

# 세로 영상(쇼츠) 캔버스로
python video-editor/edit_videos.py --width 1080 --height 1920

# 결과 파일 이름 지정 / 입력·출력 폴더 변경
python video-editor/edit_videos.py --name 내영상 --input ./clips --output ./done

# 중요 단어 주황색 강조 + 짤(이미지) 자동 삽입
python video-editor/edit_videos.py \
  --highlight "피그마,AI,색상,상세페이지" \
  --overlay "assets/image.jpg@만렙@2.6" \
  --overlay "assets/image1.jpg@일자리@2.6"

# 효과음 끄기
python video-editor/edit_videos.py --no-intro-sound --no-transition-sound

# 자막 정확도 ↑: 도메인 어휘 힌트(상품명·전문용어)를 주면 깨짐·환청이 줄어듦
python video-editor/edit_videos.py --initial-prompt "피그마,상세페이지,초당옥수수,제주다팜"

# 2단계 내용 컷: 무음이 아니라 '군말·중복' 문장까지 LLM이 골라 제거
#   (A) 자동 — Claude API 키가 있을 때
export ANTHROPIC_API_KEY=sk-...
python video-editor/edit_videos.py --llm-cut
#   (B) 수동 — 잘라낼 문장 번호를 직접 지정(대화형으로 고른 번호 주입)
python video-editor/edit_videos.py --cut-segments "4,12,16,23,39"
```

> **2단계 내용 컷이란?** 무음 컷은 *말을 멈춘 곳*만 자릅니다. 내용 컷은 *말은 하지만
> 빼도 되는* 군말·말 더듬기·같은 말 반복·횡설수설을 문장 단위로 골라 잘라냅니다.
> "의미 판단은 AI, 시간 계산은 코드" — 어떤 문장을 뺄지는 LLM이, 초 단위 컷·타임코드
> 재정렬은 코드가 합니다. 비발화 구간(화면 데모 등)은 보존됩니다.

전체 옵션은 `python video-editor/edit_videos.py --help` 로 볼 수 있습니다.

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--model` | `medium` | 음성 인식 모델 `tiny`·`base`·`small`·`medium`·`large-v3`·`large-v3-turbo` (GPU 있으면 turbo 권장) |
| `--initial-prompt` | (없음) | 도메인 어휘 힌트(상품명·전문용어). 한국어 인식 정확도↑ |
| `--noise` | `-30dB` | 이보다 작은 소리는 무음으로 간주 |
| `--min-silence` | `0.6` | 이 길이(초) 이상 조용해야 컷 |
| `--margin` | `0.20` | 말 구간 앞뒤로 남길 여유(초) |
| `--no-normalize-audio` | 꺼짐 | 음성 정규화 끄기(작게 녹음된 영상은 거의 잘려나갈 수 있어 권장 안 함) |
| `--width`/`--height`/`--fps` | `1920`/`1080`/`30` | 결과 영상 규격 |
| `--font` | `Gmarket Sans TTF` | 자막 폰트(assets 폴더 폰트 사용) |
| `--max-chars` | `12` | 자막 한 줄당 글자수(이 정도로 끊음) |
| `--margin-v` | `20` | 자막을 화면 아래에서 띄울 거리(px) |
| `--highlight` | (없음) | 주황색으로 강조할 단어들(쉼표 구분) |
| `--orange` | `#FF8C42` | 강조 색 |
| `--overlay` | (없음) | 짤 삽입 `경로@자막키워드@지속초` (반복 가능) |
| `--llm-cut` | 꺼짐 | Claude(ANTHROPIC_API_KEY)로 군말·중복 문장 자동 제거(2단계 내용 컷) |
| `--cut-segments` | (없음) | 직접 제거할 문장 번호 `4,12,16-18` (수동 내용 컷) |
| `--no-intro-sound` / `--no-transition-sound` | 꺼짐 | 인트로/전환 효과음 끄기 |
| `--soft-subs` | 꺼짐 | 자막을 태우지 않고 트랙으로만 삽입 |
| `--no-subs` / `--no-trim` | 꺼짐 | 자막 / 무음 컷 단계 건너뛰기 |

---

## 지원 형식

`.mp4 .mov .mkv .avi .webm .m4v .flv .wmv .mpg .mpeg .ts`

---

## 문제 해결

- **`ffmpeg 가 필요합니다`** → `bash video-editor/setup.sh` 를 먼저 실행하세요.
- **자막 글자가 □□□(두부)로 보임** → 한글 폰트가 없는 경우입니다.
  Linux는 `fonts-nanum`을 설치하고, macOS는 `--font "AppleSDGothicNeo-Regular"` 처럼 시스템 폰트를 지정하세요.
- **자막이 부정확함** → `--model large-v3` 로 올려보세요. CPU에서는 느리지만 한국어 정확도가 크게 좋아집니다.
- **너무 많이/적게 잘림** → `--noise`(예 `-35dB`)와 `--min-silence`(예 `1.0`) 값을 조절하세요.
- **작게 녹음된 영상인데 거의 다 잘리거나 자막이 안 생김** → 기본적으로 음성 정규화가 켜져 있어 자동으로
  해결됩니다. 그래도 이상하면 `--noise -45dB` 처럼 무음 기준을 더 낮춰보세요.
