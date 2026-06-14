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

1. **무음 컷** — 각 영상에서 일정 시간 이상 조용한 구간을 찾아 잘라냅니다. (ffmpeg `silencedetect`)
   말이 끊기지 않도록 말하는 구간 앞뒤에 약간의 여유(margin)를 남깁니다.
2. **규격 통일 & 이어 붙이기** — 해상도·프레임레이트가 제각각인 영상도 같은 캔버스(기본 1920×1080·30fps)로
   맞춘 뒤(비율 유지 + 레터박스), 파일 이름 순서대로 이어 붙입니다.
3. **한국어 전사** — 합쳐진 영상의 음성을 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)로
   한국어 자막(.srt)으로 변환합니다. (VAD로 환청·잡음 구간을 걸러냅니다)
4. **자막 입히기** — 한글 자막을 영상 위에 태워(burn-in) `output`에 저장합니다.

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
```

전체 옵션은 `python video-editor/edit_videos.py --help` 로 볼 수 있습니다.

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--model` | `medium` | 음성 인식 모델 `tiny`·`base`·`small`·`medium`·`large-v3` (클수록 정확·느림) |
| `--noise` | `-30dB` | 이보다 작은 소리는 무음으로 간주 |
| `--min-silence` | `0.6` | 이 길이(초) 이상 조용해야 컷 |
| `--margin` | `0.20` | 말 구간 앞뒤로 남길 여유(초) |
| `--width`/`--height`/`--fps` | `1920`/`1080`/`30` | 결과 영상 규격 |
| `--font` | `NanumGothic` | 자막 폰트(한글 지원) |
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
