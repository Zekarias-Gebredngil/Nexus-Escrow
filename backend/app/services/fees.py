from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.config import settings

ETB_CENT = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class FeeBreakdown:
    gateway_fee_etb: Decimal
    escrow_fee_etb: Decimal
    admin_cut_etb: Decimal
    seller_net_etb: Decimal


class FeeCalculator:
    def calculate(self, item_price_etb: Decimal) -> FeeBreakdown:
        item_price = self._money(item_price_etb)
        escrow_fee = self._money(item_price * settings.platform_fee_rate)
        gateway_fee = self._money(item_price * settings.gateway_fee_rate)
        platform_net = max(escrow_fee - gateway_fee, Decimal("0.00"))
        admin_cut = self._money(platform_net * settings.admin_net_share_rate)
        return FeeBreakdown(
            gateway_fee_etb=gateway_fee,
            escrow_fee_etb=escrow_fee,
            admin_cut_etb=admin_cut,
            seller_net_etb=item_price,
        )

    @staticmethod
    def _money(value: Decimal) -> Decimal:
        return value.quantize(ETB_CENT, rounding=ROUND_HALF_UP)
