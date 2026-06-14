# n8n으로 OSMU 시스템 자동화 — 왕초보 가이드
> n8n을 처음 써도 따라올 수 있게, 한 줄씩 짚어 드립니다.

---

## 0. 먼저: n8n이 뭐고, 여기서 뭘 해주나 (정직하게)

- **n8n** = 레고 블록(노드)을 선으로 연결해 작업을 자동화하는 도구입니다. "이거 실행되면 → 저거 해라"를 그림으로 짭니다.
- **여기서 n8n의 진짜 역할:** 영상을 직접 만드는 게 아닙니다(그건 무거운 ffmpeg·Whisper 작업이라 파이썬이 합니다). n8n은 **버튼 하나로 파이프라인을 실행**하고, 나중에 **예약·알림·구글시트 연동·업로드**까지 엮는 '지휘자'입니다.
- **솔직히:** 단순히 "파이프라인 실행"만 원하면 그냥 스크립트를 직접 돌리는 게 더 간단합니다. n8n은 이런 걸 붙일 때 진가가 납니다 → ① 매주 자동 실행 ② 구글시트에 쌓아둔 다음 주제 자동으로 읽기 ③ 완료되면 텔레그램/이메일 알림. 그래서 지금은 **'맛보기 + 확장 기반'**으로 깝니다.
- ⚠️ **핵심 철학 유지:** n8n으로도 **완전 무인은 하지 않습니다.** 자산 준비와 검수는 사람 게이트로 남겨, 슬롭·정책 사고를 막습니다.

---

## 1. 큰 그림 (이렇게 흘러갑니다)

```
[n8n 워크플로우 1: 준비]  버튼 클릭
   → run_prep.sh 실행 (고증검토 → TTS교정 → 이미지 프롬프트 생성)
   → image_prompts.md, config.tts.json 이 생김

[사람이 직접]  ← 여기는 자동화 안 함(슬롭 방지)
   ① 프롬프트로 이미지 생성(ChatGPT/ImageFX) → assets/ 에 저장
   ② 브루로 tts_text 음성화 → assets/ 에 저장

[n8n 워크플로우 2: 조립]  버튼 클릭
   → run_build.sh 실행 (자산 점검 → 본편 + 클립 + 자막)
   → out_tulip/ 에 영상 완성
```

---

## 2. 전제 (중요)
- **n8n을 '파이썬 스크립트가 깔린 그 PC'에서 돌려야 합니다.** n8n이 그 컴퓨터의 명령을 직접 실행(Execute Command)해야 하기 때문입니다.
- 그래서 클라우드 버전(n8n Cloud)이 아니라 **내 PC에서 직접 실행(self-hosting)** 합니다. (Cloud는 보안상 Execute Command가 막혀 있습니다.)
- 이미 1단계로 도구가 작동하는 PC라면, 파이썬·ffmpeg는 이미 준비된 상태입니다.

---

## 3. n8n 설치 — 가장 쉬운 방법 (npx)

1. **Node.js LTS 설치** — https://nodejs.org 에서 LTS 버전 설치(n8n이 Node 기반).
2. 터미널(명령 프롬프트)에 입력:
   ```bash
   npx n8n
   ```
   → 처음엔 자동 설치 후 실행됩니다(몇 분 걸림).
3. 브라우저에서 열기: **http://localhost:5678**
4. 첫 화면에서 로컬 계정(이메일/비번)을 만듭니다. (내 PC에만 저장됨)

> Docker로도 가능하지만, 그러면 컨테이너 안에서 파이썬·ffmpeg가 안 보여 복잡해집니다. **초보는 npx 방식을 권장합니다.**

---

## 4. 워크플로우 만들기 (둘 중 택1)

### 방법 A — 직접 만들기 (노드 2개, 5분 · 추천: 배우기 좋음)
1. 왼쪽 위 **+ (New Workflow)**.
2. 캔버스에서 **+** → 검색창에 `Manual Trigger` → **"On clicking 'Execute workflow'"** 추가. (직접 실행 버튼)
3. 그 노드 오른쪽 **+** → `Execute Command` 검색해 추가. (두 노드가 선으로 연결됨)
4. **Execute Command** 노드를 클릭 → **Command** 칸에 입력:
   ```
   bash /당신의/실제경로/osmu_video/run_prep.sh
   ```
   - 경로는 `osmu_video` 폴더의 **실제 위치**로 바꾸세요. (모르면 터미널에서 그 폴더로 간 뒤 `pwd`)
5. 오른쪽 위 **Save** → **Execute workflow**(실행) 클릭.
6. 노드가 초록색이 되고, 클릭하면 **출력(OUTPUT)**에 실행 로그가 보입니다.
7. **워크플로우를 하나 더** 같은 방식으로 만들되, Command만 `run_build.sh`로. (이게 조립용)

### 방법 B — 파일 가져오기 (Import)
1. 새 워크플로우 화면에서 오른쪽 위 **⋯ (점 세 개)** → **Import from File**.
2. 동봉된 `n8n_workflow_1_prep.json` 선택.
3. Execute Command 노드를 열어 **`/CHANGE_ME/`를 실제 경로로 수정** → Save.
4. `n8n_workflow_2_build.json` 도 똑같이.
> 임포트가 버전 차이로 안 되면, **방법 A로 직접 만드세요**(더 확실하고 금방 됩니다).

---

## 5. 실제로 돌리는 순서 (사람 게이트 포함)

1. **워크플로우 1(준비) 실행** → 끝나면 `osmu_video/` 안에 `image_prompts.md`, `config.tts.json` 생성.
2. **사람이 직접:**
   - `image_prompts.md`의 프롬프트를 ChatGPT/ImageFX/미드저니에 붙여 이미지 생성 → `assets/` 에 `b1.jpg`…`b12.jpg`로 저장.
   - 브루에서 `config.tts.json`의 `tts_text`를 음성화 → `assets/` 에 `s1.mp3`…`s12.mp3`로 저장.
3. **워크플로우 2(조립) 실행** → `out_tulip/`에 본편 + 클립 3개 완성.
   - 자산이 빠졌으면 **자동으로 중단**되고 무엇이 없는지 알려줍니다(안전장치).

---

## 6. (선택) 한 단계 업그레이드 — 나중에

| 하고 싶은 것 | 방법 |
|---|---|
| **매주 자동 실행** | Manual Trigger를 **Schedule Trigger**로 교체 |
| **완료 알림** | 맨 끝에 **Telegram / Send Email** 노드 추가 → "영상 완성" 메시지 |
| **다음 주제 자동 공급** | **Google Sheets** 노드로 주제 행을 읽어 config 생성(고급) |
| **HTTP로 호출** | `api.py` 띄우고(아래) **HTTP Request** 노드로 호출 |

> 지금은 ④까지 안 해도 됩니다. **버튼 실행만으로 충분**하고, 익숙해지면 하나씩 붙이세요.

---

## 7. 자주 막히는 곳 (트러블슈팅)

- **Execute Command 노드가 안 보이거나 막힘** → n8n **Cloud는 보안상 비활성**. 반드시 **내 PC에서 npx로 실행**한 n8n에서 사용.
- **`python3: command not found`** → 파이썬 경로 문제. 터미널에서 `which python3` 확인 후, 스크립트가 그 파이썬을 쓰는지 점검. (윈도우는 `python` 일 수 있음 → 스크립트의 `python3`를 `python`으로)
- **`Permission denied`** → `chmod +x run_prep.sh run_build.sh` 한 번 실행.
- **경로에 한글/공백** → 명령에서 경로를 큰따옴표로: `bash "/내 폴더/osmu_video/run_prep.sh"`.
- **Whisper 첫 실행이 느림** → 모델을 1회 자동 다운로드(인터넷 필요). 이후엔 빠릅니다.
- **윈도우라서 bash가 없음** → Git Bash 설치 후 사용하거나, Command를 `wsl bash ...`(WSL) 또는 `python3 auto.py ...`로 직접 호출.

---

## 8. (선택) HTTP 방식 — api.py
Execute Command 대신 HTTP로 부르고 싶을 때만.
```bash
pip install fastapi uvicorn
uvicorn api:app --host 127.0.0.1 --port 8000
```
- n8n **HTTP Request** 노드 → Method: POST → URL: `http://127.0.0.1:8000/prep` (또는 `/build`).
- 장점: 깔끔·분리. 단점: API 서버를 따로 띄워 둬야 함. → **초보는 Execute Command가 더 간단**합니다.

---

## 9. 한 장 요약
1. `npx n8n` → http://localhost:5678
2. 워크플로우 1: Manual Trigger → Execute Command(`bash .../run_prep.sh`)
3. 실행 → 이미지·음성 만들어 `assets/`에 넣기
4. 워크플로우 2: Execute Command(`bash .../run_build.sh`) → 영상 완성
5. 익숙해지면 Schedule(예약)·Telegram(알림) 추가
