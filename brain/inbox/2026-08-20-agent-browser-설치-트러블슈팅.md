# agent-browser 스킬 설치 + 원격 환경 브라우저 트러블슈팅

날짜: 2026-08-20
맥락: Claude Code 원격(클라우드 컨테이너) 세션에서 진행. 브랜치 `claude/agent-browser-skill-jzrhga`, PR #28.

## 1. 한 일

```
npx --yes skills@latest add vercel-labs/agent-browser --agent claude-code --yes --copy
npm install -g agent-browser
agent-browser install
```

- 저장소에 생긴 파일: `.claude/skills/agent-browser/SKILL.md`, `skills-lock.json`
- SKILL.md는 "디스커버리 스텁"일 뿐. 실제 사용법은 CLI가 버전에 맞춰 제공 → `agent-browser skills get core`
- 특화 스킬: electron, slack, dogfood, derive-client, vercel-sandbox, agentcore
- CLI 버전 0.27.0, 크롬 152.0.7977.42 를 `/root/.agent-browser/browsers/` 에 설치

## 2. 증상

로컬 페이지(`http://127.0.0.1:8899`)는 잘 열림. 그런데 외부 HTTPS는 전부 실패:

```
✗ Navigation failed: net::ERR_CONNECTION_RESET
```

반면 `curl https://example.com` 은 200 정상. 즉 네트워크 자체는 살아있고 크롬만 실패.

## 3. 틀린 진단 (기록용)

처음에 netlog에서 `net_error: -202` (ERR_CERT_AUTHORITY_INVALID, is_issued_by_known_root: false)를 보고
"프록시 MITM 인증서를 크롬이 못 믿는다"고 판단했다. → **틀렸다.**

그 -202는 크롬 자체 텔레메트리(clients2.google.com 등) 요청에서 난 것이고 우리가 열려던 사이트와 무관했다.
실제로 `openssl s_client -proxy` 로 확인하니 프록시는 example.com을 MITM하지 않고
진짜 Cloudflare 인증서를 그대로 통과시켰다 (Verify return code: 0).

교훈: netlog에서 에러 코드만 grep하지 말고 **source id로 요청을 묶어서** 어느 호스트의 이벤트인지 확인해야 한다.

## 4. 진짜 원인

netlog를 source id 기준으로 다시 추적한 결과:

1. 크롬 → 프록시 TCP 연결 성공
2. `CONNECT example.com:443` 전송 → 프록시가 `HTTP/1.1 200 Connection Established` 응답 (터널 성립)
3. 크롬이 ClientHello 전송 (1945~2049 바이트)
4. `SOCKET_READ_ERROR [ERR_CONNECTION_RESET] os_error: 104` → 여기서 끊김

ClientHello를 파싱해보니:

```
key_share groups: [('0xcaca', 1), ('0x11ec', 1216), ('0x1d', 32)]
ECH extension present, len 218
```

- `0x11ec` = **X25519MLKEM768** (양자내성 키교환). 키셰어 하나가 **1216바이트**.
- 이것 때문에 ClientHello가 ~2000바이트가 되어 TCP 세그먼트를 넘김.
- 중간 프록시/미들박스가 이 큰 ClientHello를 처리 못 하고 RST.
- curl(OpenSSL 3.0)은 ML-KEM이 없어 ClientHello가 작아서 통과했던 것.

## 5. 안 먹힌 시도들

이 이름들은 크롬 152에서 전부 무효 (ClientHello 크기 그대로, 0x11ec 여전히 존재):

- `--disable-features=PostQuantumKyber`
- `--disable-features=X25519MLKEM768`
- `--disable-features=UseMLKEM`
- `--disable-features=PostQuantumKeyAgreement`
- `--disable-features=TLS13KyberDraft`
- `--disable-features=EncryptedClientHello`
- `--disable-features=TLSTrustAnchorIDs`

크롬 바이너리를 `strings`로 뒤져보니 TLS용 PQ 기능 플래그 자체가 없고
`WebRtcPostQuantumKeyAgreement`(WebRTC 전용)만 존재.
엔터프라이즈 정책 `PostQuantumKeyAgreementEnabled` 문자열도 바이너리에 없음 → 크롬 152에서 제거된 듯.

## 6. 해결책

ML-KEM 키셰어는 **TLS 1.3 전용**이므로, TLS 1.2로 상한을 두면 통째로 빠진다:

```
--ssl-version-max=tls1.2
```

**인증서 검증은 그대로 유지된다.** 보안 검증을 끄는 것(`--ignore-certificate-errors`)이 아니라,
프록시가 못 다루는 신기능만 안 쓰는 것. 원격 환경 README도 TLS 검증 비활성화를 명시적으로 금지한다.

## 7. 실제 사용법

```bash
agent-browser batch --proxy "$HTTPS_PROXY" --args "--ssl-version-max=tls1.2" \
  "open https://example.com" "get title" "get text h1" "screenshot shot.png"
```

두 가지 함정:

- **프록시 포트는 세션마다 바뀐다.** 작업 도중에도 43453 → 42755로 변경됐다.
  반드시 `"$HTTPS_PROXY"` 환경변수로 넘길 것. 숫자를 하드코딩하면 다음 세션에 깨진다.
- **`batch`를 써라.** `open`과 `get`을 따로 실행하면 매번 새 브라우저가 떠서 앞 페이지를 잃는다.

또 하나: `--args`는 **쉼표를 항상 구분자로 처리**한다.
그래서 `--disable-features=A,B,C` 같은 쉼표 포함 값은 넘길 수 없다
(잘려서 크롬이 "Multiple targets are not supported in headless mode" 로 죽는다).

## 8. 검증 결과

- example.com: 제목·h1·본문 추출 성공
- github.com/kotkim8210/kotkim8210: 제목 추출 + 스크린샷(76KB) 성공

## 9. 쿠팡은 안 된다 [확인필요]

`www.coupang.com`, `wing.coupang.com` 둘 다 차단:

```
Access Denied
You don't have permission to access "http://www.coupang.com/" on this server.
Reference #18.44a4c017...  →  errors.edgesuite.net
```

`errors.edgesuite.net` = **Akamai** 방화벽. 우리 프록시 문제가 아니라 쿠팡 측 차단.
원인 추정: 이 세션이 클라우드 데이터센터 IP에서 돌아가고, 커머스 사이트는 크롤링 방지로
데이터센터 IP 대역을 통째로 막는다. 로그인 자격증명 유무와 무관하게 현관에서 차단.

→ 따라서 `coupang-inventory` 스킬의 기존 방식(사람이 쿠팡윙에서 엑셀 2개를 직접 받아 업로드)은
   그대로 유지해야 한다. 브라우저 자동화로 대체 불가.
   우회 시도는 쿠팡 이용약관 위반이므로 하지 않는다.

## 10. 부수 효과 / 남은 것

- 인증서 방향으로 조사하던 중 `libnss3-tools` 설치, 빈 `/root/.pki/nssdb` 생성 → 결국 불필요했음. 무해.
- 인증서 신뢰 저장소 조작과 `/etc` 정책 파일 쓰기는 권한 분류기가 차단했다. 결과적으로 필요 없었으니 잘 막힌 셈.
- CLI와 크롬은 저장소 밖(임시 컨테이너)에 설치되므로 세션 종료 시 사라진다. PR에는 스킬 파일 2개만 포함.
