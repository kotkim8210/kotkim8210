# assets — 영상 편집용 리소스

영상 자동 편집기(`video-editor/`)가 사용하는 폰트·효과음·이미지를 모아두는 곳입니다.

## 폰트 — GmarketSans
- `GmarketSansTTFBold.ttf` / `GmarketSansTTFMedium.ttf` / `GmarketSansTTFLight.ttf`
- 제공: eBay Korea (G마켓), **SIL Open Font License 1.1** (상업적 이용 가능, 재배포 허용)
- 출처: https://corp.gmarket.com/fonts/
- 자막 번인에 family **"Gmarket Sans TTF"**(Bold) 로 사용.

## 효과음 (직접 합성 — 저작권 free)
- `sound.wav` — 인트로 임팩트("두둥", 넷플릭스 인트로 느낌). 합본 맨 앞에 삽입.
- `sound1.wav` — 전환 휘릭("쇼츠 스타일 스와이프"). 입력 영상이 넘어가는 지점(영상 2개 이상일 때)에 삽입.
- ffmpeg 합성음이라 라이선스 걱정 없이 교체·수정 가능.

## 이미지(짤) — 쇼츠용 리액션 밈
- `image.jpg` — Gigachad(기가차드) 밈. "만렙/장비템 풀장착" 같은 플렉스 맥락에 삽입.
- `image1.jpg` — Surprised Pikachu(놀란 피카츄) 밈. "AI 공포/일자리" 같은 충격 맥락에 삽입.
- `--overlay '경로@자막키워드@지속초'` 로 자막 키워드가 나오는 타이밍에 오버레이.
- 다른 이미지로 교체하려면 같은 이름으로 바꿔 넣거나 `--overlay` 경로를 지정하세요.
- (밈 이미지는 인터넷 공개본이며, 개인적 편집 용도로 사용)
