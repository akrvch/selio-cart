from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "cart",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=True),
        sa.Column("company_id", sa.BigInteger(), nullable=False),
        sa.Column("cookie", sa.String(length=255), nullable=True),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # Partial unique constraints: one ACTIVE per company for user or cookie
    op.create_index(
        "uq_cart_company_user_active",
        "cart",
        ["company_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("status = 1 AND user_id IS NOT NULL"),
    )
    op.create_index(
        "uq_cart_company_cookie_active",
        "cart",
        ["company_id", "cookie"],
        unique=True,
        postgresql_where=sa.text("status = 1 AND cookie IS NOT NULL"),
    )

    op.create_table(
        "cart_item",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("cart_id", sa.BigInteger(), sa.ForeignKey("cart.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_cart_item_quantity_positive"),
    )

    op.create_index("ix_cart_item_cart_id", "cart_item", ["cart_id"], unique=False)
    op.create_index("uq_cart_item_cart_product", "cart_item", ["cart_id", "product_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_cart_item_cart_product", table_name="cart_item")
    op.drop_index("ix_cart_item_cart_id", table_name="cart_item")
    op.drop_table("cart_item")

    op.drop_index("uq_cart_company_cookie_active", table_name="cart")
    op.drop_index("uq_cart_company_user_active", table_name="cart")
    op.drop_table("cart")


