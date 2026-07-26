"""쿠팡 마진계산기 + 묶음(bundle) 아비트라지 엔진.

핵심 아이디어(사용자 요청):
    도매꾹에서 '심리스팬티 5장 묶음'을 택배비 1번으로 사입 → 쿠팡에 '1장'씩 판매.
    이때 개당 원가 = 묶음가/수량, 개당 배송분담 = 도매배송비/수량 으로 떨어지고,
    이 '랜디드 원가(landed cost)'로 쿠팡 판매가에서 진짜 마진이 남는지 판정한다.

가장 흔한 저비용 진입 방식인 **마켓플레이스(셀러배송)** 기준으로 모델링한다.
전부 표준 라이브러리만 사용 → 무설치로 테스트 가능(tests/test_margin.py).

수수료 근거(공개 자료, config/coupang_fees.json에서 카테고리별로 덮어쓸 수 있음):
- 쿠팡 판매수수료는 카테고리별 약 4~10.8%이며 **결제수수료가 포함**된다(고객 결제금액 기준).
- 월매출 100만원 이상이면 월 55,000원 서비스 이용료(판매수량으로 분산 가능).
- 셀러배송은 내가 택배비를 부담(무료배송이면 판매가에 녹임).
"""
from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# 입력 모델
# --------------------------------------------------------------------------- #
@dataclass
class BundleSourcing:
    """도매 묶음 사입 조건 → 개당 랜디드 원가 계산."""
    bundle_price: int          # 묶음 1개 총 매입가 (예: 5장 묶음 = 9,000원)
    bundle_qty: int            # 묶음당 낱개 수량 (예: 5)
    inbound_shipping: int = 0  # 도매처→나 배송비 (주문 1회당, 예: 3,000)
    bundles_per_order: int = 1 # 한 번 주문에 몇 묶음 사입하나 (많을수록 배송비 분산↑)

    @property
    def units(self) -> int:
        """이번 주문으로 확보하는 총 낱개 수량."""
        return self.bundle_qty * self.bundles_per_order

    @property
    def unit_cost(self) -> float:
        """개당 순매입가 (배송 제외)."""
        return (self.bundle_price * self.bundles_per_order) / self.units

    @property
    def inbound_ship_per_unit(self) -> float:
        """개당 사입배송 분담액 = 배송비 1회 / 총 낱개수. 묶음/주문량이 클수록 작아진다."""
        return self.inbound_shipping / self.units

    @property
    def landed_unit_cost(self) -> float:
        """개당 랜디드 원가 = 순매입가 + 사입배송 분담."""
        return self.unit_cost + self.inbound_ship_per_unit


@dataclass
class CoupangCost:
    """쿠팡 판매 시 개당 부대비용 가정 (마켓플레이스/셀러배송 기준)."""
    commission_rate: float          # 카테고리 판매수수료(결제 포함). 예: 0.108
    outbound_shipping: int = 0      # 고객에게 보내는 택배비(셀러배송, 내 부담). 무료배송이면 0으로 두고 판매가에 반영
    packaging: int = 200            # 개당 포장/부자재비
    return_rate: float = 0.02       # 반품·교환율 (셀러배송은 왕복 택배비 손실)
    return_ship_roundtrip: int = 0  # 반품 1건당 왕복 택배 손실(0이면 outbound*2로 추정)
    ad_cost_per_unit: int = 0       # 개당 광고비(선택). 광고 최소화가 목표라면 0
    monthly_service_fee: int = 55000  # 월 서비스 이용료(월매출 100만+). 분산은 monthly_units로
    vat_mode: str = "none"          # none | simplified(간이) | normal(일반)


# --------------------------------------------------------------------------- #
# 계산
# --------------------------------------------------------------------------- #
def _vat(sale: float, landed: float, cost: CoupangCost) -> float:
    """부가세 부담(개당). 소싱 판단용 근사치."""
    if cost.vat_mode == "normal":
        # 일반과세: 매출부가세(판매가/11) − 매입부가세 공제(원가·택배·포장/11, 세금계산서 수취 가정)
        vat_out = sale / 11
        vat_in = (landed + cost.outbound_shipping + cost.packaging) / 11
        return vat_out - vat_in
    if cost.vat_mode == "simplified":
        # 간이과세 소매업 근사: 공급대가 × 부가율(약15%) × 10% ≈ 판매가 × 1.5%
        return sale * 0.015
    return 0.0


def compute(
    sale_price: float,
    sourcing: BundleSourcing,
    cost: CoupangCost,
    monthly_units: int | None = None,
) -> dict:
    """판매가 + 묶음소싱 + 쿠팡비용 → 개당 순마진 상세.

    monthly_units: 월 예상 판매수량(주면 서비스 이용료를 개당으로 분산; 없으면 서비스료 제외).
    """
    landed = sourcing.landed_unit_cost
    commission = sale_price * cost.commission_rate
    roundtrip = cost.return_ship_roundtrip or (cost.outbound_shipping * 2)
    # 반품 충당: 반품 시 왕복택배 손실 + (재판매 불가 가정 시) 원가 손실의 절반을 보수적으로 반영
    return_reserve = cost.return_rate * (roundtrip + landed * 0.5)
    service = (cost.monthly_service_fee / monthly_units) if monthly_units else 0.0
    vat = _vat(sale_price, landed, cost)

    costs = {
        "매입원가(개당)": landed,
        "쿠팡수수료": commission,
        "고객배송비": float(cost.outbound_shipping),
        "포장비": float(cost.packaging),
        "반품충당": return_reserve,
        "광고비": float(cost.ad_cost_per_unit),
        "서비스료분산": service,
        "부가세": vat,
    }
    total_cost = sum(costs.values())
    net = sale_price - total_cost
    return {
        "판매가": float(sale_price),
        "랜디드원가": landed,
        "비용상세": costs,
        "총비용": total_cost,
        "순마진": net,
        "마진율": (net / sale_price) if sale_price else None,
        "ROI": (net / landed) if landed else None,  # 투입 원가 대비 수익률
    }


def breakeven_price(
    sourcing: BundleSourcing,
    cost: CoupangCost,
    target_margin: float = 0.15,
    monthly_units: int | None = None,
) -> float:
    """목표 마진율을 남기려면 최소 판매가가 얼마여야 하는지 역산.

    마진율 m 목표: net = m·P.
    P − [수수료율·P + 부가세율·P] − 고정비 = m·P  로 풀어 P를 구한다.
    (부가세는 간이=1.5%P, 일반=대략 (P−공제)/11 → 근사로 매출부가세율만 반영, none=0)
    """
    landed = sourcing.landed_unit_cost
    roundtrip = cost.return_ship_roundtrip or (cost.outbound_shipping * 2)
    return_reserve = cost.return_rate * (roundtrip + landed * 0.5)
    service = (cost.monthly_service_fee / monthly_units) if monthly_units else 0.0
    fixed = landed + cost.outbound_shipping + cost.packaging + return_reserve + cost.ad_cost_per_unit + service

    rate = cost.commission_rate + target_margin
    if cost.vat_mode == "simplified":
        rate += 0.015
    elif cost.vat_mode == "normal":
        rate += 1 / 11  # 매출부가세율 근사(매입공제는 보수적으로 무시 → 상한 추정)
    price = fixed / (1 - rate)
    return round(price)


def verdict(result: dict, floor: float = 0.10) -> tuple[str, str]:
    """마진 결과 → (판정, 사유). floor=최소 허용 마진율."""
    mr = result.get("마진율")
    if mr is None:
        return "판정불가", "판매가 없음"
    if result["순마진"] <= 0:
        return "역마진", f"팔수록 손해({round(result['순마진']):,}원/개)"
    if mr < floor:
        return "주의", f"마진율 {mr*100:.1f}% < 안전선 {floor*100:.0f}%"
    if mr < floor * 1.8:
        return "가능", f"마진율 {mr*100:.1f}% (박하지만 회전 빠르면 OK)"
    return "좋음", f"마진율 {mr*100:.1f}% · ROI {result['ROI']*100:.0f}%"
