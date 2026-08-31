"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

escrow_state = postgresql.ENUM(
    "INITIATED",
    "WAITING_FOR_PAYMENT",
    "PAID",
    "SHIPPED",
    "DISPUTED",
    "RELEASED",
    "REFUNDED",
    name="escrow_state",
    create_type=False,
)


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    escrow_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("first_name", sa.String(length=150), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False, unique=True),
        sa.Column("reputation_score", sa.Numeric(3, 2), nullable=False, server_default="5.00"),
        sa.Column("total_escrows_completed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "channels",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("admin_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel_name", sa.String(length=250), nullable=False),
        sa.Column("payout_account_type", sa.String(length=50), nullable=False),
        sa.Column("payout_account_number", sa.String(length=50), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "escrows",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("buyer_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("seller_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), sa.ForeignKey("channels.id"), nullable=True),
        sa.Column("item_title", sa.String(length=255), nullable=False),
        sa.Column("item_price_etb", sa.Numeric(12, 2), nullable=False),
        sa.Column("gateway_fee_etb", sa.Numeric(12, 2), nullable=False),
        sa.Column("escrow_fee_etb", sa.Numeric(12, 2), nullable=False),
        sa.Column("admin_cut_etb", sa.Numeric(12, 2), nullable=False),
        sa.Column("seller_net_etb", sa.Numeric(12, 2), nullable=False),
        sa.Column("current_state", escrow_state, nullable=False, server_default="INITIATED"),
        sa.Column("chapa_reference", sa.String(length=100), nullable=True, unique=True),
        sa.Column("tracking_id", sa.String(length=100), nullable=True),
        sa.Column("shipping_proof_url", sa.Text(), nullable=True),
        sa.Column("unboxing_video_url", sa.Text(), nullable=True),
        sa.Column("payment_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("auto_release_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_escrows_buyer_id", "escrows", ["buyer_id"])
    op.create_index("ix_escrows_seller_id", "escrows", ["seller_id"])
    op.create_index("ix_escrows_current_state", "escrows", ["current_state"])

    op.create_table(
        "escrow_audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "escrow_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("escrows.id"),
            nullable=False,
        ),
        sa.Column("from_state", escrow_state, nullable=False),
        sa.Column("to_state", escrow_state, nullable=False),
        sa.Column("changed_by", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_escrow_audit_logs_escrow_id", "escrow_audit_logs", ["escrow_id"])


def downgrade() -> None:
    op.drop_index("ix_escrow_audit_logs_escrow_id", table_name="escrow_audit_logs")
    op.drop_table("escrow_audit_logs")
    op.drop_index("ix_escrows_current_state", table_name="escrows")
    op.drop_index("ix_escrows_seller_id", table_name="escrows")
    op.drop_index("ix_escrows_buyer_id", table_name="escrows")
    op.drop_table("escrows")
    op.drop_table("channels")
    op.drop_table("users")
    escrow_state.drop(op.get_bind(), checkfirst=True)
