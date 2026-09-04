from app.main import app


def test_openapi_exposes_core_routes() -> None:
    paths = app.openapi()["paths"]

    assert "/v1/health" in paths
    assert "/v1/health/ready" in paths
    assert "/v1/users/{user_id}" in paths
    assert "/v1/channels/{channel_id}" in paths
    assert "/v1/escrows" in paths
    assert "/v1/escrows/{escrow_id}/dispute" in paths
    assert "/v1/escrows/{escrow_id}/resolve/release" in paths
    assert "/v1/escrows/{escrow_id}/resolve/refund" in paths
    assert "/v1/webhooks/chapa" in paths
