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

    # 국내 도매는 보통 부가세 포함가로 표시되고 세금계산서를 받으면 매입세액 공제된다.
    price_includes_vat: bool = True
    tax_invoice: bool = True

    @property
    def vat_credit_per_unit(self) -> float:
        """개당 공제 가능한 매입세액. 일반과세자가 세금계산서를 받았을 때만 유효."""
        if not self.tax_invoice:
            return 0.0
        base = self.unit_cost + self.inbound_ship_per_unit
        return base / 11 if self.price_includes_vat else base * 0.1


@dataclass
class ImportSourcing:
    """중국 1688 등 **해외 직수입** 조건 → 개당 랜디드 원가.

    계산 순서(정식 통관 기준):
        물품가(CNY) = 개당단가×수량 + 중국내륙배송
        물품가(KRW) = 물품가(CNY) × 환율        ← 환율에 카드/송금 수수료를 얹어 잡는 걸 권장
        CIF        = 물품가 + 국제운임 + 보험
        관세        = CIF × 관세율               ← HS코드별. 한중FTA 원산지증명(FORM E) 있으면 감면
        수입부가세  = (CIF + 관세) × 10%         ← 일반과세자는 매입세액 공제 → 원가에서 제외
        랜디드총액  = CIF + 관세 + 통관/포워더 수수료
    """
    unit_price_cny: float           # 1688 개당 단가 (CNY)
    qty: int                        # 이번에 수입하는 총 수량
    fx_rate: float = 195.0          # CNY→KRW 환율(수수료 포함해 보수적으로)
    china_domestic_cny: float = 0.0 # 중국 내륙배송(1688→포워더 창고), CNY
    intl_shipping: float = 0.0      # 국제운임 총액(KRW). 0이면 무게×단가로 계산
    weight_kg: float = 0.0          # 총 중량(또는 부피중량) kg
    intl_rate_per_kg: float = 0.0   # kg당 국제운임(KRW). 해운 LCL은 CBM 기준이라 별도 환산 필요
    insurance: float = 0.0          # 적하보험(KRW)
    duty_rate: float = 0.08         # 관세율(HS코드별, 기본 8%)
    customs_fee: float = 30000.0    # 통관수수료+포워더 수수료(수입 건당, KRW)
    vat_deductible: bool = True     # 일반과세자면 True → 수입부가세는 공제되어 원가에서 빠짐

    @property
    def units(self) -> int:
        return self.qty

    @property
    def goods_krw(self) -> float:
        """물품가(KRW) = (개당단가×수량 + 중국내륙배송) × 환율."""
        return (self.unit_price_cny * self.qty + self.china_domestic_cny) * self.fx_rate

    @property
    def freight_krw(self) -> float:
        """국제운임(KRW). 총액을 직접 줬으면 그 값, 아니면 무게×kg단가."""
        return self.intl_shipping or (self.weight_kg * self.intl_rate_per_kg)

    @property
    def cif(self) -> float:
        """과세가격(CIF) = 물품가 + 국제운임 + 보험."""
        return self.goods_krw + self.freight_krw + self.insurance

    @property
    def duty(self) -> float:
        """관세 = CIF × 관세율."""
        return self.cif * self.duty_rate

    @property
    def import_vat(self) -> float:
        """수입 부가세 = (CIF + 관세) × 10%. 세관 납부."""
        return (self.cif + self.duty) * 0.1

    @property
    def landed_total(self) -> float:
        """랜디드 총액(부가세 제외) = CIF + 관세 + 통관·포워더 수수료.

        수입부가세는 일반과세자면 매입세액으로 공제되므로 원가에 넣지 않는다.
        간이/면세 사업자라면 vat_deductible=False → 원가에 포함한다.
        """
        total = self.cif + self.duty + self.customs_fee
        if not self.vat_deductible:
            total += self.import_vat
        return total

    @property
    def unit_cost(self) -> float:
        """개당 물품가(운임·관세 제외) — 참고용."""
        return self.goods_krw / self.qty

    @property
    def inbound_ship_per_unit(self) -> float:
        """개당 국제운임+통관비 분담."""
        return (self.freight_krw + self.insurance + self.duty + self.customs_fee) / self.qty

    @property
    def landed_unit_cost(self) -> float:
        """개당 랜디드 원가."""
        return self.landed_total / self.qty

    @property
    def vat_credit_per_unit(self) -> float:
        """개당 공제 가능한 매입세액 = 수입부가세/수량 (일반과세자만)."""
        return (self.import_vat / self.qty) if self.vat_deductible else 0.0


# --------------------------------------------------------------------------- #
# 광고비 모델
# --------------------------------------------------------------------------- #
def ad_cost_from_cpc(cpc: float, conversion_rate: float) -> float:
    """CPC와 전환율로 '판매 1건당 광고비'를 계산.

    예) CPC 300원, 전환율 3% → 1건 팔려면 클릭 33회 → 광고비 10,000원/건.
    쿠팡 광고가 마진을 통째로 먹는지 여기서 바로 드러난다.
    """
    if conversion_rate <= 0:
        return float("inf")
    return cpc / conversion_rate


def ad_cost_from_roas(sale_price: float, target_roas: float) -> float:
    """목표 ROAS로 개당 허용 광고비. ROAS 500%(=5.0)면 판매가의 20%."""
    if target_roas <= 0:
        return float("inf")
    return sale_price / target_roas


def blended_ad_cost(cost_per_ad_sale: float, ad_share: float) -> float:
    """실제로 부담하는 **개당 평균 광고비**.

    광고로 팔린 건에만 광고비가 붙는다. 전체 판매 중 광고 기여 비중이 ad_share면
        개당 평균 광고비 = 건당 광고비 × ad_share
    예) 건당 10,000원인데 광고 판매 비중 20% → 개당 평균 2,000원.

    "무광고로 팔 수 있나"는 결국 ad_share를 얼마나 낮출 수 있냐의 문제다.
    (오가닉 노출이 늘수록 ad_share↓ → 실질 광고비↓)
    """
    return cost_per_ad_sale * max(0.0, min(1.0, ad_share))


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
def _vat(sale: float, sourcing, cost: CoupangCost) -> float:
    """부가세 부담(개당). 소싱 판단용 근사치.

    일반과세: 납부세액 = 매출세액 − 매입세액.
      · 매출세액 = 판매가/11 (판매가는 부가세 포함가)
      · 매입세액 = 사입분(소싱 객체가 계산: 국내는 매입가/11, 수입은 수입부가세)
                  + 택배·포장 등 국내 매입분/11
      → 수입은 물품가에 부가세가 없고 세관에 낸 수입부가세가 공제분이므로,
        국내 사입과 공제 구조가 다르다. 그래서 소싱 객체에 위임한다.
    """
    if cost.vat_mode == "normal":
        vat_out = sale / 11
        credit = getattr(sourcing, "vat_credit_per_unit", 0.0)
        vat_in = credit + (cost.outbound_shipping + cost.packaging) / 11
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
    vat = _vat(sale_price, sourcing, cost)

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
        rate += 1 / 11  # 매출부가세율
        # 매입세액 공제분은 비용을 줄여준다(현금 유입)
        fixed -= getattr(sourcing, "vat_credit_per_unit", 0.0) + (cost.outbound_shipping + cost.packaging) / 11
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
