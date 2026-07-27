"""로컬 중계 프록시 — 브라우저(Chromium/Camoufox) ↔ 에이전트 프록시 사이의 다리.

왜 필요한가
-----------
이 개발 샌드박스의 이그레스 프록시는 curl·python의 CONNECT는 통과시키지만
Chromium이 보내는 CONNECT는 ERR_CONNECTION_RESET으로 끊는다(프록시 로그에는
거부 기록조차 남지 않음). 반면 파이썬 소켓으로 직접 CONNECT를 보내면
터널이 정상적으로 열린다.

그래서 이 모듈은 브라우저가 붙을 수 있는 **평범한 HTTP 프록시**를 로컬에 띄우고,
받은 CONNECT를 파이썬 소켓으로 다시 만들어 상위 프록시에 전달한다.
바이트는 양방향으로 그대로 흘려보내므로 TLS는 브라우저↔목적지 간에 유지된다
(상위 프록시가 MITM이면 그 인증서를 브라우저가 신뢰하면 된다).

보안 메모: 이것은 프록시를 **우회하지 않는다**. 모든 트래픽은 그대로 상위
에이전트 프록시를 통과하며 정책 검사를 받는다. 단지 CONNECT 요청을 프록시가
받아들이는 형태로 다시 써줄 뿐이다.

사용:
    from crawler.relay_proxy import RelayProxy
    with RelayProxy() as relay:
        page = fetch(url, FetchOptions(proxy=relay.url))
"""
from __future__ import annotations

import logging
import os
import select
import socket
import threading
from urllib.parse import urlparse

log = logging.getLogger("crawler.relay")

BUF = 65536


def _upstream() -> tuple[str, int] | None:
    """환경변수에서 상위 프록시 주소를 읽는다. 없으면 직결 모드."""
    raw = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if not raw:
        return None
    u = urlparse(raw if "://" in raw else f"http://{raw}")
    if not u.hostname:
        return None
    return u.hostname, (u.port or 8080)


def _pipe(a: socket.socket, b: socket.socket) -> None:
    """두 소켓 사이로 바이트를 양방향 전달한다."""
    socks = [a, b]
    try:
        while True:
            r, _, x = select.select(socks, [], socks, 60)
            if x or not r:
                break
            for s in r:
                try:
                    data = s.recv(BUF)
                except OSError:
                    return
                if not data:
                    return
                dst = b if s is a else a
                try:
                    dst.sendall(data)
                except OSError:
                    return
    finally:
        for s in socks:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                s.close()
            except OSError:
                pass


class RelayProxy:
    """브라우저가 붙을 로컬 HTTP 프록시. with 문으로 쓰면 자동 종료된다."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.host = host
        self._srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._srv.bind((host, port))
        self._srv.listen(64)
        self.port = self._srv.getsockname()[1]
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.upstream = _upstream()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

    # ── 서버 루프 ────────────────────────────────────────────────────────
    def start(self) -> "RelayProxy":
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        log.info("중계 프록시 시작: %s (상위=%s)", self.url,
                 f"{self.upstream[0]}:{self.upstream[1]}" if self.upstream else "직결")
        return self

    def stop(self) -> None:
        self._stop.set()
        try:
            self._srv.close()
        except OSError:
            pass

    def __enter__(self) -> "RelayProxy":
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                cli, _ = self._srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(cli,), daemon=True).start()

    # ── 요청 처리 ────────────────────────────────────────────────────────
    def _handle(self, cli: socket.socket) -> None:
        try:
            cli.settimeout(30)
            head = b""
            while b"\r\n\r\n" not in head:
                chunk = cli.recv(BUF)
                if not chunk:
                    cli.close()
                    return
                head += chunk
                if len(head) > 262144:
                    cli.close()
                    return

            first = head.split(b"\r\n", 1)[0].decode("latin-1", "replace")
            parts = first.split()
            if len(parts) < 3:
                cli.close()
                return
            method, target = parts[0], parts[1]

            if method.upper() == "CONNECT":
                self._do_connect(cli, target)
            else:
                # 평문 HTTP는 상위 프록시가 거부하므로(405) 그대로 전달하지 않는다.
                cli.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n"
                            b"Content-Length: 0\r\nConnection: close\r\n\r\n")
                cli.close()
        except Exception as exc:  # noqa: BLE001
            log.debug("중계 처리 오류: %s", exc)
            try:
                cli.close()
            except OSError:
                pass

    def _do_connect(self, cli: socket.socket, target: str) -> None:
        host, _, port_s = target.rpartition(":")
        if not host:
            host, port_s = target, "443"
        try:
            port = int(port_s)
        except ValueError:
            port = 443

        try:
            up = self._open_tunnel(host, port)
        except Exception as exc:  # noqa: BLE001
            log.debug("터널 실패 %s:%s — %s", host, port, exc)
            try:
                cli.sendall(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
                cli.close()
            except OSError:
                pass
            return

        try:
            cli.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        except OSError:
            up.close()
            return
        cli.settimeout(None)
        up.settimeout(None)
        _pipe(cli, up)

    def _open_tunnel(self, host: str, port: int) -> socket.socket:
        """상위 프록시로 CONNECT를 다시 보내 터널을 연다(없으면 직결)."""
        if not self.upstream:
            return socket.create_connection((host, port), timeout=20)

        ph, pp = self.upstream
        s = socket.create_connection((ph, pp), timeout=20)
        req = (f"CONNECT {host}:{port} HTTP/1.1\r\n"
               f"Host: {host}:{port}\r\n"
               f"Proxy-Connection: keep-alive\r\n\r\n").encode()
        s.sendall(req)

        resp = b""
        while b"\r\n\r\n" not in resp:
            d = s.recv(BUF)
            if not d:
                raise ConnectionError("상위 프록시가 응답 없이 연결을 닫음")
            resp += d
            if len(resp) > 65536:
                raise ConnectionError("상위 프록시 응답이 비정상적으로 큼")

        status = resp.split(b"\r\n", 1)[0].decode("latin-1", "replace")
        if " 200" not in status:
            raise ConnectionError(f"상위 프록시 CONNECT 거부: {status}")
        return s
