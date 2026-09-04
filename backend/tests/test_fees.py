from decimal import Decimal

from app.services.fees import FeeCalculator


def test_fee_breakdown_matches_spec_example() -> None:
    fees = FeeCalculator().calculate(Decimal("3000.00"))

    assert fees.escrow_fee_etb == Decimal("75.00")
    assert fees.gateway_fee_etb == Decimal("60.00")
    assert fees.admin_cut_etb == Decimal("6.00")
    assert fees.seller_net_etb == Decimal("3000.00")

