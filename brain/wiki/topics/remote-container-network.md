---
title: 원격 컨테이너 네트워크 — 프록시·TLS·IP 차단의 3중 제약
slug: remote-container-network
tags: [환경, 네트워크, 프록시, TLS, 원격세션, 트러블슈팅]
created: 2026-08-20
updated: 2026-08-20
sources: [2026-08-20-agent-browser-설치-트러블슈팅.md]
related: [[agent-browser]], [[session-independence]], [[claude-code-skills]], [[my-projects]]
confidence: high
status: active
---

## 한 줄 요약
클라우드 원격 세션의 외부 통신은 ① 포트가 매번 바뀌는 강제 프록시 ② 큰 ClientHello를 끊어버리는 TLS 제약 ③ 데이터센터 IP 차단, 이 3중 제약을 받으며 — 앞의 둘은 우회 가능하지만 셋째는 불가능하다.

## 핵심 내용

### ① 프록시: 포트가 세션마다 바뀐다
- 모든 외부 HTTPS는 `$HTTPS_PROXY`(로컬 강제 프록시)를 거친다. CA 번들은 `/root/.ccr/ca-bundle.crt`.
- `curl`·`node`·`python` 등은 환경변수(`CURL_CA_BUNDLE`·`NODE_EXTRA_CA_CERTS` 등)로 이미 설정돼 있다.
- **크롬은 이 환경변수들을 무시한다.** 별도로 `--proxy`를 넘겨야 한다.
- **포트는 고정이 아니다.** 한 작업 세션 도중에도 43453 → 42755로 바뀌었다. (2026-08-20-agent-browser-설치-트러블슈팅.md)
  → 숫자 하드코딩 금지. 반드시 `"$HTTPS_PROXY"` 환경변수로 넘길 것.
- 프록시는 CONNECT만 받는다. 평문 HTTP GET은 `ERR_BLOCKED_BY_CLIENT`로 거부(`non-CONNECT request` 로그).
- 상태 확인: `curl -sS "$HTTPS_PROXY/__agentproxy/status"` — 최근 실패 이력까지 보여준다.

### ② TLS: 양자내성 키교환이 연결을 끊는다 ⭐
**증상**: 크롬만 외부 HTTPS 전부 `net::ERR_CONNECTION_RESET`. 같은 주소를 `curl`은 200으로 잘 받음. 로컬 페이지는 정상.

**추적 결과**(netlog):
1. 크롬 → 프록시 TCP 연결 성공
2. `CONNECT example.com:443` → `HTTP/1.1 200 Connection Established` (터널 성립)
3. ClientHello 전송 (1945~2049 바이트)
4. `SOCKET_READ_ERROR [ERR_CONNECTION_RESET] os_error: 104` ← 여기서 끊김

**원인**: ClientHello의 key_share에 `0x11ec` = **X25519MLKEM768**(양자내성 키교환)이 들어가는데
이 키셰어 하나가 **1216바이트**. ClientHello가 ~2000바이트가 되어 TCP 세그먼트를 넘기고, 중간 장비가 처리 못 해 RST.
`curl`(OpenSSL 3.0)은 ML-KEM이 없어 ClientHello가 작아서 통과했던 것.

**해결**: ML-KEM은 TLS 1.3 전용이므로 상한을 1.2로 두면 통째로 빠진다.
```
--ssl-version-max=tls1.2
```
**인증서 검증은 그대로 유지된다.** `--ignore-certificate-errors`(검증 비활성화)와 혼동 금지 — 원격 환경 README가 명시적으로 금지하는 항목이다.

**안 먹힌 것들**(크롬 152 기준, ClientHello 크기 불변 · `0x11ec` 여전히 존재):
`--disable-features=` 뒤에 `PostQuantumKyber` / `X25519MLKEM768` / `UseMLKEM` / `PostQuantumKeyAgreement` / `TLS13KyberDraft` / `EncryptedClientHello` / `TLSTrustAnchorIDs` — 전부 무효.
바이너리를 `strings`로 확인하니 TLS용 PQ 기능 플래그 자체가 없고 `WebRtcPostQuantumKeyAgreement`(WebRTC 전용)만 존재.
엔터프라이즈 정책 `PostQuantumKeyAgreementEnabled` 문자열도 없음 → 크롬 152에서 제거된 것으로 보인다.

### ③ IP 차단: 커머스 사이트는 아예 못 들어간다 ⚠️
`www.coupang.com`·`wing.coupang.com` 둘 다 차단:
```
Access Denied — You don't have permission to access ... on this server.
Reference #18.44a4c017...  →  errors.edgesuite.net
```
`errors.edgesuite.net` = **Akamai** 방화벽. 프록시 문제가 아니라 **사이트 측 차단**이다.
원인 추정: 이 세션이 클라우드 데이터센터 IP에서 돌고, 대형 커머스는 크롤링 방지로 데이터센터 IP 대역을 통째로 막는다.
**로그인 자격증명 유무와 무관하게 현관에서 차단**되므로 자동화 자체가 성립하지 않는다.
→ 우회 시도는 이용약관 위반이므로 하지 않는다.

## 진단 방법론 (재사용 가능)
- 크롬 netlog: `--log-net-log=<경로> --net-log-capture-mode=Everything`
- **에러 코드만 grep하면 오진한다.** 실제로 `net_error: -202`(인증서 신뢰 실패)를 보고 "MITM 인증서 문제"로 결론냈다가 틀렸다 —
  그건 크롬 자체 텔레메트리(clients2.google.com) 요청의 에러였고 우리 요청과 무관했다.
  → **source id로 이벤트를 묶어 어느 호스트의 흐름인지 확인**한 뒤 판단할 것.
- 프록시가 MITM하는지 확인: `openssl s_client -connect <host>:443 -proxy 127.0.0.1:<port>` → 여기선 진짜 인증서를 통과시켰다(Verify return code: 0).

## 연결고리 (Connections)
- [[agent-browser]] — 이 제약들이 실제로 드러난 무대. 브라우저 자동화를 원격에서 쓰려면 이 문서의 설정이 전제다.
- [[session-independence]] — "어디서나 작동" 원칙의 예외 지대. 명령은 어디서나 돌지만 **네트워크 능력은 세션 위치에 따라 다르다.**
- [[claude-code-skills]] — "로컬 PC ↔ 클라우드는 다른 컴퓨터" 원칙의 네트워크판 확장.
- [[my-projects]] — 쿠팡 관련 작업(쿠팡파트너스·재고관리)은 원격 세션에서 브라우저 자동화로 대체 불가.

## 미해결/모순 (Open Questions)
- [확인필요] ③ 차단이 데이터센터 IP 때문인지, 자동화 브라우저 탐지 때문인지 분리 검증 안 됨. 로컬 PC에서 시도하면 구분 가능.
- [확인필요] TLS 1.2 상한이 필요한 게 이 프록시 때문인지 상위 네트워크 장비 때문인지 미확정.
- [확인필요] 쿠팡 외 다른 커머스(네이버·11번가 등)도 같은 차단인지 미검증.
