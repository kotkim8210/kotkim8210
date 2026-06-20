# 원본 캡처 — min-inter.co.kr 영상편집 자동화 글 검토 (2026-06-14)

출처: https://min-inter.co.kr/wiki/video-editing-automation-whisper-ffmpeg-remotion/
요청: "정말 자동화 되는지 냉정하게 검토 + 내 스킬과 비교 + 더 나은 건 습득해 스킬화 + 제2의 뇌 저장"

## 글의 골자 (5단계)
1 입력분석(Whisper/faster-whisper/WhisperX/Vrew) → 2 편집결정(LLM: 군말·중복 골라내기)
→ 3 컷(ffmpeg select+setpts / auto-editor) → 4 꾸미기(ffmpeg subtitles / Remotion)
→ 5 출력(libx264 / nvenc / videotoolbox).
설계철학: ① 의미판단=AI, 시간계산=코드  ② 단계마다 중간산출 저장(재개 가능)  ③ 무엇을→언제 순서.
저자가 인정한 한계: 미적 판단·감성 B-roll 선택은 자동화 불가.

## 검증된 핵심 명령(다 실제로 맞음)
- whisper --model large-v3-turbo --language ko --word_timestamps True
- whisper ... --initial_prompt "도메인용어"   ← 정확도 힌트
- ffmpeg select=between(t,a,b),setpts=PTS-STARTPTS / asetpts  ← 컷 후 싱크
- ffmpeg silencedetect=noise=-30dB:d=0.5
- auto-editor input.mp4 --margin 0.2s
- ffmpeg crop=ih*9/16:ih,scale=1080:1920  (가로→세로 9:16)
- ffmpeg -c:v h264_nvenc / h264_videotoolbox  (HW 인코딩)
- npx skills add remotion-dev/skills  (Remotion Agent Skills)

## 내 도구(video-editor/edit_videos.py)와 비교 — 냉정하게
글이 맞고 내 구현이 이미 하는 것: faster-whisper, silencedetect, setpts 싱크, concat 규격주의, 자막 번인, 중간산출 보존.
글이 더 나은 것(습득 대상): initial_prompt(도메인힌트), large-v3-turbo, WhisperX(단어정밀), Remotion(모션그래픽),
  LLM 내용컷(군말 제거), HW 인코더, 화자분리.
내가 더 나은 것(글에 없음): **라우드니스 정규화(loudnorm)** ← 글에 아예 없음, 실전 최대 함정 해결;
  자동 규격통일(scale+pad 레터박스); ASS 리치 스타일(폰트·단어색·줌팝); 짤 오버레이·키워드 타이밍; SFX;
  반환각 억제 실전노하우(word_timestamps가 오히려 깸 → 문장 비례분할, 한글없는 큐 버리기).

## 즉시 습득(구현 완료)
- video-editor 에 `--initial-prompt` 추가 → 도메인 어휘 힌트로 한국어 정확도↑ (옥수수영상 깨짐 문제 직격).
- --model 도움말에 large-v3-turbo 권장 명시.

## 결론
"자동화"는 핸즈오프가 아니라 "스크립트 보조". 글은 기술적으로 정직·정확.
미개척 최대 레버 = **2단계(LLM 내용컷: 무음이 아닌 군말·중복 제거)** — 양쪽 다 아직 미완.
