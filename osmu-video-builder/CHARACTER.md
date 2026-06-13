# 채널 내레이터 캐릭터 — sref 기준 (전 에피소드 공용)

채널 명제 "사람은 왜 무너지는가"의 화자. 페르소나 = **냉정한 관찰자**.
이 캐릭터를 **딱 1장 먼저 만들어 sref(스타일/캐릭터 참조)로 고정**한 뒤, 내레이터가
등장하는 컷(`with_character: true` — 3화 기준 s1·s11·s12)에 재사용한다. → 72컷이 한 인물로 통일.

> ⚠️ 대부분의 컷(도쿄 야경·차트·군중 등)은 캐릭터가 없는 '장면'이다. 캐릭터는 도입·심리·결론 등
> 화자가 직접 말하는 컷에만 등장시켜야 자연스럽다(억지로 다 넣지 말 것).

---

## 캐릭터 설정(고정)
- 30대 후반, 차분하고 날카로운 눈빛, 단정한 검은색 가르마 머리, 옅은 수염.
- 짙은 차콜 트렌치코트 + 검정 터틀넥. 시대를 타지 않는 '관찰자' 룩(어느 시대 사건이든 해설).
- 표정의 기본값: 침착·통찰. 과장된 감정 없음. 신뢰감.
- 성별·연령은 취향대로 교체 가능(아래 core 문구만 바꾸면 전부 따라감).

**core(모든 프롬프트에 공통으로 들어갈 한 줄):**
```
a calm sharp-eyed male analyst in his late 30s, neat dark side-parted hair, light stubble, wearing a dark charcoal trench coat over a black turtleneck, composed intelligent expression, a timeless observer
```

---

## 1) 캐릭터 레퍼런스 시트 (이걸로 sref 고정 — 가장 중요)
Flow(Nano Banana Pro)에 붙여넣고 4장 중 1장 선택 → `assets/_character.jpg`로 저장 + sref 등록.
```
character reference sheet of a calm sharp-eyed male analyst in his late 30s, neat dark side-parted hair, light stubble, wearing a dark charcoal trench coat over a black turtleneck, composed intelligent expression, a timeless observer, front view and three-quarter view and side view, full body and bust close-up, consistent character design, model sheet turnaround, neutral light grey background, even soft lighting, 2d Korean naver webtoon comic style, flat vivid colors, bold clean outlines, minimal cel shading
```
**negative:** `photorealistic, 3d render, photograph, multiple different people, inconsistent face, text, watermark, logo, extra fingers, deformed hands, lowres`

## 2) 표정 시트 (컷별 감정 맞출 때 참고)
```
expression sheet of the same character (a calm sharp-eyed analyst in a dark charcoal trench coat, neat dark hair), six expressions in a grid: calm, thoughtful, quietly concerned, a knowing faint smirk, serious warning, subtle empathy, identical consistent face, neutral grey background, 2d Korean naver webtoon comic style, flat colors, bold clean outlines, minimal cel shading
```

## 3) 채널 키 비주얼 (썸네일·인트로용)
```
key visual of a calm sharp-eyed male analyst in a dark charcoal trench coat, arms crossed, looking directly at the viewer, dark moody background with faint falling stock charts and ghostly numbers, dramatic rim light, cinematic webtoon composition, 2d Korean naver webtoon comic style, bold clean outlines, flat dramatic colors
```

---

## 사용 순서
1. **1) 레퍼런스 시트** 프롬프트 → Flow에서 생성 → 마음에 드는 1장을 `assets/_character.jpg`로 저장.
2. Flow/Nano Banana Pro에서 그 이미지를 **sref(스타일 참조)로 등록**(또는 매 프롬프트에 첨부).
3. 내레이터 등장 컷(`with_character:true`) 생성 시: **sref + 그 컷의 장면 프롬프트**(image_prompts.md) 함께 입력 → 동일 인물 유지.
4. 표정이 어색하면 **2) 표정 시트**에서 맞는 표정을 참고해 프롬프트에 한 단어 추가(예: "concerned expression").

## config 연동
- `image_style.character` 값이 내레이터 묘사이고, `segment.with_character: true` 인 컷에 자동 주입됨.
  → 위 core 문구를 바꾸면 `image_style.character`도 같이 바꿔 두 곳을 일치시킬 것.
