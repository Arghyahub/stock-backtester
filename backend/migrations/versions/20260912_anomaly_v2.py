"""Add persisted Anomaly Trading V2 results and curated mappings."""
from alembic import op
import sqlalchemy as sa

revision = "20260912_anomaly_v2"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("strategy_runs", sa.Column("pk_strategy_run_id", sa.Integer(), primary_key=True), sa.Column("strategy_id", sa.Integer(), sa.ForeignKey("strategies.pk_strategy_id"), nullable=False), sa.Column("status", sa.String(), nullable=False), sa.Column("computed_at", sa.DateTime(), nullable=False), sa.Column("configuration", sa.JSON(), nullable=False), sa.Column("data_quality", sa.JSON(), nullable=False))
    op.create_table("instrument_mappings", sa.Column("pk_instrument_mapping_id", sa.Integer(), primary_key=True), sa.Column("sector_equity_id", sa.Integer(), sa.ForeignKey("equities.pk_equity_id"), nullable=False), sa.Column("instrument_equity_id", sa.Integer(), sa.ForeignKey("equities.pk_equity_id"), nullable=False), sa.Column("active", sa.Boolean(), nullable=False), sa.UniqueConstraint("sector_equity_id", "instrument_equity_id", name="uq_sector_instrument"))
    op.create_table("strategy_plans", sa.Column("pk_strategy_plan_id", sa.Integer(), primary_key=True), sa.Column("strategy_run_id", sa.Integer(), sa.ForeignKey("strategy_runs.pk_strategy_run_id", ondelete="CASCADE"), nullable=False), sa.Column("sector_equity_id", sa.Integer(), sa.ForeignKey("equities.pk_equity_id"), nullable=False), sa.Column("month", sa.Integer(), nullable=False), sa.Column("day", sa.Integer(), nullable=False), sa.Column("window_days", sa.Integer(), nullable=False), sa.Column("oos_observations", sa.Integer(), nullable=False), sa.Column("oos_mean_return", sa.Float(), nullable=False), sa.Column("oos_win_rate", sa.Float(), nullable=False), sa.Column("oos_worst_return", sa.Float(), nullable=False), sa.Column("oos_worst_drawdown", sa.Float(), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False))
    op.create_table("plan_instruments", sa.Column("pk_plan_instrument_id", sa.Integer(), primary_key=True), sa.Column("strategy_plan_id", sa.Integer(), sa.ForeignKey("strategy_plans.pk_strategy_plan_id", ondelete="CASCADE"), nullable=False), sa.Column("equity_id", sa.Integer(), sa.ForeignKey("equities.pk_equity_id"), nullable=False), sa.Column("instrument_type", sa.String(), nullable=False), sa.Column("seasonal_return", sa.Float(), nullable=False), sa.Column("alpha", sa.Float(), nullable=False), sa.Column("beta", sa.Float(), nullable=False), sa.Column("observation_count", sa.Integer(), nullable=False), sa.Column("is_recommended", sa.Boolean(), nullable=False), sa.Column("evidence", sa.JSON(), nullable=False), sa.UniqueConstraint("strategy_plan_id", "equity_id", name="uq_plan_instrument"))

def downgrade():
    op.drop_table("plan_instruments"); op.drop_table("strategy_plans"); op.drop_table("instrument_mappings"); op.drop_table("strategy_runs")
