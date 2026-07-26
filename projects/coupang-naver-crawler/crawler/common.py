"""크롤러 공통 유틸 — Scrapling 페처 래퍼 · 적응형 선택자 · 재시도 · 저장.

핵심 설계:
- 페처(fetchers) 의존성은 **실행 시점에만** import 한다. 그래야 파서만 있는
  환경(예: 오프라인 테스트)에서도 이 모듈을 불러올 수 있다.
- 선택자는 항상 `_sel()`을 거친다 → 사이트 레이아웃이 바뀌면 Scrapling의
  adaptive 재배치로 요소를 다시 찾는다(영상의 핵심 기능).
- 버전마다 페처 인자가 달라도 죽지 않도록, 지원하지 않는 kwarg는 걸러내며 호출한다.
"""
from __future__ import annotations

import csv
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("crawler")

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


# --------------------------------------------------------------------------- #
# 로깅 / 예의 있는 대기
# --------------------------------------------------------------------------- #
def setup_logging(verbose: bool = False) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def polite_sleep(base: float = 1.5, jitter: float = 1.5) -> None:
    """서버에 부담을 주지 않도록 요청 사이에 임의 지연을 둔다."""
    time.sleep(base + random.uniform(0, jitter))


# --------------------------------------------------------------------------- #
# 페처 옵션
# --------------------------------------------------------------------------- #
@dataclass
class FetchOptions:
    engine: str = "stealthy"          # stealthy | dynamic | http
    headless: bool = True
    solve_cloudflare: bool = True     # StealthyFetcher 전용
    network_idle: bool = True
    google_search: bool = True        # 구글 리퍼러로 위장 (StealthyFetcher)
    proxy: str | None = None
    timeout: int = 30000              # ms
    wait: int = 0                     # 로드 후 추가 대기 (ms)
    wait_selector: str | None = None  # 이 선택자가 나타날 때까지 대기
    # 불필요 리소스 차단(속도↑). scrapling의 disable_resources는 image/font/media 등을
    # 함께 드롭하므로 별도의 이미지 차단 옵션은 두지 않는다(0.4.11에 block_images 인자 없음).
    disable_resources: bool = False
    adaptive: bool = True             # 적응형 선택자 활성화
    extra: dict = field(default_factory=dict)  # 버전별 추가 인자 통과용


# --------------------------------------------------------------------------- #
# 페처 로딩 & 호출
# --------------------------------------------------------------------------- #
def _load_fetchers():
    try:
        from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher
    except ModuleNotFoundError as exc:  # curl_cffi / playwright 등 미설치
        raise SystemExit(
            "\n[설치 필요] Scrapling 페처 의존성이 없습니다. 다음을 실행하세요:\n"
            '    pip install "scrapling[fetchers]"\n'
            "    scrapling install\n"
            f"(원인: {exc})\n"
        )
    return Fetcher, StealthyFetcher, DynamicFetcher


_BAD_KWARG = re.compile(r"unexpected keyword argument '(\w+)'")


def _call(fn: Callable, url: str, kwargs: dict):
    """지원하지 않는 kwarg가 있으면 제거하며 재귀적으로 호출한다(버전 호환)."""
    while True:
        try:
            return fn(url, **kwargs)
        except TypeError as exc:
            m = _BAD_KWARG.search(str(exc))
            if m and m.group(1) in kwargs:
                log.warning("이 Scrapling 버전은 '%s' 인자를 지원하지 않아 무시합니다.", m.group(1))
                kwargs.pop(m.group(1))
                continue
            raise


def fetch(url: str, opts: FetchOptions | None = None):
    """opts.engine에 맞는 페처로 URL을 가져와 Selector 페이지를 반환한다."""
    opts = opts or FetchOptions()
    Fetcher, StealthyFetcher, DynamicFetcher = _load_fetchers()

    # 적응형 저장소 활성화 (레이아웃 변경 시 요소 재배치)
    if opts.adaptive:
        for cls in (StealthyFetcher, DynamicFetcher, Fetcher):
            try:
                cls.adaptive = True
            except Exception:  # noqa: BLE001 - 버전에 따라 속성이 없을 수 있음
                pass

    if opts.engine == "http":
        kwargs: dict[str, Any] = {"stealthy_headers": True, "timeout": opts.timeout / 1000}
        if opts.proxy:
            kwargs["proxy"] = opts.proxy
        kwargs.update(opts.extra)
        return _call(Fetcher.get, url, kwargs)

    cls = DynamicFetcher if opts.engine == "dynamic" else StealthyFetcher
    kwargs = {
        "headless": opts.headless,
        "network_idle": opts.network_idle,
        "timeout": opts.timeout,
    }
    if opts.engine == "stealthy":
        kwargs["solve_cloudflare"] = opts.solve_cloudflare
        kwargs["google_search"] = opts.google_search
    if opts.proxy:
        kwargs["proxy"] = opts.proxy
    if opts.wait:
        kwargs["wait"] = opts.wait
    if opts.wait_selector:
        kwargs["wait_selector"] = opts.wait_selector
    if opts.disable_resources:
        kwargs["disable_resources"] = True
    kwargs.update(opts.extra)
    return _call(cls.fetch, url, kwargs)


class FetchBlocked(RuntimeError):
    """재시도를 모두 소진했을 때 올리는, 사람이 읽을 수 있는 실패."""


def with_retry(fn: Callable, *, tries: int = 2, base_delay: float = 2.0, what: str = "요청"):
    """네트워크·차단 실패에 대비한 지수 백오프 재시도.

    주의: Scrapling 페처는 내부적으로도 3회 재시도한다. 여기서 tries를 크게 잡으면
    (내부 3회 × 외부 tries) 만큼 곱해져 차단된 사이트에서 매우 느려진다 → 기본 2.
    """
    last: Exception | None = None
    for i in range(1, tries + 1):
        try:
            return fn()
        except SystemExit:
            raise  # 설치 안내는 재시도하지 않음
        except Exception as exc:  # noqa: BLE001
            last = exc
            log.warning("[%s] 시도 %d/%d 실패: %s", what, i, tries, exc)
            if i < tries:
                time.sleep(base_delay * (2 ** (i - 1)) + random.uniform(0, 1))
    assert last is not None
    raise FetchBlocked(f"{what}: {tries}회 시도 모두 실패 — {type(last).__name__}: {last}") from last


# --------------------------------------------------------------------------- #
# 적응형 선택자 헬퍼
# --------------------------------------------------------------------------- #
def _adaptive_enabled(page) -> bool:
    """이 페이지에서 Scrapling 적응형 기능이 실제로 켜져 있는지 확인.

    켜져 있지 않은데 auto_save/adaptive 인자를 넘기면 Scrapling이 인자를 무시하며
    선택자마다 WARNING을 찍는다 → 미리 확인해 불필요한 호출과 로그 소음을 없앤다.
    """
    return bool(getattr(page, "_Selector__adaptive_enabled", False))


def _sel(page, selector: str, adaptive: bool = True):
    """selector로 요소를 찾는다. 비면 adaptive 재배치를 시도하고, 최종적으로 평범한 css로 폴백."""
    if not (adaptive and _adaptive_enabled(page)):
        return page.css(selector)  # 적응형 미지원 → 평범한 css 한 번만

    # 1) 정상 경로 — 첫 성공 시 선택자 지문을 저장(auto_save)
    try:
        res = page.css(selector, auto_save=True)
        if res:
            return res
    except Exception:  # noqa: BLE001 - 저장소 미설정 등
        pass
    # 2) 레이아웃이 바뀐 경우 — 저장된 지문으로 재배치
    try:
        res = page.css(selector, adaptive=True)
        if res:
            return res
    except Exception:  # noqa: BLE001
        pass
    # 3) 평범한 css (항상 동작)
    return page.css(selector)


def first(el, selector: str, default: Any = None):
    """단일 요소/페이지에서 selector의 첫 텍스트/속성값을 안전하게 꺼낸다."""
    try:
        v = el.css(selector).get()
    except Exception:  # noqa: BLE001
        return default
    if isinstance(v, str):
        v = v.strip()
    return v if v not in (None, "") else default


def present(el, selector: str | None) -> bool | None:
    """selector에 해당하는 요소가 존재하는지(예: 로켓배송 배지) 여부."""
    if not selector:
        return None
    try:
        return bool(el.css(selector).get())
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- #
# 숫자 파싱 / 저장 / 선택자 설정
# --------------------------------------------------------------------------- #
_NUM = re.compile(r"[\d,]+")


def to_int(text: Any) -> int | None:
    """'29,900원' → 29900. 숫자가 없으면 None."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return int(text)
    m = _NUM.search(str(text))
    return int(m.group().replace(",", "")) if m else None


def save(rows: list[dict], path: str | Path, fmt: str | None = None) -> Path:
    """결과를 JSON 또는 CSV로 저장한다(확장자로 자동 판별)."""
    path = Path(path)
    fmt = fmt or (path.suffix.lstrip(".").lower() or "json")
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        keys: list[str] = []
        for r in rows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(rows)
    else:
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_selectors(site: str, defaults: dict) -> dict:
    """config/selectors.json 에서 사이트별 선택자를 읽어 기본값에 덮어쓴다.

    사이트 레이아웃이 바뀌어 기본 선택자가 안 맞을 때, 코드를 고치지 않고
    config/selectors.json 만 수정하면 되도록 하는 장치.
    """
    merged = dict(defaults)
    cfg = CONFIG_DIR / "selectors.json"
    if cfg.exists():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            merged.update(data.get(site, {}))
        except Exception as exc:  # noqa: BLE001
            log.warning("selectors.json 로드 실패(기본 선택자 사용): %s", exc)
    return merged
