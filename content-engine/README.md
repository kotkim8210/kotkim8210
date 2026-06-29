# 🚀 content-engine — 크리에이터 증폭기 (1 오리지널 → N 채널)

> **"AI가 콘텐츠를 만든다"가 아니라 "내가 만든 오리지널을 AI가 10배 멀리 퍼뜨린다."**

상용 'VideoGen 스타터 키트(₩149,000)'류의 *주제→AI 양산* 모델은 2026년 유튜브의
**대량생산·재사용 콘텐츠 수익화 배제 정책**에 정면으로 걸린다(채널 정지 리스크). 그래서
이 모듈은 방향을 바꿨다 — **내 오리지널 1개(롱폼/대본)를 전 채널 네이티브 포맷으로
재가공·배포**하는 데 집중한다. 정책 안전(내 독창성이 들어감) + 고ROI(1→N) + 무과금(로컬).

설계 원칙: **의미 판단은 AI, 시간 계산은 코드.**
(무엇을 말할지·어디가 임팩트인지·어떤 훅이 강한지 = AI / 정확한 시각·길이·동기화·비율 = 코드)

## 입력 → 산출 (목표)
```
오리지널 영상(URL/파일) 또는 대본 1개
   → 전사(faster-whisper) / 또는 TTS 내레이션(타이밍 무료 획득)
   → (Claude가 하이라이트·채널별 카피 판단)
   → 9:16 쇼츠 N개(자막 번인) + 블로그(SEO) + 인스타(릴+캐러셀+캡션)
     + 스레드 + X + 링크드인 + 썸네일
   → output/<slug>/ 패키지 + 발행 체크리스트(검수 게이트)
```

## 현재 구현 상태
| 파일 | 상태 | 역할 |
|---|---|---|
| `tts.py` | ✅ 검증 | 로컬 한국어 내레이션(edge-tts) + 문장 타이밍 추출(자막용). 프록시 CA 처리. ⚠️ 상업용은 MeloTTS 전환(주석 참고) |
| `clip.py` | ✅ 검증 | 오리지널 구간 → 9:16/1:1 쇼츠 컷 + ASS 자막 번인(blur/cover/contain) |
| `carousel.py` | ⏳ 예정 | 인스타 캐러셀(4:5 1080×1350, 8~10슬라이드) |
| `thumbnail.py` | ⏳ 예정 | 1280×720 썸네일 + 대비/가독성 게이트 |
| `engine.py` | ⏳ 예정 | 오케스트레이터(입력→전 채널 패키지) + `/content-engine` 스킬 |

기존 자산 재사용: `video-editor/`(무음컷·9:16·자막·짤·효과음), `youtube-curator/`
(yt-dlp 다운로드·트렌드 발굴·업로드 게이트).

## 빠른 사용(현재)
```bash
pip install -r content-engine/requirements.txt
# 내레이션 + 자막(SRT)
python content-engine/tts.py "대본 텍스트" --voice female --out narration.mp3 --srt narration.srt
# 오리지널 구간 → 쇼츠(자막 자동: transcript.json 필요)
python content-engine/clip.py 원본.mp4 --start 60 --end 90 --out short.mp4 \
  --transcript transcript.json --hook "첫 줄 훅" --credit "@내채널 · 원본 링크"
```

## 정책·라이선스 주의
- **내 오리지널만 재가공**(CC·타인 영상 재업로드는 '재사용 콘텐츠' 정책 위험).
- TTS: edge-tts=개인/프로토타입, **상업·판매 산출물은 MeloTTS(MIT)**.
- 발행은 **draft 생성 + 사람 검수** 기본(자동 대량발행 금지).
