"""쿠팡·네이버쇼핑 크롤러 패키지 (Scrapling 기반).

영상 학습 출처: 오늘코드(todaycode) — "7만 GitHub star를 받은 Scrapling,
Cloudflare 차단 어디까지 우회할 수 있을까? 적응형 웹스크래핑".

세 페처(Fetcher / StealthyFetcher / DynamicFetcher)와 적응형(adaptive) 선택자를
쿠팡·네이버쇼핑에 적용한다. 자세한 사용법은 README.md 참고.
"""

__all__ = ["common", "coupang", "naver_shopping"]
__version__ = "0.1.0"
