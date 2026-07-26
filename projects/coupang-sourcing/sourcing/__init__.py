"""쿠팡 자동 소싱기 — 경쟁강도 분석 + 검색량 + 마진 게이트 + 묶음 아비트라지.

구성:
    margin.py        쿠팡 마진계산기 + 묶음(도매꾹) 아비트라지  ← 핵심, 무설치 테스트
    competition.py   쿠팡 검색결과 → 경쟁강도 지표
    naver_ads.py     네이버 검색광고 API → 월간 검색량
    score.py         기회 점수(0~100) 합성
    xiaohongshu.py   샤오홍수 트렌드(레드오션 신제품 각도)
    pipeline.py      키워드 → 신호수집 → 마진게이트 → 랭킹 리포트
"""

__all__ = ["margin", "competition", "naver_ads", "score", "xiaohongshu", "pipeline"]
__version__ = "0.1.0"
