"""Replace legacy usernames with email accounts and add Midcap SHOP journals."""
from alembic import op
import sqlalchemy as sa


revision = "20260913_account_midcap_shop"
down_revision = "20260912_anomaly_v2"
branch_labels = None
depends_on = None


def upgrade():
    # The requested fresh start intentionally removes the old username-only accounts.
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("users"):
        op.execute("DELETE FROM users")
        op.add_column("users", sa.Column("email", sa.String(), nullable=True))
        op.alter_column("users", "email", nullable=False)
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.drop_column("users", "user_name")
    else:
        op.create_table(
            "users",
            sa.Column("pk_user_id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password", sa.String(), nullable=False),
            sa.Column("user_type", sa.Enum("admin", "general", name="usertype"), nullable=False),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.bulk_insert(
        sa.table(
            "users",
            sa.column("email", sa.String()),
            sa.column("password", sa.String()),
            sa.column("user_type", sa.Enum("ADMIN", "GENERAL", name="usertype", create_type=False)),
        ),
        [{
            "email": "admin@admin.com",
            "password": "$argon2id$v=19$m=65536,t=3,p=4$9PWIXAYpj1jcIT5cA/MjlA$Kt1DOf2vp45gEI+zFaTtQzK2AjFlJjcbMnOmdsMXS4o",
            "user_type": "ADMIN",
        }],
    )
    op.create_table(
        "midcap_shop_positions",
        sa.Column("pk_midcap_shop_position_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.pk_user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("average_cost", sa.Float(), nullable=False),
        sa.Column("latest_purchase_price", sa.Float(), nullable=False),
        sa.Column("latest_purchase_date", sa.Date(), nullable=False),
        sa.Column("purchase_count", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "ticker", name="uq_midcap_shop_user_ticker"),
    )
    op.create_index("ix_midcap_shop_positions_user_id", "midcap_shop_positions", ["user_id"])
    op.create_table(
        "midcap_shop_trade_events",
        sa.Column("pk_midcap_shop_trade_event_id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.pk_user_id", ondelete="CASCADE"), nullable=False),
        sa.Column("ticker", sa.String(length=32), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("execution_price", sa.Float(), nullable=False),
        sa.Column("execution_date", sa.Date(), nullable=False),
        sa.Column("cost_basis", sa.Float(), nullable=True),
        sa.Column("realized_pnl", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_midcap_shop_trade_events_user_id", "midcap_shop_trade_events", ["user_id"])
    op.create_index("ix_midcap_shop_trade_events_ticker", "midcap_shop_trade_events", ["ticker"])
    op.create_index("ix_midcap_shop_trade_events_execution_date", "midcap_shop_trade_events", ["execution_date"])


def downgrade():
    op.drop_table("midcap_shop_trade_events")
    op.drop_table("midcap_shop_positions")
    op.drop_index("ix_users_email", table_name="users")
    op.add_column("users", sa.Column("user_name", sa.String(), nullable=True))
    op.drop_column("users", "email")
